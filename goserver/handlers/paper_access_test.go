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

// T040（Issue #76）：升版后的论文（content_revision 递增、approved_revision 清空、
// review_status 回到 pending）不再对外公开——匿名访问者不可见，上传者与管理员
// 仍按各自身份路径可见。
//
// 注：登录的非上传者用户查看 pending 论文详情是既有可见性语义（canViewPaper
// 的 pending 分支，TestCanViewPaperMatrix 锁定「logged pending → true」），
// 不属于本 Feature 的改动范围；本 Feature 保证的是「不对外公开」——
// 匿名不可见 + 公开查询（搜索/图表）不返回。
func TestRevisionBumpedPaperIsNotPublic(t *testing.T) {
	ownerID := uint(7)
	owner := &models.User{ID: ownerID, Role: "user", IsApproved: true}
	bumped := &models.Paper{
		ReviewStatus:    reviewStatusPending,
		ApprovedRevision: nil,
		ContentRevision: 2,
		UploadedBy:      &ownerID,
	}

	if canViewPaper(bumped, nil) {
		t.Fatal("升版后的论文对匿名访问者必须不可见")
	}
	if !canViewPaper(bumped, owner) {
		t.Fatal("升版后的论文对上传者应可见（我的论文）")
	}
	if !canViewPaper(bumped, &models.User{ID: 9, Role: "admin", IsApproved: true}) {
		t.Fatal("升版后的论文对管理员应可见")
	}
}
