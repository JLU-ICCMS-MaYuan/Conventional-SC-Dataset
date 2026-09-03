package handlers

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"scwiki/server/database"
	"scwiki/server/models"
)

type newsFeedLink struct {
	Source string `json:"source"`
	URL    string `json:"url"`
}

type newsFeedView struct {
	models.NewsFeedItem
	Authors []string       `json:"authors"`
	Links   []newsFeedLink `json:"links"`
	Notice  string         `json:"notice"`
}

func newsPageParameter(c *gin.Context, name string, fallback, maximum int) (int, bool) {
	value, err := strconv.Atoi(c.DefaultQuery(name, strconv.Itoa(fallback)))
	return value, err == nil && value > 0 && value <= maximum
}

// ListNewsFeed 只读取自动资讯表，旧人工快讯接口保持独立。
func ListNewsFeed(c *gin.Context) {
	page, validPage := newsPageParameter(c, "page", 1, 10000)
	size, validSize := newsPageParameter(c, "page_size", 20, 100)
	kind := c.Query("kind")
	if !validPage || !validSize || (kind != "" && kind != "news" && kind != "preprint" && kind != "journal_article") {
		c.JSON(http.StatusBadRequest, gin.H{"error": "资讯查询参数不合法"})
		return
	}
	fail := func() { c.JSON(http.StatusInternalServerError, gin.H{"error": "资讯读取失败，请稍后重试"}) }
	query := database.DB.WithContext(c.Request.Context()).Model(&models.NewsFeedItem{})
	if kind != "" {
		query = query.Where("CASE WHEN display_kind = '' THEN kind ELSE display_kind END = ?", kind)
	}
	var total int64
	if err := query.Count(&total).Error; err != nil {
		fail()
		return
	}
	rows := make([]models.NewsFeedItem, 0)
	if err := query.Order("published_at DESC").Order("first_seen_at DESC").Order("id DESC").Limit(size).Offset((page - 1) * size).Find(&rows).Error; err != nil {
		fail()
		return
	}
	items := make([]newsFeedView, 0, len(rows))
	for _, row := range rows {
		item := newsFeedView{NewsFeedItem: row, Authors: []string{}, Links: []newsFeedLink{}, Notice: "自动采集，未经本站审核"}
		if json.Unmarshal([]byte(row.Authors), &item.Authors) != nil || json.Unmarshal([]byte(row.Links), &item.Links) != nil {
			fail()
			return
		}
		if item.Authors == nil {
			item.Authors = []string{}
		}
		if item.Links == nil {
			item.Links = []newsFeedLink{}
		}
		items = append(items, item)
	}
	states := make([]models.NewsFeedSource, 0)
	if err := database.DB.WithContext(c.Request.Context()).Find(&states).Error; err != nil {
		fail()
		return
	}
	sources := make([]models.NewsFeedSource, 0, 3)
	for _, candidate := range states {
		if candidate.Source != "" {
			sources = append(sources, candidate)
		}
	}
	for _, name := range []string{"arxiv", "crossref", "openalex", "aps", "acs", "nature", "science", "nsr", "cpl", "cpb", "materials_today", "physorg", "google_news"} {
		found := false
		for _, candidate := range sources {
			if candidate.Source == name {
				found = true
				break
			}
		}
		if found {
			continue
		}
		state := models.NewsFeedSource{Source: name, Status: "never"}
		sources = append(sources, state)
	}
	c.Header("Cache-Control", "no-store")
	c.JSON(http.StatusOK, gin.H{"items": items, "total": total, "page": page, "page_size": size, "sources": sources})
}
