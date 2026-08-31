package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════════════
// 知识图谱 API — 代理到 Python Neo4j 实时查询
// ═══════════════════════════════════════════════

var kgPythonBackend string

func InitKnowledgeGraph() {
	kgPythonBackend = os.Getenv("PYTHON_BACKEND_URL")
	if kgPythonBackend == "" {
		kgPythonBackend = "http://python:8000"
	}
	println("[KG] 使用动态 Neo4j 数据源:", kgPythonBackend)
}

// KGOverview 图谱总览 — 代理到 Python
// GET /api/knowledge-graph/overview?limit=30
func KGOverview(c *gin.Context) {
	limit := c.DefaultQuery("limit", "30")
	url := fmt.Sprintf("%s/api/knowledge-graph-live/overview?limit=%s", kgPythonBackend, limit)

	resp, err := http.Get(url)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "无法连接到知识图谱服务", "detail": err.Error()})
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "读取响应失败"})
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "解析响应失败"})
		return
	}

	c.JSON(resp.StatusCode, result)
}

// KGPaperNeighbors 论文邻居节点 — 代理到 Python
// GET /api/knowledge-graph/papers/:paperId/neighbors?limit=10
func KGPaperNeighbors(c *gin.Context) {
	paperId := c.Param("paperId")
	limit := c.DefaultQuery("limit", "10")
	url := fmt.Sprintf("%s/api/knowledge-graph-live/papers/%s/neighbors?limit=%s",
		kgPythonBackend, paperId, limit)

	resp, err := http.Get(url)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "无法连接到知识图谱服务"})
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "读取响应失败"})
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "解析响应失败"})
		return
	}

	c.JSON(resp.StatusCode, result)
}

// KGStats 图谱统计 — 代理到 Python
// GET /api/knowledge-graph/stats
func KGStats(c *gin.Context) {
	url := fmt.Sprintf("%s/api/knowledge-graph-live/stats", kgPythonBackend)

	resp, err := http.Get(url)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "无法连接到知识图谱服务"})
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "读取响应失败"})
		return
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "解析响应失败"})
		return
	}

	c.JSON(resp.StatusCode, result)
}

// LoadGraph 兼容旧接口，实际不再加载静态文件
func LoadGraph(graphPath string) {
	println("[KG] 静态 graph.json 已弃用，使用动态 Neo4j 查询")
}
