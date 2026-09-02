package handlers

import (
	"net/http"
	"strconv"
	"strings"

	"scwiki/server/database"

	"github.com/gin-gonic/gin"
)

// 引用图谱只读取 MySQL 中由 GROBID 解析并保留的引用事实。旧 Neo4j 语义边
// （例如 BUILDS_ON）不在任何 SQL 路径中出现，避免把 LLM 自由文本当成引用。

type graphNodeRow struct {
	PaperID            uint   `gorm:"column:paper_id"`
	Label              string `gorm:"column:label"`
	Title              string `gorm:"column:title"`
	Year               *int   `gorm:"column:year"`
	SuperconductorKind string `gorm:"column:superconductor_kind"`
	CitationCount      int64  `gorm:"column:citation_count"`
}

type graphFamily struct {
	ID   uint   `json:"id"`
	Name string `json:"name"`
}

type graphNode struct {
	PaperID            uint          `json:"paper_id"`
	Label              string        `json:"label"`
	Title              string        `json:"title"`
	Year               *int          `json:"year"`
	MaterialFamilies   []graphFamily `json:"material_families"`
	SuperconductorKind string        `json:"superconductor_kind"`
	CitationCount      int64         `json:"citation_count"`
	Marks              []string      `json:"marks"`
}

type graphEdge struct {
	CitingPaperID uint `json:"citing_paper_id"`
	CitedPaperID  uint `json:"cited_paper_id"`
}

type graphFamilyRow struct {
	PaperID uint   `gorm:"column:paper_id"`
	ID      uint   `gorm:"column:id"`
	Name    string `gorm:"column:name"`
}

type graphMarkRow struct {
	PaperID  uint   `gorm:"column:paper_id"`
	MarkType string `gorm:"column:mark_type"`
}

const publicPaperScope = "p.review_status = 'approved' AND p.approved_revision = p.content_revision"

func InitKnowledgeGraph() {}

func graphError(c *gin.Context, status int, code, message string) {
	c.JSON(status, gin.H{"code": code, "error": message})
}

func graphPlaceholders(count int) string {
	return strings.TrimRight(strings.Repeat("?,", count), ",")
}

func graphIDArgs(ids []uint) []interface{} {
	args := make([]interface{}, 0, len(ids))
	for _, id := range ids {
		args = append(args, id)
	}
	return args
}

func graphNodeIDs(nodes []graphNode) []uint {
	ids := make([]uint, 0, len(nodes))
	for _, node := range nodes {
		ids = append(ids, node.PaperID)
	}
	return ids
}

func parseGraphLimit(c *gin.Context, defaultValue, maximum int) (int, bool) {
	value := c.DefaultQuery("limit", strconv.Itoa(defaultValue))
	limit, err := strconv.Atoi(value)
	if err != nil || limit < 1 || limit > maximum {
		graphError(c, http.StatusBadRequest, "invalid_graph_filter", "limit 参数无效")
		return 0, false
	}
	return limit, true
}

func parseGraphOffset(c *gin.Context) (int, bool) {
	value := c.DefaultQuery("offset", "0")
	offset, err := strconv.Atoi(value)
	if err != nil || offset < 0 {
		graphError(c, http.StatusBadRequest, "invalid_graph_filter", "offset 参数无效")
		return 0, false
	}
	return offset, true
}

func graphOverviewFilter(c *gin.Context) (string, []interface{}, bool) {
	filter := ""
	args := make([]interface{}, 0)
	if kind := c.Query("superconductor_kind"); kind != "" {
		if kind != "conventional" && kind != "unconventional" {
			graphError(c, http.StatusBadRequest, "invalid_graph_filter", "superconductor_kind 只能是 conventional 或 unconventional")
			return "", nil, false
		}
		filter += " AND p.superconductor_kind = ?"
		args = append(args, kind)
	}

	familyIDs := make([]uint, 0)
	seen := map[uint]bool{}
	for _, value := range c.QueryArray("material_family_id") {
		id, err := strconv.ParseUint(value, 10, 32)
		if err != nil || id == 0 {
			graphError(c, http.StatusBadRequest, "invalid_graph_filter", "material_family_id 参数无效")
			return "", nil, false
		}
		converted := uint(id)
		if !seen[converted] {
			seen[converted] = true
			familyIDs = append(familyIDs, converted)
		}
	}
	if len(familyIDs) > 0 {
		filter += " AND EXISTS (SELECT 1 FROM paper_material_families pmf WHERE pmf.paper_id = p.id AND pmf.paper_revision = p.content_revision AND pmf.material_family_id IN (" + graphPlaceholders(len(familyIDs)) + "))"
		args = append(args, graphIDArgs(familyIDs)...)
	}
	return filter, args, true
}

