package handlers

import (
	"net/http"
	"strconv"
	"strings"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

var validGraphMarkTypes = map[string]struct{}{
	"origin": {}, "breakthrough": {},
}

// ReplacePaperGraphMarks 整体替换管理员确认的领域里程碑。引用关系不允许
// 人工写入；这里仅维护无法由被引量自动判断的源头和突破。
func ReplacePaperGraphMarks(c *gin.Context) {
	parsedID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil || parsedID == 0 {
		graphError(c, http.StatusBadRequest, "invalid_graph_mark", "论文 ID 无效")
		return
	}
	var body struct {
		Marks []string `json:"marks"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Marks == nil {
		graphError(c, http.StatusBadRequest, "invalid_graph_mark", "marks 必须是数组")
		return
	}
	marks := make([]string, 0, len(body.Marks))
	seen := map[string]bool{}
	for _, mark := range body.Marks {
		mark = strings.TrimSpace(mark)
		if _, ok := validGraphMarkTypes[mark]; !ok {
			graphError(c, http.StatusBadRequest, "invalid_graph_mark", "marks 只允许 origin 或 breakthrough")
			return
		}
		if !seen[mark] {
			seen[mark] = true
			marks = append(marks, mark)
		}
	}

	email, exists := c.Get("user_email")
	if !exists {
		graphError(c, http.StatusUnauthorized, "unauthorized", "未登录")
		return
	}
	var actor models.User
	if err := database.DB.Where("email = ?", email).First(&actor).Error; err != nil {
		graphError(c, http.StatusUnauthorized, "unauthorized", "用户不存在")
		return
	}
	paperID := uint(parsedID)
	err = database.DB.Transaction(func(tx *gorm.DB) error {
		var paper models.Paper
		if err := tx.First(&paper, paperID).Error; err != nil {
			return err
		}
		if paper.ReviewStatus != reviewStatusApproved || paper.ApprovedRevision == nil || *paper.ApprovedRevision != paper.ContentRevision {
			return errPaperGraphMarkNotApproved
		}
		if err := tx.Where("paper_id = ?", paperID).Delete(&models.PaperGraphMark{}).Error; err != nil {
			return err
		}
		for _, mark := range marks {
			if err := tx.Create(&models.PaperGraphMark{
				PaperID: paperID, MarkType: mark, CreatedByUserID: actor.ID,
			}).Error; err != nil {
				return err
			}
		}
		return nil
	})
	if err == gorm.ErrRecordNotFound {
		graphError(c, http.StatusNotFound, "paper_not_found", "论文不存在")
		return
	}
	if err == errPaperGraphMarkNotApproved {
		graphError(c, http.StatusConflict, "paper_not_approved", "只有当前已审核论文可以标记")
		return
	}
	if err != nil {
		graphError(c, http.StatusInternalServerError, "graph_mark_write_failed", "保存图谱里程碑失败")
		return
	}
	c.JSON(http.StatusOK, gin.H{"paper_id": paperID, "marks": marks})
}

var errPaperGraphMarkNotApproved = &paperGraphMarkNotApprovedError{}

type paperGraphMarkNotApprovedError struct{}

func (*paperGraphMarkNotApprovedError) Error() string {
	return "paper graph mark requires approved paper"
}
