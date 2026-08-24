package handlers

import (
	"bytes"
	cryptorand "crypto/rand"
	"encoding/hex"
	"encoding/json"
	"image"
	"image/color"
	"image/jpeg"
	_ "image/png"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
	_ "golang.org/x/image/webp"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

func accountProfilePayload(user models.User) gin.H {
	var interests []string
	if len(user.ResearchInterests) > 0 {
		_ = json.Unmarshal(user.ResearchInterests, &interests)
	}
	return gin.H{
		"id": user.ID, "email": user.Email, "username": user.Username,
		"username_change_allowed": user.UsernameChangeAllowed,
		"real_name":               user.RealName, "affiliation": user.Affiliation,
		"orcid": user.ORCID, "research_interests": interests,
		"avatar_url": avatarURL(user), "role": user.Role,
		"is_email_verified": user.IsEmailVerified, "account_status": user.AccountStatus,
	}
}

func GetAccountProfile(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	c.JSON(200, accountProfilePayload(*user))
}

func normalizeORCID(value string) (string, bool) {
	value = strings.ToUpper(strings.TrimSpace(value))
	if value == "" {
		return "", true
	}
	if len(value) != 19 || value[4] != '-' || value[9] != '-' || value[14] != '-' {
		return "", false
	}
	digits := strings.ReplaceAll(value, "-", "")
	if len(digits) != 16 {
		return "", false
	}
	total := 0
	for i := 0; i < 15; i++ {
		if digits[i] < '0' || digits[i] > '9' {
			return "", false
		}
		total = (total + int(digits[i]-'0')) * 2
	}
	remainder := total % 11
	result := (12 - remainder) % 11
	check := byte('0' + result)
	if result == 10 {
		check = 'X'
	}
	return value, digits[15] == check
}

func normalizeInterests(values []string) ([]string, bool) {
	if len(values) > 10 {
		return nil, false
	}
	seen := map[string]bool{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || len([]rune(value)) > 30 {
			return nil, false
		}
		if !seen[value] {
			seen[value] = true
			result = append(result, value)
		}
	}
	return result, true
}

func stringPointer(value string) *string {
	value = strings.TrimSpace(value)
	if value == "" {
		return nil
	}
	return &value
}

func UpdateAccountProfile(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		RealName          *string   `json:"real_name"`
		Affiliation       *string   `json:"affiliation"`
		ORCID             *string   `json:"orcid"`
		ResearchInterests *[]string `json:"research_interests"`
	}
	if c.ShouldBindJSON(&body) != nil {
		c.JSON(400, gin.H{"error": "参数错误"})
		return
	}
	updates := map[string]any{}
	if body.RealName != nil {
		value := strings.TrimSpace(*body.RealName)
		if len([]rune(value)) > 100 {
			c.JSON(400, gin.H{"error": "真实姓名最多 100 个字符"})
			return
		}
		updates["real_name"] = value
	}
	if body.Affiliation != nil {
		value := strings.TrimSpace(*body.Affiliation)
		if len([]rune(value)) > 255 {
			c.JSON(400, gin.H{"error": "所属机构最多 255 个字符"})
			return
		}
		updates["affiliation"] = stringPointer(value)
	}
	if body.ORCID != nil {
		value, valid := normalizeORCID(*body.ORCID)
		if !valid {
			c.JSON(400, gin.H{"error": "ORCID 格式或校验位错误"})
			return
		}
		updates["orcid"] = stringPointer(value)
	}
	if body.ResearchInterests != nil {
		values, valid := normalizeInterests(*body.ResearchInterests)
		if !valid {
			c.JSON(400, gin.H{"error": "研究方向最多 10 项，每项最多 30 个字符"})
			return
		}
		encoded, _ := json.Marshal(values)
		updates["research_interests"] = json.RawMessage(encoded)
	}
	if len(updates) == 0 {
		c.JSON(200, accountProfilePayload(*user))
		return
	}
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var locked models.User
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&locked, user.ID).Error; err != nil {
			return err
		}
		for field, oldValue := range map[string]*string{"real_name": stringPointer(locked.RealName), "affiliation": locked.Affiliation} {
			newRaw, changed := updates[field]
			if !changed {
				continue
			}
			var newValue *string
			switch value := newRaw.(type) {
			case string:
				newValue = stringPointer(value)
			case *string:
				newValue = value
			}
			oldText, newText := "", ""
			if oldValue != nil {
				oldText = *oldValue
			}
			if newValue != nil {
				newText = *newValue
			}
			if oldText != newText {
				if err := tx.Create(&models.ProfileChangeAuditEvent{TargetUserID: locked.ID, ChangedByUserID: locked.ID, FieldName: field, OldValue: oldValue, NewValue: newValue}).Error; err != nil {
					return err
				}
			}
		}
		return tx.Model(&locked).Updates(updates).Error
	})
	if err != nil {
		if isDuplicateKeyError(err) {
			c.JSON(409, gin.H{"error": "ORCID 已绑定其他账号"})
		} else {
			c.JSON(500, gin.H{"error": "资料保存失败"})
		}
		return
	}
	database.DB.First(user, user.ID)
	c.JSON(200, accountProfilePayload(*user))
}

