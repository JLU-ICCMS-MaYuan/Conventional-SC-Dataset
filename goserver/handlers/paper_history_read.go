package handlers

import (
	"net/http"
	"strconv"
	"strings"
	"time"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

type paperHistoryActorResponse struct {
	Username *string `json:"username"`
	Unknown  bool    `json:"unknown"`
}

type paperHistoryReviewResponse struct {
	Status  string  `json:"status"`
	Comment *string `json:"comment"`
}

type paperHistoryEventResponse struct {
	ID            uint                        `json:"id"`
	EventType     string                      `json:"event_type"`
	PaperRevision uint                        `json:"paper_revision"`
	Actor         paperHistoryActorResponse   `json:"actor"`
	OccurredAt    time.Time                   `json:"occurred_at"`
	Review        *paperHistoryReviewResponse `json:"review"`
}

// GetPaperHistory 返回管理员可见的论文上传、修改、审核时间线。
// GET /api/admin/papers/:id/history
func GetPaperHistory(c *gin.Context) {
	paperID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil || paperID == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	var paper models.Paper
	if err := database.DB.Select("id").First(&paper, uint(paperID)).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	var events []models.PaperHistoryEvent
	if err := database.DB.Where("paper_id = ?", paper.ID).
		Order("occurred_at ASC").Order("id ASC").Find(&events).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "历史加载失败"})
		return
	}
	response := make([]paperHistoryEventResponse, 0, len(events))
	for _, event := range events {
		var actorName *string
		if event.ActorUsernameSnapshot != nil && strings.TrimSpace(*event.ActorUsernameSnapshot) != "" {
			name := *event.ActorUsernameSnapshot
			actorName = &name
		}
		item := paperHistoryEventResponse{
			ID: event.ID, EventType: event.EventType, PaperRevision: event.PaperRevision,
			Actor: paperHistoryActorResponse{
				Username: actorName,
				Unknown:  event.EventType == paperHistoryUploaded && actorName == nil,
			},
			OccurredAt: event.OccurredAt,
		}
		if event.EventType == paperHistoryReviewed && event.ReviewStatus != nil {
			item.Review = &paperHistoryReviewResponse{
				Status: *event.ReviewStatus, Comment: event.ReviewComment,
			}
		}
		response = append(response, item)
	}
	c.JSON(http.StatusOK, gin.H{"paper_id": paper.ID, "events": response})
}
