# SC-Wiki Docker 部署包

## 文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| `compose.yaml` | 3.5 KB | Docker Compose 编排（7 个服务，全部从 Docker Hub 拉镜像） |
| `.env.example` | - | 环境变量模板，复制为 `.env` 填入密钥 |
| `mysql-export.sql` | 91 MB | MySQL 全量导出 |
| `neo4j-dump/` | 908 KB | Neo4j 知识图谱导出 |
| `data-files.tar.gz` | 632 MB | Qdrant + graph.json + uploads + clean_results |

## Docker Hub 镜像

| 镜像 | 大小 |
|------|------|
| `str3num/scwiki-goserver:v1.0` | 14 MB |
| `str3num/scwiki-frontend:v1.0` | 27 MB |
| `str3num/scwiki-python:v1.0` | 219 MB |
| `mysql:8.4` | 官方 |
| `redis:7-alpine` | 官方 |
| `neo4j:5` | 官方 |
| `qdrant/qdrant:latest` | 官方 |

## 部署步骤

### 0. 装 Docker

```bash
curl -fsSL https://get.docker.com | sh
```

### 1. 上传到服务器

```bash
scp deploy.tar.gz user@服务器IP:/opt/scwiki/
cd /opt/scwiki
tar xzf deploy.tar.gz
cd deploy
```

### 2. 配置环境变量

```bash
cp .env.example .env
nano .env   # 填入真实密钥
```

### 3. 解压数据文件

```bash
tar xzf data-files.tar.gz
# 得到 data/ 目录（Qdrant、graph.json、uploads 等）
```

### 4. 拉取镜像

```bash
docker compose pull
```

### 5. 启动数据库容器

```bash
docker compose up -d mysql neo4j redis qdrant
# 等待 healthy 状态
docker compose ps
```

### 6. 导入 MySQL

```bash
docker compose exec -T mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD}" < mysql-export.sql
```

### 7. 导入 Neo4j

```bash
# 先把 dump 文件拷进容器
docker compose cp neo4j-dump/ neo4j:/backup/
# 导入（需要先停掉 neo4j）
docker compose stop neo4j
docker compose run --rm neo4j neo4j-admin database load neo4j --from-path=/backup/ --overwrite
docker compose up -d neo4j
```

### 8. 启动全部服务

```bash
docker compose up -d
docker compose ps   # 确认 7 个容器全部 running
```

### 9. 验证

```bash
curl http://localhost:80      # 前端
curl http://localhost:8080/health  # Go API
```

## 服务器目录结构

```
/opt/scwiki/deploy/
├── compose.yaml
├── .env
├── data/                    # 从 data-files.tar.gz 解压
│   ├── qdrant_storage/
│   ├── graph.json
│   ├── uploads/
│   ├── clean_results/
│   └── property_name_mapping.json
├── mysql-export.sql
└── neo4j-dump/
```

## 更新流程

代码更新后在开发机重新构建 + 推送新版本，然后在服务器：

```bash
docker compose pull          # 拉取新镜像
docker compose up -d         # 滚动重启（零停机）
```
