package handlers

import (
	"testing"

	"scwiki/server/models"
)

func TestCanViewPaperMatrix(t *testing.T) {
	ownerID := uint(7)
	owner := &models.User{ID: ownerID, Role: "user", IsApproved: true}
	other := &models.User{ID: 8, Role: "user", IsApproved: true}
	admin := &models.User{ID: 9, Role: "admin", IsApproved: true}
	cases := []struct {
		name   string
		status string
		user   *models.User
		want   bool
	}{
		{"anonymous approved", reviewStatusApproved, nil, true},
		{"anonymous pending", reviewStatusPending, nil, false},
		{"logged pending", reviewStatusPending, other, true},
		{"other rejected", reviewStatusRejected, other, false},
		{"owner rejected", reviewStatusRejected, owner, true},
		{"admin rejected", reviewStatusRejected, admin, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			paper := models.Paper{ReviewStatus: tc.status, UploadedBy: &ownerID}
			if got := canViewPaper(&paper, tc.user); got != tc.want {
				t.Fatalf("got %v want %v", got, tc.want)
			}
		})
	}
}

func TestPaperForViewerFiltersReviewFields(t *testing.T) {
	ownerID := uint(7)
	comment, internal := "请补充页码", "内部风控备注"
	paper := models.Paper{
		ReviewStatus: reviewStatusRejected, UploadedBy: &ownerID,
		ReviewComment: &comment, AdminInternalNote: &internal,
	}
	other := &models.User{ID: 8, Role: "user", IsApproved: true}
	owner := &models.User{ID: ownerID, Role: "user", IsApproved: true}
	admin := &models.User{ID: 9, Role: "admin", IsApproved: true}

	if _, exists := paperForViewer(paper, other)["review_comment"]; exists {
		t.Fatal("其他用户不应看到审核意见")
	}
	if _, exists := paperForViewer(paper, owner)["review_comment"]; !exists {
		t.Fatal("上传者应看到审核意见")
	}
	if _, exists := paperForViewer(paper, owner)["admin_internal_note"]; exists {
		t.Fatal("上传者不应看到内部备注")
	}
	if _, exists := paperForViewer(paper, admin)["admin_internal_note"]; !exists {
		t.Fatal("管理员应看到内部备注")
	}
}
