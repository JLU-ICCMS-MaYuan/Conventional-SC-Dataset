# Go 后端 — 多阶段构建
FROM golang:1.25-alpine AS builder

ENV GOPROXY=https://goproxy.cn,direct

WORKDIR /build
COPY goserver/go.mod goserver/go.sum ./
RUN go mod download
COPY goserver/ .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o goserver .

FROM alpine:3.21
RUN apk add --no-cache ca-certificates tzdata
WORKDIR /app
COPY --from=builder /build/goserver .
EXPOSE 8080
CMD ["./goserver"]