func graphNodeRows(filter string, args []interface{}, limit int) ([]graphNodeRow, int64, error) {
	where := " WHERE " + publicPaperScope + filter
	var total int64
	if err := database.DB.Raw("SELECT COUNT(*) FROM papers p"+where, args...).Scan(&total).Error; err != nil {
		return nil, 0, err
	}
	query := `SELECT p.id AS paper_id,
 COALESCE(NULLIF(p.knowledge_graph_title, ''), p.title, '') AS label,
 COALESCE(p.title, '') AS title,
 p.year AS year,
 p.superconductor_kind AS superconductor_kind,
 COUNT(DISTINCT CASE WHEN citing.id IS NOT NULL THEN incoming.paper_id END) AS citation_count
 FROM papers p
 LEFT JOIN paper_references incoming ON incoming.cited_paper_id = p.id
   AND incoming.match_status = 'matched'
 LEFT JOIN papers citing ON citing.id = incoming.paper_id
   AND citing.content_revision = incoming.paper_revision
   AND citing.review_status = 'approved'
   AND citing.approved_revision = citing.content_revision` + where + `
 GROUP BY p.id, p.knowledge_graph_title, p.title, p.year, p.superconductor_kind
 ORDER BY citation_count DESC, p.id ASC
 LIMIT ?`
	queryArgs := append(append([]interface{}{}, args...), limit)
	rows := make([]graphNodeRow, 0)
	if err := database.DB.Raw(query, queryArgs...).Scan(&rows).Error; err != nil {
		return nil, 0, err
	}
	return rows, total, nil
}

func decorateGraphNodes(rows []graphNodeRow) ([]graphNode, error) {
	nodes := make([]graphNode, len(rows))
	for index, row := range rows {
		nodes[index] = graphNode{
			PaperID: row.PaperID, Label: row.Label, Title: row.Title, Year: row.Year,
			MaterialFamilies: []graphFamily{}, SuperconductorKind: row.SuperconductorKind,
			CitationCount: row.CitationCount, Marks: []string{},
		}
	}
	if len(nodes) == 0 {
		return nodes, nil
	}
	byID := make(map[uint]*graphNode, len(nodes))
	for index := range nodes {
		byID[nodes[index].PaperID] = &nodes[index]
	}
	ids := graphNodeIDs(nodes)
	placeholders := graphPlaceholders(len(ids))

	families := make([]graphFamilyRow, 0)
	if err := database.DB.Raw(`SELECT pmf.paper_id, mf.id,
 COALESCE(NULLIF(mf.name_zh, ''), mf.name_en, mf.code) AS name
 FROM paper_material_families pmf
 JOIN papers p ON p.id = pmf.paper_id AND p.content_revision = pmf.paper_revision
 JOIN material_families mf ON mf.id = pmf.material_family_id
 WHERE pmf.paper_id IN (`+placeholders+`) ORDER BY pmf.paper_id, mf.id`, graphIDArgs(ids)...).Scan(&families).Error; err != nil {
		return nil, err
	}
	for _, family := range families {
		if node := byID[family.PaperID]; node != nil {
			node.MaterialFamilies = append(node.MaterialFamilies, graphFamily{ID: family.ID, Name: family.Name})
		}
	}

	marks := make([]graphMarkRow, 0)
	if err := database.DB.Raw(`SELECT paper_id, mark_type FROM paper_graph_marks
 WHERE paper_id IN (`+placeholders+`) ORDER BY paper_id, mark_type`, graphIDArgs(ids)...).Scan(&marks).Error; err != nil {
		return nil, err
	}
	for _, mark := range marks {
		if node := byID[mark.PaperID]; node != nil {
			node.Marks = append(node.Marks, mark.MarkType)
		}
	}
	return nodes, nil
}

func graphNodes(filter string, args []interface{}, limit int) ([]graphNode, int64, error) {
	rows, total, err := graphNodeRows(filter, args, limit)
	if err != nil {
		return nil, 0, err
	}
	nodes, err := decorateGraphNodes(rows)
	return nodes, total, err
}

