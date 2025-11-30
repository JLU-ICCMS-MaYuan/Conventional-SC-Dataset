# 管理员审核系统使用指南

## 📋 系统概述

超导文献数据库现已集成完整的管理员审核系统，支持：
- ✅ 管理员注册与邮箱验证
- ✅ 超级管理员审批机制
- ✅ 文献审核状态追踪
- ✅ 开放贡献（匿名上传标记为未审核）
- ✅ JWT 认证与权限控制

---

## 🚀 快速开始

### 1. 创建超级管理员

首次部署后，需要创建第一个超级管理员账户：

```bash
# 交互式创建
python -m backend.create_superadmin

# 或使用环境变量
export SUPERADMIN_EMAIL="admin@example.com"
export SUPERADMIN_PASSWORD="your_secure_password"
export SUPERADMIN_NAME="管理员姓名"
python -m backend.create_superadmin
```

### 2. SMTP 邮箱配置（可选）

如需启用邮箱验证功能，配置环境变量：

```bash
export SMTP_SERVER="smtp.qq.com"          # SMTP 服务器地址
export SMTP_PORT="587"                     # SMTP 端口（TLS）
export SMTP_USERNAME="your_email@qq.com"  # 邮箱账号
export SMTP_PASSWORD="your_auth_code"     # 邮箱授权码（不是密码！）
export SMTP_SENDER_EMAIL="your_email@qq.com"
```

**注意**：QQ邮箱/163邮箱需要使用授权码，不是登录密码。

**开发模式**：如果未配置 SMTP，验证码会打印到控制台。

### 3. JWT 密钥配置（生产环境必须）

```bash
export JWT_SECRET_KEY="your-random-secret-key-min-32-chars"
```

---

## 👥 用户角色

### 1. 匿名用户
- 可以浏览所有文献（包括未审核文献）
- 可以上传文献（标记为未审核）
- 可以筛选查看已审核/未审核文献

### 2. 管理员（Admin）
- 拥有匿名用户所有权限
- 可以审核文献（标记为已审核）
- 可以取消审核状态
- 查看自己审核过的文献

### 3. 超级管理员（Superadmin）
- 拥有管理员所有权限
- 审批新管理员申请
- 查看所有管理员列表
- 管理员统计信息

---

## 📝 注册与审批流程

### 管理员注册流程：

1. 访问 `/admin/register`
2. 填写邮箱、真实姓名、密码
3. 点击"发送验证码"，系统发送 6 位验证码到邮箱
4. 输入验证码完成邮箱验证
5. **等待超级管理员审批**

### 超级管理员审批流程：

1. 登录 `/admin/login`
2. 系统自动跳转到 `/admin/superadmin`
3. 在"待审批管理员"标签页查看申请
4. 点击"批准"或"拒绝"
5. 系统自动发送邮件通知申请人

---

## 🔍 文献审核流程

### 1. 查看待审核文献

管理员登录后：
1. 访问 `/admin/dashboard`
2. 查看"待审核文献列表"
3. 每篇文献显示：标题、DOI、期刊、贡献者、提交时间

### 2. 审核操作

- 点击"查看原文"：跳转到 DOI 链接查看完整论文
- 点击"标记为已审核"：确认文献质量后标记
- 系统自动记录审核人姓名和时间

### 3. 审核状态展示

文献列表中会显示徽章：
- ✅ 已审核 (审核人姓名) - 绿色
- ⏳ 未审核 - 黄色

用户可通过筛选按钮选择：
- 全部文献
- 仅已审核
- 仅未审核

---

## 🔐 API 端点

