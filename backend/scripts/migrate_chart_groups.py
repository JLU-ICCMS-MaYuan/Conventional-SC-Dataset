"""创建 chart_groups / chart_group_items 表 + 预设数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.database import engine, SessionLocal
from backend.models import Base, ChartGroup, ChartGroupItem

Base.metadata.create_all(bind=engine, tables=[
    ChartGroup.__table__,
    ChartGroupItem.__table__,
])

db = SessionLocal()
try:
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
finally:
    db.close()

print("完成")
