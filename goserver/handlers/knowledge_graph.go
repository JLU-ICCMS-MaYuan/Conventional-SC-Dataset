package handlers

import (
	"encoding/json"
	"net/http"
	"os"
	"sort"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════════════
// 知识图谱 API（替代 Python /api/knowledge-graph/*）
// ═══════════════════════════════════════════════

var graphData *Graph

// Graph JSON 结构
type Graph struct {
	Nodes []GraphNode `json:"nodes"`
	Edges []GraphEdge `json:"edges"`
}

type GraphNode struct {
	ID    string `json:"id"`
	Label string `json:"label"`
	Year  int    `json:"year,omitempty"`
	DOI   string `json:"doi,omitempty"`
}

type GraphEdge struct {
	Source     string  `json:"source"`
	Target     string  `json:"target"`
	Type       string  `json:"type"`
	Importance float64 `json:"importance"`
	Evidence   string  `json:"evidence"`
	Color      string  `json:"color,omitempty"`
}

var relationColors = map[string]string{
	"first_discovery":           "#e53935",
	"experimental_validation":   "#43a047",
	"theoretical_basis":         "#1e88e5",
	"correction_or_dispute":     "#fb8c00",
	"development_extension":     "#8e24aa",
	"material_system_extension": "#00acc1",
	"same_research_direction":   "#546e7a",
	"supporting_evidence":       "#78909c",
}

func LoadGraph(graphPath string) {
	data, err := os.ReadFile(graphPath)
	if err != nil {
		println("[KG] 图谱加载失败:", err.Error())
		return
	}
	graphData = &Graph{}
	if err := json.Unmarshal(data, graphData); err != nil {
		println("[KG] 图谱解析失败:", err.Error())
		graphData = nil
	}
	println("[KG] 图谱加载完成:", len(graphData.Nodes), "节点,", len(graphData.Edges), "边")
}

// KGOverview 首页图谱：按 importance 降序取 top-K 边
// GET /api/knowledge-graph/overview?limit=10
func KGOverview(c *gin.Context) {
	if graphData == nil || len(graphData.Edges) == 0 {
		c.JSON(http.StatusOK, gin.H{"nodes": []any{}, "edges": []any{}, "message": "图谱数据未加载"})
		return
	}

	limit := 10
	if l := c.Query("limit"); l != "" {
		// simple atoi
		n := 0
		for _, ch := range l {
			if ch >= '0' && ch <= '9' {
				n = n*10 + int(ch-'0')
			}
		}
		if n > 0 && n <= 100 {
			limit = n
		}
	}

	edges := make([]GraphEdge, len(graphData.Edges))
	copy(edges, graphData.Edges)
	sort.Slice(edges, func(i, j int) bool {
		return edges[i].Importance > edges[j].Importance
	})

	if len(edges) > limit {
		edges = edges[:limit]
	}

	// 收集涉及的节点
	used := make(map[string]bool)
	for _, e := range edges {
		used[e.Source] = true
		used[e.Target] = true
	}
	nodes := make([]GraphNode, 0)
	for _, n := range graphData.Nodes {
		if used[n.ID] {
			nodes = append(nodes, n)
		}
	}

	for i := range edges {
		if c, ok := relationColors[edges[i].Type]; ok {
			edges[i].Color = c
		} else {
			edges[i].Color = "#999"
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"nodes":          nodes,
		"edges":          edges,
		"total_edges":    len(graphData.Edges),
		"relation_types": relationTypeKeys(),
	})
}

// KGNeighbors 展开论文节点的一层关联
// GET /api/knowledge-graph/papers/:paper_id/neighbors?limit=10
func KGNeighbors(c *gin.Context) {
	if graphData == nil {
		c.JSON(http.StatusOK, gin.H{"error": "图谱数据未加载"})
		return
	}

	paperID := c.Param("paper_id")
	nodeMap, adj := buildGraphIndex()

	node, ok := nodeMap[paperID]
	if !ok {
		c.JSON(http.StatusOK, gin.H{"error": "node not found", "center": paperID})
		return
	}

	limit := 10
	if l := c.Query("limit"); l != "" {
		n := 0
		for _, ch := range l {
			if ch >= '0' && ch <= '9' {
				n = n*10 + int(ch-'0')
			}
		}
		if n > 0 && n <= 50 {
			limit = n
		}
	}

	related := adj[paperID]
	sort.Slice(related, func(i, j int) bool {
		return related[i].Importance > related[j].Importance
	})

	selected := related
	if len(selected) > limit {
		selected = selected[:limit]
	}

	neighborIDs := make(map[string]bool)
	for _, e := range selected {
		if e.Source != paperID {
			neighborIDs[e.Source] = true
		}
		if e.Target != paperID {
			neighborIDs[e.Target] = true
		}
	}

	newNodes := make([]GraphNode, 0)
	for id := range neighborIDs {
		if n, ok := nodeMap[id]; ok {
			newNodes = append(newNodes, n)
		}
	}

	for i := range selected {
		if c, ok := relationColors[selected[i].Type]; ok {
			selected[i].Color = c
		} else {
			selected[i].Color = "#999"
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"center":    node,
		"new_nodes": newNodes,
		"new_edges": selected,
		"has_more":  len(related) > limit,
	})
}

// KGPaperDetail 论文节点详情
// GET /api/knowledge-graph/papers/:paper_id
func KGPaperDetail(c *gin.Context) {
	if graphData == nil {
		c.JSON(http.StatusOK, gin.H{"error": "图谱数据未加载"})
		return
	}

	paperID := c.Param("paper_id")
	nodeMap, adj := buildGraphIndex()

	node, ok := nodeMap[paperID]
	if !ok {
		c.JSON(http.StatusOK, gin.H{"error": "node not found"})
		return
	}

	related := adj[paperID]
	relSummary := make(map[string][]gin.H)
	for _, e := range related {
		t := e.Type
		neighbor := e.Target
		if e.Source == paperID {
			neighbor = e.Target
		} else {
			neighbor = e.Source
		}
		label := ""
		if n, ok := nodeMap[neighbor]; ok {
			label = n.Label
			if len(label) > 60 {
				label = label[:60]
			}
		}
		evidence := e.Evidence
		if len(evidence) > 200 {
			evidence = evidence[:200]
		}
		relSummary[t] = append(relSummary[t], gin.H{
			"neighbor": neighbor,
			"label":    label,
			"evidence": evidence,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"node":           node,
		"relation_count": len(related),
		"relations":      relSummary,
	})
}

// KGGraphStats 图谱统计
// GET /api/knowledge-graph/stats
func KGGraphStats(c *gin.Context) {
	if graphData == nil {
		c.JSON(http.StatusOK, gin.H{"error": "图谱数据未加载"})
		return
	}

	_, adj := buildGraphIndex()

	typeCounts := make(map[string]int)
	for _, e := range graphData.Edges {
		typeCounts[e.Type]++
	}

	degrees := make(map[string]int)
	for id := range adj {
		degrees[id] = len(adj[id])
	}
	type degPair struct {
		ID     string
		Degree int
	}
	pairs := make([]degPair, 0, len(degrees))
	for id, deg := range degrees {
		pairs = append(pairs, degPair{id, deg})
	}
	sort.Slice(pairs, func(i, j int) bool { return pairs[i].Degree > pairs[j].Degree })

	topN := 10
	if len(pairs) < topN {
		topN = len(pairs)
	}
	topNodes := make([]gin.H, 0, topN)
	nodeMap, _ := buildGraphIndex()
	for _, p := range pairs[:topN] {
		label := ""
		if n, ok := nodeMap[p.ID]; ok {
			label = n.Label
			if len(label) > 60 {
				label = label[:60]
			}
		}
		topNodes = append(topNodes, gin.H{"id": p.ID, "degree": p.Degree, "label": label})
	}

	c.JSON(http.StatusOK, gin.H{
		"total_nodes":    len(graphData.Nodes),
		"total_edges":    len(graphData.Edges),
		"relation_types": typeCounts,
		"top_nodes":      topNodes,
	})
}

// ── helpers ────────────────────────────────────

func buildGraphIndex() (map[string]GraphNode, map[string][]GraphEdge) {
	nodeMap := make(map[string]GraphNode)
	for _, n := range graphData.Nodes {
		nodeMap[n.ID] = n
	}
	adj := make(map[string][]GraphEdge)
	for _, e := range graphData.Edges {
		adj[e.Source] = append(adj[e.Source], e)
		adj[e.Target] = append(adj[e.Target], e)
	}
	return nodeMap, adj
}

func relationTypeKeys() []string {
	keys := make([]string, 0, len(relationColors))
	for k := range relationColors {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