### 认证 API (`/api/auth/`)

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/auth/register` | POST | 注册管理员（第一步：发送验证码） | 公开 |
| `/api/auth/verify-email` | POST | 验证邮箱（第二步：验证码验证） | 公开 |
| `/api/auth/login` | POST | 登录获取 JWT token | 公开 |
| `/api/auth/me` | GET | 获取当前用户信息 | 需登录 |

### 管理员 API (`/api/admin/`)

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/admin/pending-approvals` | GET | 获取待审批管理员列表 | 超级管理员 |
| `/api/admin/approve-user` | POST | 审批管理员申请 | 超级管理员 |
| `/api/admin/all-admins` | GET | 获取所有管理员 | 超级管理员 |
| `/api/admin/papers/{id}/review` | POST | 标记文献为已审核 | 管理员 |
| `/api/admin/papers/{id}/unreview` | POST | 取消审核状态 | 管理员 |
| `/api/admin/papers/unreviewed` | GET | 获取未审核文献列表 | 管理员 |
| `/api/admin/my-reviews` | GET | 获取我审核的文献 | 管理员 |

### 文献查询 API

| 参数 | 说明 | 示例 |
|------|------|------|
| `review_status` | 审核状态筛选 | `reviewed` / `unreviewed` |

示例：
```bash
GET /api/papers/compound/Ba-Cu-O-Y?review_status=reviewed
```

---

## 📊 数据库模型

### User 表

```python
- id: 主键
- email: 邮箱（唯一）
- password_hash: 密码哈希（bcrypt）
- real_name: 真实姓名
- is_admin: 是否为管理员
- is_superadmin: 是否为超级管理员
- is_approved: 是否已审批
- is_email_verified: 邮箱是否已验证
- verification_code: 验证码
- verification_expires: 验证码过期时间
- created_at: 创建时间
- approved_at: 审批时间
- approved_by: 审批人 ID
```

### Paper 表新增字段

```python
- review_status: 审核状态 ('reviewed' / 'unreviewed')
- reviewed_by: 审核人 ID（外键 → User）
- reviewed_at: 审核时间
```

---

## 🛠️ 常见问题

### 1. 忘记超级管理员密码？

重新运行创建脚本，同一邮箱会升级为超级管理员：
```bash
python -m backend.create_superadmin
```

### 2. 收不到验证码邮件？

- 检查 SMTP 配置是否正确
- QQ/163 邮箱需使用授权码，不是登录密码
- 查看服务器日志，开发模式下验证码会打印到控制台

### 3. 如何查看所有管理员？

超级管理员登录后，访问 `/admin/superadmin`，切换到"已批准管理员"标签页。

### 4. 如何重置数据库？

```bash
# 删除旧数据库
rm data/superconductor.db

# 重新初始化
python -m backend.init_db

# 重新创建超级管理员
python -m backend.create_superadmin
```

---

## 🔒 安全建议

1. **生产环境必须更改 JWT 密钥**
   ```bash
   export JWT_SECRET_KEY="生成一个32+字符的随机密钥"
   ```

2. **启用 HTTPS**（Railway 自动提供）

3. **定期审查管理员权限**

4. **保护 SMTP 授权码**
   - 不要提交到 Git
   - 使用环境变量或密钥管理服务

5. **监控日志**
   - 查看异常登录尝试
   - 监控大量审核操作

---

## 📱 前端页面

| 页面 | 路径 | 说明 |
|------|------|------|
| 管理员登录 | `/admin/login` | JWT 登录界面 |
| 管理员注册 | `/admin/register` | 两步注册流程 |
| 管理员审核面板 | `/admin/dashboard` | 审核待审核文献 |
| 超级管理员面板 | `/admin/superadmin` | 审批管理员申请 |
| 我审核的文献 | `/admin/my-reviews` | 查看审核历史 |

---

## 🎯 开发者说明

吉林大学物理学院 马原
邮箱：mayuan@calypso.org.cn

系统使用 FastAPI + SQLAlchemy + JWT + SMTP 实现完整的权限管理。

技术栈：
- 后端：FastAPI, SQLAlchemy, python-jose, passlib
- 前端：Bootstrap 5, 原生 JavaScript
- 数据库：SQLite
- 认证：JWT Bearer Token
- 邮件：SMTP (QQ/163邮箱)
