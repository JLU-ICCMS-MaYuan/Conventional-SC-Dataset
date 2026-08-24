package handlers

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

type publicProfileResponse struct {
	Username          string   `json:"username"`
	AvatarURL         *string  `json:"avatar_url,omitempty"`
	RealName          string   `json:"real_name,omitempty"`
	Affiliation       *string  `json:"affiliation,omitempty"`
	ORCID             *string  `json:"orcid,omitempty"`
	ResearchInterests []string `json:"research_interests,omitempty"`
	RoleBadge         string   `json:"role_badge,omitempty"`
	IsBanned          bool     `json:"is_banned,omitempty"`
}

func GetPublicProfile(c *gin.Context) {
	var user models.User
	if database.DB.Where("username = ?", c.Param("username")).First(&user).Error != nil || user.AccountStatus == "deactivated" {
		c.JSON(http.StatusNotFound, gin.H{"error": "用户不存在"})
		return
	}
	var interests []string
	if len(user.ResearchInterests) > 0 {
		_ = json.Unmarshal(user.ResearchInterests, &interests)
	}
	badge := ""
	if user.Role == "admin" {
		badge = "管理员"
	} else if user.Role == "superadmin" {
		badge = "超级管理员"
	}
	c.JSON(200, publicProfileResponse{Username: user.Username, AvatarURL: avatarURL(user), RealName: user.RealName, Affiliation: user.Affiliation, ORCID: user.ORCID, ResearchInterests: interests, RoleBadge: badge, IsBanned: user.AccountStatus == "banned"})
}

func GetPublicAvatar(c *gin.Context) {
	var user models.User
	if database.DB.Select("avatar_key", "account_status").Where("username = ?", c.Param("username")).First(&user).Error != nil || user.AccountStatus == "deactivated" || user.AvatarKey == nil {
		c.Status(http.StatusNotFound)
		return
	}
	key := filepath.Base(*user.AvatarKey)
	if key != *user.AvatarKey {
		c.Status(http.StatusNotFound)
		return
	}
	path := filepath.Join(avatarDir, key)
	if _, err := os.Stat(path); err != nil {
		c.Status(http.StatusNotFound)
		return
	}
	c.Header("Cache-Control", "public, max-age=3600")
	c.File(path)
}