func graphEdgesBetween(ids []uint) ([]graphEdge, error) {
	if len(ids) == 0 {
		return []graphEdge{}, nil
	}
	placeholders := graphPlaceholders(len(ids))
	args := append(graphIDArgs(ids), graphIDArgs(ids)...)
	edges := make([]graphEdge, 0)
	query := `SELECT DISTINCT reference.paper_id AS citing_paper_id, reference.cited_paper_id AS cited_paper_id
 FROM paper_references reference
 JOIN papers citing ON citing.id = reference.paper_id
   AND citing.content_revision = reference.paper_revision
   AND citing.review_status = 'approved'
   AND citing.approved_revision = citing.content_revision
 JOIN papers cited ON cited.id = reference.cited_paper_id
   AND cited.review_status = 'approved'
   AND cited.approved_revision = cited.content_revision
 WHERE reference.match_status = 'matched'
   AND reference.paper_id IN (` + placeholders + `)
   AND reference.cited_paper_id IN (` + placeholders + `)
 ORDER BY reference.paper_id, reference.cited_paper_id`
	if err := database.DB.Raw(query, args...).Scan(&edges).Error; err != nil {
		return nil, err
	}
	return edges, nil
}

// KGOverview 返回按当前分类筛选的公开引用图概览。
func KGOverview(c *gin.Context) {
	limit, ok := parseGraphLimit(c, 30, 100)
	if !ok {
		return
	}
	filter, args, ok := graphOverviewFilter(c)
	if !ok {
		return
	}
	nodes, total, err := graphNodes(filter, args, limit)
	if err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "读取引用图谱失败")
		return
	}
	edges, err := graphEdgesBetween(graphNodeIDs(nodes))
	if err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "读取引用关系失败")
		return
	}
	c.JSON(http.StatusOK, gin.H{"nodes": nodes, "edges": edges, "total_nodes": total})
}

// KGSearch 从全部当前已审核论文中搜索，供前端将未出现在概览的节点固定到图上。
func KGSearch(c *gin.Context) {
	query := strings.TrimSpace(c.Query("q"))
	if query == "" {
		graphError(c, http.StatusBadRequest, "invalid_graph_filter", "q 不能为空")
		return
	}
	limit, ok := parseGraphLimit(c, 10, 50)
	if !ok {
		return
	}
	like := "%" + query + "%"
	nodes, _, err := graphNodes(" AND (p.title LIKE ? OR p.knowledge_graph_title LIKE ? OR p.doi LIKE ?)", []interface{}{like, like, like}, limit)
	if err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "搜索论文失败")
		return
	}
	c.JSON(http.StatusOK, gin.H{"nodes": nodes})
}

func graphPublicPaperExists(id uint) (bool, error) {
	var total int64
	err := database.DB.Raw("SELECT COUNT(*) FROM papers p WHERE "+publicPaperScope+" AND p.id = ?", id).Scan(&total).Error
	return total == 1, err
}

func graphNeighborRows(centerID uint, direction string, limit, offset int) ([]graphNodeRow, int64, error) {
	var neighborJoin, relationCondition string
	if direction == "upstream" {
		neighborJoin = "JOIN papers p ON p.id = relation.cited_paper_id"
		relationCondition = "relation.paper_id = ? AND relation.paper_revision = center.content_revision"
	} else {
		neighborJoin = "JOIN papers p ON p.id = relation.paper_id AND relation.paper_revision = p.content_revision"
		relationCondition = "relation.cited_paper_id = ?"
	}
	base := ` FROM paper_references relation
 JOIN papers center ON center.id = ? AND center.review_status = 'approved' AND center.approved_revision = center.content_revision
 ` + neighborJoin + `
	WHERE relation.match_status = 'matched'
	  AND p.review_status = 'approved' AND p.approved_revision = p.content_revision
	  AND p.id <> center.id
	  AND ` + relationCondition
	args := []interface{}{centerID, centerID}
	var total int64
	if err := database.DB.Raw("SELECT COUNT(DISTINCT p.id)"+base, args...).Scan(&total).Error; err != nil {
		return nil, 0, err
	}
	query := `SELECT p.id AS paper_id,
 COALESCE(NULLIF(p.knowledge_graph_title, ''), p.title, '') AS label,
 COALESCE(p.title, '') AS title,
 p.year AS year, p.superconductor_kind AS superconductor_kind,
 COUNT(DISTINCT CASE WHEN citing.id IS NOT NULL THEN incoming.paper_id END) AS citation_count
 FROM paper_references relation
 JOIN papers center ON center.id = ? AND center.review_status = 'approved' AND center.approved_revision = center.content_revision
 ` + neighborJoin + `
 LEFT JOIN paper_references incoming ON incoming.cited_paper_id = p.id AND incoming.match_status = 'matched'
 LEFT JOIN papers citing ON citing.id = incoming.paper_id
   AND citing.content_revision = incoming.paper_revision
   AND citing.review_status = 'approved' AND citing.approved_revision = citing.content_revision
	WHERE relation.match_status = 'matched'
	   AND p.review_status = 'approved' AND p.approved_revision = p.content_revision
	   AND p.id <> center.id
	   AND ` + relationCondition + `
 GROUP BY p.id, p.knowledge_graph_title, p.title, p.year, p.superconductor_kind
 ORDER BY citation_count DESC, p.id ASC
 LIMIT ? OFFSET ?`
	queryArgs := append(append([]interface{}{}, args...), limit, offset)
	rows := make([]graphNodeRow, 0)
	if err := database.DB.Raw(query, queryArgs...).Scan(&rows).Error; err != nil {
		return nil, 0, err
	}
	return rows, total, nil
}

