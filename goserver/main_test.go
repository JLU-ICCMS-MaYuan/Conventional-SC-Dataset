package main

import (
	"compress/gzip"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestGzipMiddlewareDropsLateContentLength(t *testing.T) {
	gin.SetMode(gin.TestMode)
	payload := strings.Repeat("response-body-", 100)

	router := gin.New()
	router.Use(gzipMiddleware)
	router.GET("/proxy", func(c *gin.Context) {
		c.Header("Content-Length", strconv.Itoa(len(payload)))
		c.String(http.StatusOK, payload)
	})

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/proxy", nil)
	request.Header.Set("Accept-Encoding", "gzip")
	router.ServeHTTP(recorder, request)

	if got := recorder.Header().Get("Content-Length"); got != "" {
		t.Fatalf("compressed response retained stale Content-Length %q", got)
	}
	reader, err := gzip.NewReader(recorder.Body)
	if err != nil {
		t.Fatal(err)
	}
	decompressed, err := io.ReadAll(reader)
	if err != nil {
		t.Fatal(err)
	}
	if string(decompressed) != payload {
		t.Fatalf("unexpected response body length: got %d want %d", len(decompressed), len(payload))
	}
}
