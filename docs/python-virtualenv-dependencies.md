# SC-Wiki Python 虚拟环境依赖清单

本文档只整理 Python 虚拟环境需要安装的库，方便重新安装或排查 `./start.sh` 启动失败。

## 1. 推荐安装命令

项目根目录已有 `requirements.txt`，优先使用：

```bash
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install "PyMuPDF>=1.23"
```

其中 `PyMuPDF` 对应代码里的 `import fitz`，当前 `requirements.txt` 没有列出，但 RAG PDF 提取模块会用到。

## 2. 核心服务启动依赖

这些库是 FastAPI 主服务、数据库连接、模板页面和认证流程需要的：

```text
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
jinja2==3.1.3
sqlalchemy==2.0.25
alembic==1.13.1
pymysql==1.1.0
pydantic==2.5.3
pydantic-settings==2.1.0
email-validator==2.3.0
bcrypt==4.0.1
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-dotenv==1.0.0
httpx==0.26.0
Pillow==10.2.0
```

## 3. RAG / AI / PDF 相关依赖

这些库用于 RAG、向量库、异步数据库、LLM 调用和 PDF 解析：

```text
openai>=1.0
chromadb>=0.5
aiosqlite>=0.20
asyncmy>=0.2
anyio
PyMuPDF>=1.23
```

说明：

- `PyMuPDF` 的导入名是 `fitz`。
- `anyio` 通常会被 FastAPI/httpx 间接安装，但测试和 `backend/api/rag.py` 都直接使用它，单独列出更稳。

## 4. 材料结构 / Tc 预测相关依赖

这些库用于 CIF/POSCAR 结构解析、材料结构处理和 Tc 预测实验接口：

```text
ase==3.22.1
numpy==1.26.4
pymatgen==2023.9.25
openpyxl==3.1.2
```

说明：

- `numpy==1.26.4` 是为了兼容当前 `pymatgen` 版本，避免 NumPy 2.x 兼容性问题。
- `openpyxl` 用于 Excel 导入/导出类维护操作。

## 5. 测试依赖

```text
pytest==8.2.2
httpx==0.26.0
anyio
```

## 6. 一条完整 pip 安装命令

如果不想分步骤，可以在虚拟环境里执行：

```bash
python -m pip install -U pip setuptools wheel
python -m pip install \
  "fastapi==0.109.0" \
  "uvicorn[standard]==0.27.0" \
  "python-multipart==0.0.6" \
  "jinja2==3.1.3" \
  "sqlalchemy==2.0.25" \
  "alembic==1.13.1" \
  "pymysql==1.1.0" \
  "httpx==0.26.0" \
  "openai>=1.0" \
  "chromadb>=0.5" \
  "aiosqlite>=0.20" \
  "asyncmy>=0.2" \
  "pydantic==2.5.3" \
  "pydantic-settings==2.1.0" \
  "email-validator==2.3.0" \
  "Pillow==10.2.0" \
  "bcrypt==4.0.1" \
  "passlib[bcrypt]==1.7.4" \
  "python-jose[cryptography]==3.3.0" \
  "python-dotenv==1.0.0" \
  "pytest==8.2.2" \
  "openpyxl==3.1.2" \
  "ase==3.22.1" \
  "numpy==1.26.4" \
  "pymatgen==2023.9.25" \
  "PyMuPDF>=1.23" \
  "anyio"
```

## 7. 启动前检查

```bash
python --version
python -m pip list
python -m alembic upgrade head
./start.sh
```

如果 `./start.sh` 报 `No module named ...`，优先检查该模块是否在上面的清单中，或是否是项目内文件缺失。
