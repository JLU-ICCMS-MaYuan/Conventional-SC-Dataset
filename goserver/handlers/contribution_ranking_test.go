package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"scwiki/server/cache"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
)

func TestRankContributionRowsUsesStableOrderAndPublicFields(t *testing.T) {
	now := time.Now()
	rows := []contributionRow{
		{UserID: 2, DisplayName: "张三", ContributionCount: 5, ReachedAt: now},
		{UserID: 7, DisplayName: "李四", ContributionCount: 5, ReachedAt: now},
		{UserID: 9, DisplayName: "", ContributionCount: 1, ReachedAt: now},
	}
	ranks := rankContributionRows(rows)
	if len(ranks) != 3 || ranks[0].Rank != 1 || ranks[1].Rank != 2 {
		t.Fatalf("排名编号错误: %#v", ranks)
	}
	if ranks[0].AvatarText != "张" || ranks[2].DisplayName != "匿名贡献者" {
		t.Fatalf("公开展示字段错误: %#v", ranks)
	}
	if got := contributionRankForUser(ranks, 7); got == nil || got.Rank != 2 || got.ContributionCount != 5 {
		t.Fatalf("个人排名错误: %#v", got)
	}
	if got := contributionRankForUser(ranks, 100); got != nil {
		t.Fatalf("零贡献用户不应获得排名: %#v", got)
	}
}

func TestAvatarTextHandlesUnicodeAndBlankName(t *testing.T) {
	if got := avatarText("  Alice"); got != "A" {
		t.Fatalf("avatarText = %q", got)
	}
	if got := avatarText("王五"); got != "王" {
		t.Fatalf("avatarText = %q", got)
	}
	if got := avatarText("   "); got != "贡" {
		t.Fatalf("avatarText = %q", got)
	}
}

func TestTopContributionRanksKeepsFullPersonalRanking(t *testing.T) {
	ranks := make([]contributionRank, 25)
	for i := range ranks {
		ranks[i] = contributionRank{Rank: i + 1, UserID: uint(i + 1), DisplayName: "贡献者", ContributionCount: int64(25 - i)}
	}
	top := topContributionRanks(ranks, 20)
	if len(top) != 20 || top[19].Rank != 20 {
		t.Fatalf("Top 20 裁剪错误: %#v", top)
	}
	personal := contributionRankForUser(ranks, 25)
	if personal == nil || personal.Rank != 25 {
		t.Fatalf("Top 20 外个人排名丢失: %#v", personal)
	}
}

func TestContributionRankJSONDoesNotExposeSensitiveFields(t *testing.T) {
	data, err := json.Marshal(contributionRank{Rank: 1, UserID: 1, DisplayName: "贡献者", AvatarText: "贡", ContributionCount: 3})
	if err != nil {
		t.Fatal(err)
	}
	text := string(data)
	for _, forbidden := range []string{"email", "password", "role", "is_approved"} {
		if strings.Contains(text, forbidden) {
			t.Fatalf("公开响应泄露字段 %q: %s", forbidden, text)
		}
	}
}

func TestParseContributionRefresh(t *testing.T) {
	for _, test := range []struct {
		value        string
		force, valid bool
	}{
		{"", false, true}, {"false", false, true}, {"true", true, true}, {"1", false, false},
	} {
		force, valid := parseContributionRefresh(test.value)
		if force != test.force || valid != test.valid {
			t.Fatalf("parseContributionRefresh(%q) = (%v, %v)", test.value, force, valid)
		}
	}
}

func TestCommunityContributionsCacheTTLForceRefreshAndSingleFlight(t *testing.T) {
	redisServer := miniredis.RunT(t)
	cache.Connect(redisServer.Addr())
	oldLoader := contributionSnapshotLoader
	t.Cleanup(func() { contributionSnapshotLoader = oldLoader })

	var calls, active, maxActive atomic.Int32
	contributionSnapshotLoader = func() (contributionSnapshot, error) {
		current := active.Add(1)
		defer active.Add(-1)
		for {
			previous := maxActive.Load()
			if current <= previous || maxActive.CompareAndSwap(previous, current) {
				break
			}
		}
		time.Sleep(5 * time.Millisecond)
		count := calls.Add(1)
		return contributionSnapshot{ParticipantCount: int(count), GeneratedAt: time.Now()}, nil
	}

	request := func(query string) *httptest.ResponseRecorder {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/ranking", CommunityContributions)
		response := httptest.NewRecorder()
		router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/ranking"+query, nil))
		return response
	}
	if got := request(""); got.Code != http.StatusOK {
		t.Fatalf("initial status = %d", got.Code)
	}
	if got := request(""); got.Code != http.StatusOK || calls.Load() != 1 {
		t.Fatalf("cache miss: status=%d calls=%d", got.Code, calls.Load())
	}
	if got := request("?refresh=true"); got.Code != http.StatusOK || calls.Load() != 2 {
		t.Fatalf("force refresh failed: status=%d calls=%d", got.Code, calls.Load())
	}
	redisServer.FastForward(time.Hour + time.Second)
	if got := request(""); got.Code != http.StatusOK || calls.Load() != 3 {
		t.Fatalf("ttl refresh failed: status=%d calls=%d", got.Code, calls.Load())
	}

	var wait sync.WaitGroup
	for i := 0; i < 5; i++ {
		wait.Add(1)
		go func() { defer wait.Done(); request("?refresh=true") }()
	}
	wait.Wait()
	if maxActive.Load() != 1 {
		t.Fatalf("concurrent rebuilds = %d", maxActive.Load())
	}
}
