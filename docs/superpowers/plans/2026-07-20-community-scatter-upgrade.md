# 社区散点图全面升级 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 升级社区页面两张散点图：形状编码超导类型(7种)、颜色编码实验/理论、引入组合管理系统(chart_groups)、支持自定义标注点。

**Architecture:** 后端新建 chart_groups + chart_group_items 两张表，提供 9 个 REST API；前端用 Recharts 渲染散点图，MUI Dialog 做组合编辑，每张图独立组合选择但共享全局筛选。

**Spec:** `docs/superpowers/specs/2026-07-20-community-scatter-upgrade-design.md`

**Tech Stack:** FastAPI + SQLAlchemy / React + Recharts + MUI

---

### Task 1: 数据模型

**Files:**
- Modify: `backend/models.py`（在 KeyProperty 类后追加）

- [ ] **Step 1: 新增 ChartGroup 和 ChartGroupItem 模型**

在 `backend/models.py` 的 `KeyProperty` 类定义之后，`SuperconductorRecord` 类之前，插入：

```python
class ChartGroup(Base):
    """散点图数据点组合"""
    __tablename__ = "chart_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_preset = Column(Boolean, default=False, nullable=False, index=True)
    is_public = Column(Boolean, default=False, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User")
    items = relationship("ChartGroupItem", back_populates="group", cascade="all, delete-orphan",
                         order_by="ChartGroupItem.sort_order")


class ChartGroupItem(Base):
    """组合内的数据点（kp 引用或自定义点）"""
    __tablename__ = "chart_group_items"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("chart_groups.id"), nullable=False, index=True)
    key_property_id = Column(Integer, ForeignKey("key_properties.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    # 自定义点字段（key_property_id 为空时生效）
    custom_label = Column(String(255))
    custom_tc = Column(Float)
    custom_pressure = Column(Float)
    custom_type = Column(String(20))
    custom_year = Column(Integer)

    group = relationship("ChartGroup", back_populates="items")
    key_property = relationship("KeyProperty")
```

- [ ] **Step 2: 创建迁移脚本**

新建 `backend/scripts/migrate_chart_groups.py`：

```python
"""创建 chart_groups / chart_group_items 表 + 预设数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import engine, SessionLocal
from backend.models import Base, ChartGroup, ChartGroupItem

Base.metadata.create_all(bind=engine, tables=[
    ChartGroup.__table__,
    ChartGroupItem.__table__,
])

db = SessionLocal()
# 预设组合（仅当表为空时创建）
if db.query(ChartGroup).filter(ChartGroup.is_preset == True).count() == 0:
    presets = [
        ChartGroup(name="高压氢化物 Tc>200K", description="所有 Tc>200K 的 hydride 数据点",
                   is_preset=True, is_public=True),
        ChartGroup(name="铜基超导 Tc>100K", description="所有 cuprate Tc>100K",
                   is_preset=True, is_public=True),
        ChartGroup(name="铁基超导", description="所有 iron_based 数据点",
                   is_preset=True, is_public=True),
        ChartGroup(name="近室温超导体", description="Tc>200K 的任意类型",
                   is_preset=True, is_public=True),
        ChartGroup(name="常压超导体", description="P<1GPa 的任意类型",
                   is_preset=True, is_public=True),
    ]
    db.add_all(presets)
    db.commit()
    print(f"已创建 {len(presets)} 个预设组合")

db.close()
print("完成")
```

- [ ] **Step 3: 运行迁移**

```bash
python backend/scripts/migrate_chart_groups.py
```

期望输出: `已创建 5 个预设组合` / `完成`

- [ ] **Step 4: 验证表结构**

```bash
python -c "
import sys; sys.path.insert(0,'.')
from backend.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
for t in ['chart_groups','chart_group_items']:
    cols = [c['name'] for c in inspector.get_columns(t)]
    print(f'{t}: {cols}')
"
```

