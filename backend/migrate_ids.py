"""
数据库迁移脚本：为现有化合物填充 element_id_list
"""
import json
from backend.database import SessionLocal
from backend import models, crud

def migrate_compound_ids():
    db = SessionLocal()
    try:
        compounds = db.query(models.Compound).all()
        print(f"开始迁移 {len(compounds)} 条记录...")
        
        updated_count = 0
        for compound in compounds:
            # 解析现有的元素符号
            if compound.element_list and compound.element_list != "[]":
                symbols = json.loads(compound.element_list)
            else:
                symbols = compound.element_symbols.split("-")
            
            # 获取元素对象并排序 ID
            elements = crud.get_elements_by_symbols(db, symbols)
            element_ids = sorted([e.id for e in elements])
            
            # 更新字段
            compound.element_id_list = json.dumps(element_ids)
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"已处理 {updated_count} 条...")
        
        db.commit()
        print(f"成功完成迁移！共更新 {updated_count} 条记录。")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_compound_ids()