func UploadAvatar(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	file, _, err := c.Request.FormFile("avatar")
	if err != nil {
		c.JSON(400, gin.H{"error": "请选择头像文件"})
		return
	}
	defer file.Close()
	data, err := io.ReadAll(io.LimitReader(file, 2*1024*1024+1))
	if err != nil || len(data) > 2*1024*1024 {
		c.JSON(400, gin.H{"error": "头像最大 2 MiB"})
		return
	}
	config, _, err := image.DecodeConfig(bytes.NewReader(data))
	if err != nil || config.Width <= 0 || config.Height <= 0 || config.Width > 8192 || config.Height > 8192 || int64(config.Width)*int64(config.Height) > 25_000_000 {
		c.JSON(400, gin.H{"error": "头像格式或尺寸无效"})
		return
	}
	source, format, err := image.Decode(bytes.NewReader(data))
	if err != nil || (format != "jpeg" && format != "png" && format != "webp") {
		c.JSON(400, gin.H{"error": "仅支持 JPEG、PNG、WebP"})
		return
	}
	bounds := source.Bounds()
	side := bounds.Dx()
	if bounds.Dy() < side {
		side = bounds.Dy()
	}
	offsetX := bounds.Min.X + (bounds.Dx()-side)/2
	offsetY := bounds.Min.Y + (bounds.Dy()-side)/2
	destination := image.NewRGBA(image.Rect(0, 0, 512, 512))
	for y := 0; y < 512; y++ {
		for x := 0; x < 512; x++ {
			sx := offsetX + x*side/512
			sy := offsetY + y*side/512
			pixel := color.RGBAModel.Convert(source.At(sx, sy)).(color.RGBA)
			destination.SetRGBA(x, y, pixel)
		}
	}
	random := make([]byte, 16)
	if _, err := cryptorand.Read(random); err != nil {
		c.JSON(500, gin.H{"error": "头像保存失败"})
		return
	}
	key := hex.EncodeToString(random) + ".jpg"
	tempPath := filepath.Join(avatarDir, key+".tmp")
	finalPath := filepath.Join(avatarDir, key)
	out, err := os.OpenFile(tempPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o640)
	if err != nil {
		c.JSON(500, gin.H{"error": "头像保存失败"})
		return
	}
	err = jpeg.Encode(out, destination, &jpeg.Options{Quality: 88})
	closeErr := out.Close()
	if err != nil || closeErr != nil || os.Rename(tempPath, finalPath) != nil {
		_ = os.Remove(tempPath)
		c.JSON(500, gin.H{"error": "头像保存失败"})
		return
	}
	old := user.AvatarKey
	if err := database.DB.Model(user).Update("avatar_key", key).Error; err != nil {
		_ = os.Remove(finalPath)
		c.JSON(500, gin.H{"error": "头像保存失败"})
		return
	}
	if old != nil {
		_ = os.Remove(filepath.Join(avatarDir, filepath.Base(*old)))
	}
	user.AvatarKey = &key
	c.JSON(200, gin.H{"avatar_url": avatarURL(*user)})
}

func DeleteAvatar(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	old := user.AvatarKey
	if err := database.DB.Model(user).Update("avatar_key", nil).Error; err != nil {
		c.JSON(500, gin.H{"error": "头像删除失败"})
		return
	}
	if old != nil {
		_ = os.Remove(filepath.Join(avatarDir, filepath.Base(*old)))
	}
	c.Status(http.StatusNoContent)
}

func ChangePassword(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		CurrentPassword string `json:"current_password"`
		NewPassword     string `json:"new_password"`
	}
	if c.ShouldBindJSON(&body) != nil || len(body.NewPassword) < 10 {
		c.JSON(400, gin.H{"error": "新密码至少 10 位"})
		return
	}
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var locked models.User
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&locked, user.ID).Error; err != nil {
			return err
		}
		if bcrypt.CompareHashAndPassword([]byte(locked.PasswordHash), []byte(body.CurrentPassword)) != nil {
			return gorm.ErrInvalidData
		}
		hash, err := bcrypt.GenerateFromPassword([]byte(body.NewPassword), bcrypt.DefaultCost)
		if err != nil {
			return err
		}
		return tx.Model(&locked).Updates(map[string]any{"password_hash": string(hash), "session_version": gorm.Expr("session_version + 1"), "updated_at": time.Now()}).Error
	})
	if err == gorm.ErrInvalidData {
		c.JSON(403, gin.H{"error": "当前密码错误"})
		return
	}
	if err != nil {
		c.JSON(500, gin.H{"error": "密码修改失败"})
		return
	}
	c.Status(http.StatusNoContent)
}
