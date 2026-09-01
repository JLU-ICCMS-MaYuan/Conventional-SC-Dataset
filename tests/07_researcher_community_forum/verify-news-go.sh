#!/usr/bin/env bash
set -euo pipefail
# 仅使用本次独立测试容器的端口，不能传入生产凭证或 DSN。
news_test_port="${1:?需要隔离 MySQL 端口}"
[[ "$news_test_port" =~ ^[0-9]+$ ]] || exit 2
news_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
news_test_mode="${2:-test}"
news_test_run="News"
news_test_address=""
news_test_image="${NEWS_TEST_GO_IMAGE:-golang:1.25}"
if [[ "$news_test_mode" == "preview" ]]; then
  news_test_run="TestNewsFeedBrowserPreview"
  news_test_address="127.0.0.1:5183"
fi
docker run --rm --network host \
  -e "NEWS_TEST_MYSQL_DSN=root:news-test-only@tcp(127.0.0.1:${news_test_port})/news_test?parseTime=true" \
  -e "NEWS_TEST_PREVIEW_ADDRESS=${news_test_address}" \
  -v "${news_repo_root}/goserver:/src/goserver" \
  -v "${news_repo_root}/frontend/static:/preview:ro" \
  -w "/src/goserver" "$news_test_image" \
  go test handlers/news.go handlers/news_feed.go handlers/news_feed_test.go -run "$news_test_run" -count=1 -timeout=20m -v