期望输出:
```
chart_groups: ['id', 'name', 'description', 'is_preset', 'is_public', 'created_by', 'created_at', 'updated_at']
chart_group_items: ['id', 'group_id', 'key_property_id', 'sort_order', 'custom_label', 'custom_tc', 'custom_pressure', 'custom_type', 'custom_year']
```

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/scripts/migrate_chart_groups.py
git commit -m "feat: add ChartGroup/ChartGroupItem models and migration"
```

---

### Task 2: API 路由

**Files:**
- Create: `backend/api/chart_groups.py`

- [ ] **Step 1: 创建 API 文件**

```python
"""
Chart Group API — 散点图数据点组合管理
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.security import get_current_user

router = APIRouter(prefix="/api/chart-groups", tags=["图表组合"])


def _group_to_dict(g: models.ChartGroup) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "is_preset": g.is_preset,
        "is_public": g.is_public,
        "created_by": g.created_by,
        "creator_name": g.creator.real_name if g.creator else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
        "item_count": len(g.items),
        "items": [_item_to_dict(it) for it in g.items],
    }


def _item_to_dict(it: models.ChartGroupItem) -> dict:
    if it.key_property_id and it.key_property:
        kp = it.key_property
        return {
            "id": it.id,
            "sort_order": it.sort_order,
            "source": "kp",
            "key_property_id": kp.id,
            "material": kp.material,
            "tc": kp.value_max,
            "pressure": kp.pressure_gpa,
            "type": kp.superconductor_type,
            "year": it.key_property.paper.year if it.key_property.paper else None,
            "doi": it.key_property.paper.doi if it.key_property.paper else None,
            "article_type": kp.article_type,
        }
    else:
        return {
            "id": it.id,
            "sort_order": it.sort_order,
            "source": "custom",
            "key_property_id": None,
            "material": it.custom_label,
            "tc": it.custom_tc,
            "pressure": it.custom_pressure,
            "type": it.custom_type,
            "year": it.custom_year,
            "doi": None,
            "article_type": None,
        }


def _can_edit(g: models.ChartGroup, user: models.User) -> bool:
    """权限检查：创建者 / 管理员 / 超管可编辑"""
    if user.role == "superadmin":
        return True
    if user.role == "admin":
        return True
    if g.created_by == user.id:
        return True
    return False


def _can_set_public(user: models.User) -> bool:
    return user.role in ("admin", "superadmin")


def _can_delete(g: models.ChartGroup, user: models.User) -> bool:
    if user.role == "superadmin":
        return True
    if g.created_by == user.id:
        return True
    return False


# ── Pydantic ─────────────────────────────────────────

class ItemIn(BaseModel):
    key_property_id: Optional[int] = None
    custom_label: Optional[str] = None
    custom_tc: Optional[float] = None
    custom_pressure: Optional[float] = None
    custom_type: Optional[str] = None
    custom_year: Optional[int] = None


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: list[ItemIn] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[list[ItemIn]] = None


# ── Routes ───────────────────────────────────────────

@router.get("", summary="列表（公开+预设+自己的）")
def list_groups(db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    groups = db.query(models.ChartGroup).filter(
        (models.ChartGroup.is_public == True) |
        (models.ChartGroup.is_preset == True) |
        (models.ChartGroup.created_by == current_user.id)
    ).order_by(models.ChartGroup.is_preset.desc(), models.ChartGroup.updated_at.desc()).all()
    return [_group_to_dict(g) for g in groups]


@router.post("", summary="创建组合")
def create_group(body: GroupCreate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = models.ChartGroup(
        name=body.name, description=body.description,
        is_preset=False, is_public=False, created_by=current_user.id,
    )
    db.add(g)
    db.flush()
    for i, item in enumerate(body.items):
        db.add(models.ChartGroupItem(
            group_id=g.id, sort_order=i,
            key_property_id=item.key_property_id,
            custom_label=item.custom_label,
            custom_tc=item.custom_tc,
            custom_pressure=item.custom_pressure,
            custom_type=item.custom_type,
            custom_year=item.custom_year,
        ))
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.get("/{group_id}", summary="组合详情")
def get_group(group_id: int, db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_user)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    return _group_to_dict(g)


@router.put("/{group_id}", summary="更新组合")
def update_group(group_id: int, body: GroupUpdate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    if not _can_edit(g, current_user):
        raise HTTPException(status_code=403, detail="无权编辑此组合")
    if body.name is not None:
        g.name = body.name
    if body.description is not None:
        g.description = body.description
    if body.items is not None:
        # 全量替换 items
        db.query(models.ChartGroupItem).filter(
            models.ChartGroupItem.group_id == group_id
        ).delete()
        for i, item in enumerate(body.items):
            db.add(models.ChartGroupItem(
                group_id=g.id, sort_order=i,
                key_property_id=item.key_property_id,
                custom_label=item.custom_label,
                custom_tc=item.custom_tc,
                custom_pressure=item.custom_pressure,
                custom_type=item.custom_type,
                custom_year=item.custom_year,
            ))
    g.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.delete("/{group_id}", summary="删除组合")
def delete_group(group_id: int, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    if not _can_delete(g, current_user):
        raise HTTPException(status_code=403, detail="无权删除此组合")
    db.delete(g)
    db.commit()
    return {"message": "已删除"}


@router.post("/{group_id}/copy", summary="复制组合")
def copy_group(group_id: int, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):
    src = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="组合不存在")
    g = models.ChartGroup(
        name=f"{src.name} (副本)", description=src.description,
        is_preset=False, is_public=False, created_by=current_user.id,
    )
    db.add(g)
    db.flush()
    for item in src.items:
        db.add(models.ChartGroupItem(
            group_id=g.id, sort_order=item.sort_order,
            key_property_id=item.key_property_id,
            custom_label=item.custom_label,
            custom_tc=item.custom_tc,
            custom_pressure=item.custom_pressure,
            custom_type=item.custom_type,
            custom_year=item.custom_year,
        ))
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.get("/{group_id}/export", summary="导出组合 JSON")
def export_group(group_id: int, db: Session = Depends(get_db)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    return {
        "name": g.name,
        "description": g.description,
        "items": [
            {
                "type": "kp" if it.key_property_id else "custom",
                "key_property_id": it.key_property_id,
                "custom_label": it.custom_label,
                "custom_tc": it.custom_tc,
                "custom_pressure": it.custom_pressure,
                "custom_type": it.custom_type,
                "custom_year": it.custom_year,
            }
            for it in g.items
        ],
    }


@router.post("/import", summary="从 JSON 导入组合")
def import_group(body: dict, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = models.ChartGroup(
        name=body.get("name", "导入的组合"),
        description=body.get("description"),
        is_preset=False, is_public=False, created_by=current_user.id,
    )
    db.add(g)
    db.flush()
    for i, item in enumerate(body.get("items", [])):
        db.add(models.ChartGroupItem(
            group_id=g.id, sort_order=i,
            key_property_id=item.get("key_property_id") if item.get("type") == "kp" else None,
            custom_label=item.get("custom_label"),
            custom_tc=item.get("custom_tc"),
            custom_pressure=item.get("custom_pressure"),
            custom_type=item.get("custom_type"),
            custom_year=item.get("custom_year"),
        ))
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.patch("/{group_id}/public", summary="管理员切换公开状态")
def toggle_public(group_id: int, body: dict, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    if not _can_set_public(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可设置公开")
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    g.is_public = body.get("is_public", not g.is_public)
    db.commit()
    return {"message": "已更新", "is_public": g.is_public}
```

- [ ] **Step 2: 注册路由**

编辑 `backend/main.py`：

```python
# 在 import 区域追加
from backend.api import chart_groups

# 在 app.include_router 区域追加
app.include_router(chart_groups.router)
```

- [ ] **Step 3: 重启后端并测试创建组合**

```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 1
cd /home/work/workshop/git/SC-Wiki && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &>/tmp/backend.log &
sleep 3

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{"email":"admin@scwiki.org","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 测试列表
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/chart-groups | python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d),'groups')"

# 测试创建
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"测试组合","description":"test","items":[{"key_property_id":636},{"custom_label":"自定义点","custom_tc":300,"custom_pressure":200,"custom_type":"hydride"}]}' \
  http://127.0.0.1:8000/api/chart-groups | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['name'],'items:',d['item_count'])"
```

期望输出:
```
5 groups
测试组合 items: 2
```

- [ ] **Step 4: Commit**

```bash
git add backend/api/chart_groups.py backend/main.py
git commit -m "feat: add chart-groups API endpoints"
```

---

### Task 3: 图例配置与颜色映射

**Files:**
- Create: `frontend/src/lib/scatterConfig.ts`

- [ ] **Step 1: 创建图例配置文件**

```typescript
// 7 种超导类型的形状 + 颜色配置
export const SC_TYPE_CONFIG: Record<string, {
  label: string
  shape: 'triangle' | 'square' | 'diamond' | 'circle' | 'wye' | 'cross'
  colorExp: string   // 实验深色
  colorTheory: string // 理论浅色
}> = {
  hydride:       { label: '氢化物', shape: 'triangle', colorExp: '#4f46e5', colorTheory: '#a5b4fc' },
  cuprate:       { label: '铜基',   shape: 'square',   colorExp: '#dc2626', colorTheory: '#fca5a5' },
  iron_based:    { label: '铁基',   shape: 'diamond',  colorExp: '#ea580c', colorTheory: '#fdba74' },
  nickel_based:  { label: '镍基',   shape: 'circle',   colorExp: '#16a34a', colorTheory: '#86efac' },
  carbon:        { label: '碳基',   shape: 'wye',      colorExp: '#9333ea', colorTheory: '#c4b5fd' },
  organic:       { label: '有机',   shape: 'cross',    colorExp: '#0891b2', colorTheory: '#67e8f9' },
  others:        { label: '其他',   shape: 'diamond',  colorExp: '#64748b', colorTheory: '#cbd5e1' },
}

// data point 颜色获取
export function getPointColor(scType: string | null, articleType: string | null, opacity = 1): string {
  const cfg = SC_TYPE_CONFIG[scType || 'others'] || SC_TYPE_CONFIG.others
  const base = (articleType === 'e') ? cfg.colorExp : cfg.colorTheory
  return base + (opacity < 1 ? Math.round(opacity * 255).toString(16).padStart(2, '0') : '')
}

// 背景点半透明灰色
export const BACKGROUND_COLOR = '#d1d5db'
export const BACKGROUND_OPACITY = 0.15
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/scatterConfig.ts
git commit -m "feat: add scatter chart legend config"
```

---

### Task 4: 散点图组件 ChartScatter

**Files:**
- Create: `frontend/src/components/ChartScatter.tsx`

- [ ] **Step 1: 创建散点图组件**

```tsx
import React from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ZAxis,
} from 'recharts'
import { Box, Typography, Chip } from '@mui/material'
import {
  SC_TYPE_CONFIG, getPointColor,
  BACKGROUND_COLOR, BACKGROUND_OPACITY,
} from '../lib/scatterConfig'

interface DataPoint {
  x: number        // 实际 X 轴值
  y: number        // 实际 Y 轴值
  material: string
  scType: string
  articleType: string | null
  year: number | null
  doi: string | null
  isInGroup: boolean
  isCustom: boolean
  label: string
}

interface Props {
  title: string
  data: DataPoint[]
  xLabel: string
  yLabel: string
  xDomain?: [number, number | 'auto']
  yDomain?: [number, number | 'auto']
  visibleTypes: Set<string>
  showBackground: boolean
  onToggleType: (scType: string) => void
  tooltipFormatter?: (point: DataPoint) => React.ReactNode
}

const CustomTooltip: React.FC<{ active?: boolean; payload?: any[]; tooltipFormatter?: (point: DataPoint) => React.ReactNode }> = ({ active, payload, tooltipFormatter }) => {
  if (!active || !payload?.[0]?.payload) return null
  const d = payload[0].payload as DataPoint
  if (tooltipFormatter) return <>{tooltipFormatter(d)}</>
  return (
    <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1, fontSize: 12, minWidth: 160 }}>
      <Typography variant="body2" fontWeight={700}>{d.material}</Typography>
      <Typography variant="caption" color="text.secondary">Tc: {d.y}K · P: {d.x}GPa</Typography>
      {d.year && <Typography variant="caption" color="text.secondary"> · {d.year}</Typography>}
      {d.doi && <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>{d.doi}</Typography>}
    </Box>
  )
}

const ChartScatter: React.FC<Props> = ({
  title, data, xLabel, yLabel, xDomain, yDomain,
  visibleTypes, showBackground, onToggleType,
  tooltipFormatter,
}) => {
  // 分组数据：背景点 vs 组合内点（按类型分系列）
  const backgroundPoints = data.filter(d => !d.isInGroup && visibleTypes.has(d.scType))
  const groupPoints = data.filter(d => d.isInGroup && visibleTypes.has(d.scType))

  // 按 scType 分系列
  const scTypes = Object.keys(SC_TYPE_CONFIG)
  const groupSeries = scTypes.map(st => ({
    key: st,
    data: groupPoints.filter(p => p.scType === st),
  })).filter(s => s.data.length > 0)

  const bgSeries = scTypes.map(st => ({
    key: st,
    data: backgroundPoints.filter(p => p.scType === st),
  })).filter(s => s.data.length > 0)

  return (
    <Box>
      {/* 图例 */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
        {scTypes.map(st => {
          const cfg = SC_TYPE_CONFIG[st]
          const isVisible = visibleTypes.has(st)
          return (
            <Chip
              key={st}
              size="small"
              label={cfg.label}
              variant={isVisible ? 'filled' : 'outlined'}
              icon={<Box component="span" sx={{ fontSize: 14, lineHeight: 1 }}>{
                st === 'hydride' ? '▲' : st === 'cuprate' ? '■' :
                st === 'iron_based' ? '◆' : st === 'nickel_based' ? '●' :
                st === 'carbon' ? '▼' : st === 'organic' ? '⬢' : '✚'
              }</Box>}
              onClick={() => onToggleType(st)}
              sx={{
                cursor: 'pointer',
                bgcolor: isVisible ? cfg.colorExp : undefined,
                color: isVisible ? '#fff' : undefined,
                '& .MuiChip-icon': { color: isVisible ? '#fff' : cfg.colorExp },
              }}
            />
          )
        })}
        <Chip size="small" label={`实验=深色 理论=浅色`} variant="outlined" sx={{ ml: 'auto' }} />
      </Box>

      <ResponsiveContainer width="100%" aspect={2}>
        <ScatterChart margin={{ top: 10, right: 10, bottom: 30, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" dataKey="x" domain={xDomain || [0, 'auto']}
            label={{ value: xLabel, position: 'bottom', offset: -5 }} />
          <YAxis type="number" dataKey="y" domain={yDomain || [0, 'auto']}
            label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
          <ZAxis range={[60, 60]} />
          <Tooltip content={<CustomTooltip tooltipFormatter={tooltipFormatter} />} />

          {/* 背景点（灰色半透明） */}
          {showBackground && bgSeries.map(s => (
            <Scatter key={`bg-${s.key}`} name={`bg-${s.key}`} data={s.data}
              fill={BACKGROUND_COLOR} opacity={BACKGROUND_OPACITY}
              shape={s.key === 'hydride' ? 'triangle' : s.key === 'cuprate' ? 'square' :
                s.key === 'iron_based' ? 'diamond' : s.key === 'nickel_based' ? 'circle' :
                s.key === 'carbon' ? 'wye' : s.key === 'organic' ? 'cross' : 'diamond'} />
          ))}

          {/* 组合内点（彩色实心） */}
          {groupSeries.map(s => {
            const cfg = SC_TYPE_CONFIG[s.key]
            return (
              <Scatter key={`gp-${s.key}`} name={cfg.label} data={s.data}
                fill={cfg.colorExp} opacity={0.9}
                shape={s.key === 'hydride' ? 'triangle' : s.key === 'cuprate' ? 'square' :
                  s.key === 'iron_based' ? 'diamond' : s.key === 'nickel_based' ? 'circle' :
                  s.key === 'carbon' ? 'wye' : s.key === 'organic' ? 'cross' : 'diamond'} />
            )
          })}
        </ScatterChart>
      </ResponsiveContainer>
    </Box>
  )
}

export default ChartScatter
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ChartScatter.tsx
git commit -m "feat: add ChartScatter component with legend"
```

---

### Task 5: 组合编辑弹窗 ChartGroupEditor

**Files:**
- Create: `frontend/src/components/ChartGroupEditor.tsx`

- [ ] **Step 1: 创建编辑弹窗组件**

```tsx
import React, { useState, useEffect } from 'react'
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Typography, Box, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow,
  IconButton, Chip, Checkbox, FormControlLabel,
  Paper, Snackbar, Alert, CircularProgress, LinearProgress,
  FormControl, InputLabel, Select, MenuItem,
} from '@mui/material'
import { Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'

interface GroupItem {
  id?: number
  sort_order: number
  source: 'kp' | 'custom'
  key_property_id: number | null
  material: string
  tc: number | null
  pressure: number | null
  type: string | null
  year: number | null
  custom_label?: string
  custom_tc?: number
  custom_pressure?: number
  custom_type?: string
  custom_year?: number
}

interface GroupData {
  id?: number
  name: string
  description: string
  is_public: boolean
  items: GroupItem[]
}

interface Props {
  open: boolean
  groupId: number | null  // null = 新建
  onClose: () => void
  onSaved: () => void
}

const ChartGroupEditor: React.FC<Props> = ({ open, groupId, onClose, onSaved }) => {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'superadmin'

  const [group, setGroup] = useState<GroupData>({ name: '', description: '', is_public: false, items: [] })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [snackbar, setSnackbar] = useState('')

  // 搜索 kp
  const [kpSearch, setKpSearch] = useState('')
  const [kpResults, setKpResults] = useState<any[]>([])
  const [kpLoading, setKpLoading] = useState(false)

  // 自定义点表单
  const [customOpen, setCustomOpen] = useState(false)
  const [customForm, setCustomForm] = useState({ label: '', tc: '', pressure: '', type: 'hydride' })

  // 加载组合数据
  useEffect(() => {
    if (!open) return
    if (groupId) {
      setLoading(true)
      fetch(`/api/chart-groups/${groupId}`)
        .then(r => r.json())
        .then(d => setGroup({
          id: d.id,
          name: d.name,
          description: d.description || '',
          is_public: d.is_public,
          items: d.items || [],
        }))
        .catch(() => setSnackbar('加载失败'))
        .finally(() => setLoading(false))
    } else {
      setGroup({ name: '', description: '', is_public: false, items: [] })
    }
  }, [open, groupId])

  // 搜索 key_properties
  const handleSearch = async () => {
    if (!kpSearch.trim()) return
    setKpLoading(true)
    try {
      const res = await fetch(`/api/admin/papers/all?keyword=${encodeURIComponent(kpSearch)}&limit=10`)
      // 这里实际应调专门的搜索接口，暂时复用 admin papers 搜索
      // 若不可用需改为直接调后端专门的 kp 搜索
      setKpResults([])
    } catch { setKpResults([]) }
    finally { setKpLoading(false) }
  }

  // 删除 item
  const removeItem = (idx: number) => {
    setGroup(prev => ({ ...prev, items: prev.items.filter((_, i) => i !== idx) }))
  }

  // 添加自定义点
  const addCustom = () => {
    setGroup(prev => ({
      ...prev,
      items: [...prev.items, {
        sort_order: prev.items.length,
        source: 'custom' as const,
        key_property_id: null,
        material: customForm.label || '自定义点',
        tc: Number(customForm.tc) || null,
        pressure: Number(customForm.pressure) || null,
        type: customForm.type,
        year: null,
        custom_label: customForm.label,
        custom_tc: Number(customForm.tc) || 0,
        custom_pressure: Number(customForm.pressure) || 0,
        custom_type: customForm.type,
      }],
    }))
    setCustomForm({ label: '', tc: '', pressure: '', type: 'hydride' })
    setCustomOpen(false)
  }

  // 保存
  const handleSave = async () => {
    setSaving(true)
    try {
      const url = group.id ? `/api/chart-groups/${group.id}` : '/api/chart-groups'
      const method = group.id ? 'PUT' : 'POST'
      const body = {
        name: group.name,
        description: group.description,
        items: group.items.map(it => ({
          key_property_id: it.key_property_id,
          custom_label: it.custom_label,
          custom_tc: it.custom_tc,
          custom_pressure: it.custom_pressure,
          custom_type: it.custom_type,
          custom_year: it.custom_year,
        })),
      }
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!res.ok) throw new Error((await res.json()).detail || '保存失败')
      setSnackbar(group.id ? '已更新' : '已创建')
      onSaved()
      onClose()
    } catch (e: any) {
      setSnackbar(e.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // 添加搜索的 kp 数据点
  const addKpItems = (kps: any[]) => {
    setGroup(prev => ({
      ...prev,
      items: [...prev.items, ...kps.map((kp, i) => ({
        sort_order: prev.items.length + i,
        source: 'kp' as const,
        key_property_id: kp.id,
        material: kp.material || kp.name || '?',
        tc: kp.value_max,
        pressure: kp.pressure_gpa,
        type: kp.superconductor_type,
        year: null,
      }))],
    }))
    setKpSelected(new Set())
    setKpSearch('')
    setKpResults([])
  }

  const handleSearchAndAdd = async () => {
    if (!kpSearch.trim()) return
    setKpLoading(true)
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`/api/chart-groups/search?q=${encodeURIComponent(kpSearch)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error('搜索失败')
      const data = await res.json()
      setKpResults(data || [])
    } catch (e: any) { setSnackbar(e.message) }
    finally { setKpLoading(false) }
  }

  if (loading) return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogContent><LinearProgress /></DialogContent>
    </Dialog>
  )

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{group.id ? '编辑组合' : '新建组合'}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
          <TextField label="名称" size="small" value={group.name}
            onChange={e => setGroup({ ...group, name: e.target.value })} />
          <TextField label="描述" size="small" value={group.description}
            onChange={e => setGroup({ ...group, description: e.target.value })} />
        </Box>
        {isAdmin && (
          <FormControlLabel
            control={<Checkbox checked={group.is_public} size="small"
              onChange={e => setGroup({ ...group, is_public: e.target.checked })} />}
            label="公开（所有人可见）" />
        )}

        {/* 数据点列表 */}
        <Typography variant="subtitle2" fontWeight={700}>
          数据点 ({group.items.length})
        </Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 300 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 30 }}>#</TableCell>
                <TableCell>材料</TableCell>
                <TableCell sx={{ width: 80 }}>Tc(K)</TableCell>
                <TableCell sx={{ width: 80 }}>P(GPa)</TableCell>
                <TableCell sx={{ width: 100 }}>类型</TableCell>
                <TableCell sx={{ width: 60 }}>来源</TableCell>
                <TableCell sx={{ width: 40 }}></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {group.items.map((it, i) => (
                <TableRow key={i}>
                  <TableCell>{i + 1}</TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 160 }}>{it.material}</Typography>
                  </TableCell>
                  <TableCell>{it.tc ?? '-'}</TableCell>
                  <TableCell>{it.pressure ?? '-'}</TableCell>
                  <TableCell>{it.type || '-'}</TableCell>
                  <TableCell>
                    <Chip size="small" label={it.source === 'kp' ? 'DB' : '自定义'}
                      variant="outlined" sx={{ fontSize: 10 }} />
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => removeItem(i)}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {group.items.length === 0 && (
                <TableRow><TableCell colSpan={7} align="center" sx={{ color: 'text.secondary', py: 2 }}>暂无数据点</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* 添加操作 */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Box sx={{ display: 'flex', gap: 0.5, flex: 1 }}>
            <TextField size="small" placeholder="搜索材料名…" sx={{ flex: 1 }}
              value={kpSearch}
              onChange={e => setKpSearch(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSearchAndAdd() }} />
            <Button variant="outlined" size="small" onClick={handleSearchAndAdd}
              disabled={kpLoading}
              startIcon={kpLoading ? <CircularProgress size={14} /> : undefined}>
              搜索
            </Button>
            {kpResults.length > 0 && (
              <Box sx={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 1, mt: 0.5, maxHeight: 200, overflow: 'auto' }}>
                {kpResults.map((kp: any) => (
                  <Box key={kp.id} sx={{ px: 1, py: 0.5, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                    onClick={() => addKpItems([kp])}>
                    <Typography variant="body2">{kp.material} — Tc:{kp.value_max} P:{kp.pressure_gpa}GPa</Typography>
                  </Box>
                ))}
              </Box>
            )}
          </Box>
          <Button variant="outlined" size="small" startIcon={<AddIcon />}
            onClick={() => setCustomOpen(true)}>
            自定义点
          </Button>
        </Box>

        {/* 自定义点表单 */}
        {customOpen && (
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr auto', gap: 0.5, p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
            <TextField size="small" label="标签" value={customForm.label}
              onChange={e => setCustomForm({ ...customForm, label: e.target.value })} />
            <TextField size="small" label="Tc(K)" type="number"
              value={customForm.tc}
              onChange={e => setCustomForm({ ...customForm, tc: e.target.value })} />
            <TextField size="small" label="压强(GPa)" type="number"
              value={customForm.pressure}
              onChange={e => setCustomForm({ ...customForm, pressure: e.target.value })} />
            <FormControl size="small">
              <InputLabel>类型</InputLabel>
              <Select value={customForm.type} label="类型"
                onChange={e => setCustomForm({ ...customForm, type: e.target.value })}>
                <MenuItem value="hydride">hydride</MenuItem>
                <MenuItem value="cuprate">cuprate</MenuItem>
                <MenuItem value="iron_based">iron_based</MenuItem>
                <MenuItem value="nickel_based">nickel_based</MenuItem>
                <MenuItem value="carbon">carbon</MenuItem>
                <MenuItem value="organic">organic</MenuItem>
                <MenuItem value="others">others</MenuItem>
              </Select>
            </FormControl>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <Button size="small" variant="contained" onClick={addCustom}>添加</Button>
              <Button size="small" onClick={() => setCustomOpen(false)}>取消</Button>
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        <Button variant="contained" onClick={handleSave} disabled={saving || !group.name}>
          {saving ? <CircularProgress size={18} /> : group.id ? '保存' : '创建'}
        </Button>
      </DialogActions>

      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="info" variant="filled" onClose={() => setSnackbar('')}>{snackbar}</Alert>
      </Snackbar>
    </Dialog>
  )
}

export default ChartGroupEditor
```

- [ ] **Step 2: 添加后端搜索接口**

在 `backend/api/chart_groups.py` 中追加：

```python
@router.get("/search", summary="搜索可加入组合的 key_properties")
def search_kps(q: str = Query(min_length=1), limit: int = 20,
               db: Session = Depends(get_db)):
    rows = db.query(models.KeyProperty).filter(
        models.KeyProperty.material.like(f"%{q}%")
    ).limit(limit).all()
    return [
        {
            "id": kp.id,
            "material": kp.material,
            "name": kp.name,
            "value_max": kp.value_max,
            "value_min": kp.value_min,
            "unit": kp.unit,
            "pressure_gpa": kp.pressure_gpa,
            "superconductor_type": kp.superconductor_type,
            "article_type": kp.article_type,
        }
        for kp in rows
    ]
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChartGroupEditor.tsx backend/api/chart_groups.py
git commit -m "feat: add ChartGroupEditor dialog with kp search"
```

---

### Task 6: 重写社区页面 share.tsx

**Files:**
- Modify: `frontend/src/pages/share.tsx`

- [ ] **Step 1: 重写 share.tsx**

页面结构：全局筛选(可折叠) → Tc-Pressure 散点图(独立组合) → Tc-Year 散点图(独立组合)

```tsx
import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, Paper, Card, CardContent, Button, Chip,
  Collapse, FormControlLabel, Switch, Select, MenuItem,
  FormControl, InputLabel, IconButton, Tooltip,
} from '@mui/material'
import {
  ExpandMore as ExpandIcon, Edit as EditIcon,
  ContentCopy as CopyIcon, FileDownload as ExportIcon,
} from '@mui/icons-material'
import { api } from '../lib/api'
import { SC_TYPE_CONFIG, getPointColor, BACKGROUND_COLOR, BACKGROUND_OPACITY } from '../lib/scatterConfig'
import ChartScatter from '../components/ChartScatter'
import ChartGroupEditor from '../components/ChartGroupEditor'

const ALL_SC_TYPES = Object.keys(SC_TYPE_CONFIG)

interface ChartState {
  groupId: number | null
  groupName: string
}

const SharePage: React.FC = () => {
  // ── 全局筛选 ──
  const [showFilter, setShowFilter] = useState(true)
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(new Set(ALL_SC_TYPES))
  const [showExperiment, setShowExperiment] = useState(true)
  const [showTheory, setShowTheory] = useState(true)
  const [showBackground, setShowBackground] = useState(true)

  // ── 数据 ──
  const [allData, setAllData] = useState<any[]>([])
  const [groups, setGroups] = useState<any[]>([])

  // ── 两张图各自独立组合 ──
  const [chart1, setChart1] = useState<ChartState>({ groupId: null, groupName: '高压氢化物 Tc>200K' })
  const [chart2, setChart2] = useState<ChartState>({ groupId: null, groupName: '铁基超导' })

  // ── 编辑器 ──
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingGroupId, setEditingGroupId] = useState<number | null>(null)

  // 加载 groups 列表
  const loadGroups = useCallback(async () => {
    try {
      const res = await api.get<any[]>('/api/chart-groups')
      setGroups(Array.isArray(res) ? res : [])
    } catch { /* ignore */ }
  }, [])

  // 加载图表数据
  const loadData = useCallback(async () => {
    try {
      const [pressureData, yearData] = await Promise.all([
        api.get<any[]>('/api/papers/stats/tc-pressure'),
        api.get<any[]>('/api/papers/stats/tc-year'),
      ])
      setAllData([...pressureData, ...yearData])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { loadGroups(); loadData() }, [loadGroups, loadData])

  // 获取组合 items 的 kp_id 集合
  const getGroupKpIds = (gid: number | null): Set<number> => {
    if (!gid) return new Set()
    const g = groups.find(gr => gr.id === gid)
    if (!g || !g.items) return new Set()
    return new Set(g.items.filter((it: any) => it.source === 'kp' && it.key_property_id).map((it: any) => it.key_property_id))
  }

  const chart1KpIds = getGroupKpIds(chart1.groupId)
  const chart2KpIds = getGroupKpIds(chart2.groupId)

  // 打开编辑器
  const handleEdit = (groupId: number | null) => {
    setEditingGroupId(groupId)
    setEditorOpen(true)
  }

  const handleEditorSaved = () => {
    loadGroups()
  }

  // toggle 类型
  const toggleType = (st: string, setVisible: typeof setVisibleTypes) => {
    setVisible(prev => {
      const next = new Set(prev)
      if (next.has(st)) next.delete(st); else next.add(st)
      return next
    })
  }

  // ── 构建背景点 ──
  const buildBgPoints = (xKey: 'pressure' | 'year', chartKpIds: Set<number>) => {
    if (!showBackground) return []
    const unique = new Map<string, any>()
    for (const d of allData) {
      // 按 xKey 和 label 区分数据点
      const xVal = xKey === 'pressure' ? d.pressure_gpa : d.year
      if (xVal == null || d.value_max == null) continue
      const st = d.superconductor_type || 'others'
      if (!visibleTypes.has(st)) continue
      const isExp = d.article_type === 'e'
      if (isExp && !showExperiment) continue
      if (!isExp && !showTheory) continue
      const key = `${d.material}-${xVal}-${d.value_max}`
      if (!unique.has(key) && !chartKpIds.has(d.id)) {
        unique.set(key, {
          x: xVal,
          y: d.value_max,
          material: d.material,
          scType: st,
          articleType: d.article_type,
          year: d.year,
          doi: d.doi,
          isInGroup: false,
          isCustom: false,
          label: d.material,
        })
      }
    }
    return Array.from(unique.values())
  }

  // ── 构建组合点 ──
  const buildGroupPoints = (xKey: 'pressure' | 'year', chartKpIds: Set<number>) => {
    const gid = xKey === 'pressure' ? chart1.groupId : chart2.groupId
    const g = groups.find(gr => gr.id === gid)
    if (!g || !g.items) return []
    return g.items
      .filter((it: any) => {
        const st = it.type || 'others'
        if (!visibleTypes.has(st)) return false
        const isExp = it.article_type === 'e'
        if (isExp && !showExperiment) return false
        if (!isExp && !showTheory) return false
        return true
      })
      .map((it: any) => ({
        x: xKey === 'pressure' ? (it.pressure ?? 0) : (it.year ?? 0),
        y: it.tc ?? 0,
        material: it.material,
        scType: it.type || 'others',
        articleType: it.article_type,
        year: it.year,
        doi: it.doi,
        isInGroup: true,
        isCustom: it.source === 'custom',
        label: it.material,
      }))
  }

  // ── 组合选择器 ──
  const groupSelector = (
    state: ChartState,
    setState: (s: ChartState) => void,
  ) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
      <FormControl size="small" sx={{ minWidth: 200 }}>
        <InputLabel>组合</InputLabel>
        <Select
          value={state.groupId ?? ''}
          label="组合"
          onChange={e => {
            const gid = e.target.value ? Number(e.target.value) : null
            const g = groups.find(gr => gr.id === gid)
            setState({ groupId: gid, groupName: g?.name || '无' })
          }}
        >
          <MenuItem value="">(无组合)</MenuItem>
          {groups.map(g => (
            <MenuItem key={g.id} value={g.id}>{g.name} ({g.item_count || 0})</MenuItem>
          ))}
        </Select>
      </FormControl>
      <Tooltip title="编辑"><IconButton size="small" onClick={() => handleEdit(state.groupId)}><EditIcon fontSize="small" /></IconButton></Tooltip>
      {state.groupId && (
        <>
          <Tooltip title="复制"><IconButton size="small"
            onClick={async () => {
              try { await api.post(`/api/chart-groups/${state.groupId}/copy`); loadGroups() }
              catch (e: any) { /* ignore */ }
            }}><CopyIcon fontSize="small" /></IconButton></Tooltip>
          <Tooltip title="导出 JSON"><IconButton size="small"
            onClick={async () => {
              try {
                const data = await api.get<any>(`/api/chart-groups/${state.groupId}/export`)
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a'); a.href = url; a.download = `${state.groupName}.json`; a.click()
                URL.revokeObjectURL(url)
              } catch { /* ignore */ }
            }}><ExportIcon fontSize="small" /></IconButton></Tooltip>
        </>
      )}
      <Button size="small" variant="outlined" onClick={() => handleEdit(null)}>+ 新建</Button>
    </Box>
  )

  return (
    <Box>
      <Typography variant="overline">Community</Typography>
      <Typography variant="h1">社区</Typography>

      {/* ── 全局筛选 ── */}
      <Card sx={{ mt: 3, mb: 3 }} variant="outlined">
        <CardContent sx={{ pb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }}
            onClick={() => setShowFilter(!showFilter)}>
            <ExpandIcon sx={{ transform: showFilter ? 'rotate(180deg)' : 'none', transition: '0.2s' }} />
            <Typography variant="subtitle2" fontWeight={700}>全局筛选</Typography>
            <Box sx={{ flex: 1 }} />
            <FormControlLabel control={<Switch size="small" checked={showBackground}
              onChange={e => setShowBackground(e.target.checked)} />} label="背景点" />
          </Box>
          <Collapse in={showFilter}>
            <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {ALL_SC_TYPES.map(st => {
                const cfg = SC_TYPE_CONFIG[st]
                return (
                  <Chip key={st} size="small" label={cfg.label}
                    variant={visibleTypes.has(st) ? 'filled' : 'outlined'}
                    sx={{ cursor: 'pointer', bgcolor: visibleTypes.has(st) ? cfg.colorExp : undefined,
                      color: visibleTypes.has(st) ? '#fff' : undefined }}
                    onClick={() => toggleType(st, setVisibleTypes)} />
                )
              })}
              <Chip size="small" label="实验"
                variant={showExperiment ? 'filled' : 'outlined'} color="primary"
                onClick={() => setShowExperiment(!showExperiment)}
                sx={{ cursor: 'pointer' }} />
              <Chip size="small" label="理论"
                variant={showTheory ? 'filled' : 'outlined'}
                onClick={() => setShowTheory(!showTheory)}
                sx={{ cursor: 'pointer', bgcolor: showTheory ? '#82ca9d' : undefined,
                  color: showTheory ? '#fff' : undefined }} />
            </Box>
          </Collapse>
        </CardContent>
      </Card>

      {/* ── Tc-Pressure ── */}
      <Paper sx={{ p: 2.5, borderRadius: 4, mb: 3 }}>
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="h2" gutterBottom>Tc-Pressure 分布</Typography>
          {groupSelector(chart1, setChart1)}
        </Box>
        <ChartScatter
          title="Tc vs Pressure"
          data={[...buildBgPoints('pressure', chart1KpIds), ...buildGroupPoints('pressure', chart1KpIds)]}
          xLabel="Pressure (GPa)"
          yLabel="Tc (K)"
          visibleTypes={visibleTypes}
          showBackground={showBackground}
          onToggleType={(st) => toggleType(st, setVisibleTypes)}
        />
      </Paper>

      {/* ── Tc-Year ── */}
      <Paper sx={{ p: 2.5, borderRadius: 4, mb: 3 }}>
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="h2" gutterBottom>Tc-Year 演变</Typography>
          {groupSelector(chart2, setChart2)}
        </Box>
        <ChartScatter
          title="Tc vs Year"
          data={[...buildBgPoints('year', chart2KpIds), ...buildGroupPoints('year', chart2KpIds)]}
          xLabel="Year"
          yLabel="Tc (K)"
          xDomain={[1900, 'auto']}
          visibleTypes={visibleTypes}
          showBackground={showBackground}
          onToggleType={(st) => toggleType(st, setVisibleTypes)}
        />
      </Paper>

      {/* ── 编辑器 ── */}
      <ChartGroupEditor
        open={editorOpen}
        groupId={editingGroupId}
        onClose={() => setEditorOpen(false)}
        onSaved={handleEditorSaved}
      />
    </Box>
  )
}

export default SharePage
```

- [ ] **Step 2: 构建前端**

```bash
cd /home/work/workshop/git/SC-Wiki/frontend && npx vite build
```

期望: `✓ built in XXs`

- [ ] **Step 3: 打开浏览器验证**

访问 `http://127.0.0.1:5173/share`，验证：
1. 全局筛选折叠/展开
2. 类型 Chip 点击显隐
3. 组合下拉切换
4. 编辑弹窗

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/share.tsx
git commit -m "feat: upgrade community scatter charts with group selection"
```

---

### Task 7: 验收测试

- [ ] **Step 1: 后端 API 全量测试**

```bash
# 1. 列出组合（至少 5 个预设）
# 2. 创建新组合
# 3. 获取组合详情
# 4. 更新组合（改名称 + 替换 items）
# 5. 复制组合
# 6. 导出组合
# 7. 导入组合
# 8. 切换公开状态（管理员）
# 9. 删除组合
```

- [ ] **Step 2: 前端功能测试**

1. 页面加载 → 散点图渲染，背景点可见
2. 点击图例 Chip → 该类型显隐切换
3. 选择组合 → 组合内数据点高亮
4. 编辑组合 → Dialog 打开，修改数据点
5. 新建组合 → 空白 Dialog，添加数据点
6. 全局筛选修改 → 两张图同步更新

- [ ] **Step 3: 权限测试**

1. 普通用户 → 不能设公开，不能删他人
2. 管理员 → 可设公开，可编辑公开组合
3. 超管 → 全部权限

- [ ] **Step 4: Commit final**

```bash
git add -A && git commit -m "chore: final verification and cleanup"
```