// KGPaperNeighbors 返回一个方向的一页邻居，服务端绝不递归展开整个子图。
func KGPaperNeighbors(c *gin.Context) {
	parsedID, err := strconv.ParseUint(c.Param("paperId"), 10, 32)
	if err != nil || parsedID == 0 {
		graphError(c, http.StatusBadRequest, "invalid_graph_filter", "论文 ID 无效")
		return
	}
	centerID := uint(parsedID)
	exists, err := graphPublicPaperExists(centerID)
	if err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "读取论文失败")
		return
	}
	if !exists {
		graphError(c, http.StatusNotFound, "paper_not_found", "论文不存在或尚未审核通过")
		return
	}
	direction := c.DefaultQuery("direction", "downstream")
	if direction != "upstream" && direction != "downstream" {
		graphError(c, http.StatusBadRequest, "invalid_graph_filter", "direction 必须是 upstream 或 downstream")
		return
	}
	limit, ok := parseGraphLimit(c, 5, 50)
	if !ok {
		return
	}
	offset, ok := parseGraphOffset(c)
	if !ok {
		return
	}
	rows, total, err := graphNeighborRows(centerID, direction, limit, offset)
	if err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "读取论文邻居失败")
		return
	}
	nodes, err := decorateGraphNodes(rows)
	if err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "读取论文邻居详情失败")
		return
	}
	edges := make([]graphEdge, 0, len(nodes))
	for _, node := range nodes {
		if direction == "upstream" {
			edges = append(edges, graphEdge{CitingPaperID: centerID, CitedPaperID: node.PaperID})
		} else {
			edges = append(edges, graphEdge{CitingPaperID: node.PaperID, CitedPaperID: centerID})
		}
	}
	remaining := total - int64(offset) - int64(len(nodes))
	if remaining < 0 {
		remaining = 0
	}
	c.JSON(http.StatusOK, gin.H{
		"center_paper_id": centerID, "direction": direction, "nodes": nodes, "edges": edges,
		"offset": offset, "limit": limit, "remaining_count": remaining,
	})
}

// KGStats 保留旧端点，但只报告新引用图的公开投影统计。
func KGStats(c *gin.Context) {
	var nodeCount, edgeCount int64
	if err := database.DB.Raw("SELECT COUNT(*) FROM papers p WHERE " + publicPaperScope).Scan(&nodeCount).Error; err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "读取图谱统计失败")
		return
	}
	edgeQuery := `SELECT COUNT(*) FROM (
 SELECT DISTINCT reference.paper_id, reference.cited_paper_id
 FROM paper_references reference
 JOIN papers citing ON citing.id = reference.paper_id AND citing.content_revision = reference.paper_revision
 JOIN papers cited ON cited.id = reference.cited_paper_id
   AND cited.content_revision = cited.approved_revision
 WHERE reference.match_status = 'matched'
   AND citing.review_status = 'approved' AND citing.approved_revision = citing.content_revision
   AND cited.review_status = 'approved' AND cited.approved_revision = cited.content_revision
 ) AS public_edges`
	if err := database.DB.Raw(edgeQuery).Scan(&edgeCount).Error; err != nil {
		graphError(c, http.StatusInternalServerError, "graph_query_failed", "读取图谱统计失败")
		return
	}
	c.JSON(http.StatusOK, gin.H{"total_nodes": nodeCount, "total_edges": edgeCount})
}

// LoadGraph 是历史调用点的空实现；引用图已由 MySQL 实时查询，不加载 graph.json。
func LoadGraph(_ string) {}
