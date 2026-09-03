package handlers

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"scwiki/server/models"

	"gorm.io/gorm"
)

const (
	paperHistoryUploaded = "uploaded"
	paperHistoryModified = "modified"
	paperHistoryReviewed = "reviewed"
)

type paperHistoryInput struct {
	PaperID                uint
	PaperRevision          uint
	EventType              string
	Actor                  *models.User
	ReviewStatus           *string
	ReviewComment          *string
	OperationID            *string
	OccurredAt             time.Time
	ClassificationSnapshot []byte
}

func paperHistoryOperationExists(tx *gorm.DB, operationID string) (bool, error) {
	if operationID == "" {
		return false, nil
	}
	var count int64
	if err := tx.Model(&models.PaperHistoryEvent{}).
		Where("operation_id = ?", operationID).Count(&count).Error; err != nil {
		return false, err
	}
	return count > 0, nil
}

// appendPaperHistoryEvent 以 operation_id 实现请求重试与两段保存的幂等。
// 调用方必须已处于论文业务事务中，事件和论文最终状态因此同时提交或回滚。
func appendPaperHistoryEvent(tx *gorm.DB, input paperHistoryInput) (bool, error) {
	if input.PaperRevision < 1 {
		return false, errors.New("论文版本必须大于等于 1")
	}
	if input.OperationID != nil && len(*input.OperationID) > 64 {
		return false, errors.New("history_operation_id 过长")
	}
	if input.EventType != paperHistoryUploaded && input.EventType != paperHistoryModified && input.EventType != paperHistoryReviewed {
		return false, errors.New("不支持的文献处理事件类型")
	}
	if input.EventType == paperHistoryReviewed {
		if input.ReviewStatus == nil || !isValidReviewStatus(*input.ReviewStatus) {
			return false, errors.New("审核事件必须包含有效审核结果")
		}
	} else if input.ReviewStatus != nil || input.ReviewComment != nil {
		return false, errors.New("上传和修改事件不得包含审核结果或审核意见")
	}
	if input.EventType != paperHistoryUploaded && input.Actor == nil {
		return false, errors.New("修改和审核事件必须包含操作者")
	}
	if input.OperationID != nil && *input.OperationID != "" {
		exists, err := paperHistoryOperationExists(tx, *input.OperationID)
		if err != nil {
			return false, err
		}
		if exists {
			return false, nil
		}
	}

	var actorID *uint
	var username *string
	if input.Actor != nil {
		actorID = &input.Actor.ID
		name := strings.TrimSpace(input.Actor.Username)
		if name != "" {
			username = &name
		}
	}
	occurredAt := input.OccurredAt
	if occurredAt.IsZero() {
		occurredAt = time.Now()
	}
	event := models.PaperHistoryEvent{
		PaperID: input.PaperID, PaperRevision: input.PaperRevision,
		EventType: input.EventType, ActorUserID: actorID,
		ActorUsernameSnapshot: username, ReviewStatus: input.ReviewStatus,
		ReviewComment: input.ReviewComment, OperationID: input.OperationID,
		OccurredAt: occurredAt, ClassificationSnapshot: input.ClassificationSnapshot,
	}
	if err := tx.Create(&event).Error; err != nil {
		if input.OperationID != nil && *input.OperationID != "" && strings.Contains(strings.ToLower(err.Error()), "duplicate") {
			return false, nil
		}
		return false, fmt.Errorf("写入文献处理历史失败: %w", err)
	}
	return true, nil
}
