"""
数据导入工具
从JSON文件导入数据到数据库
"""
import json
import base64
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine
from backend import models


def import_all_data(input_file: str = "data_export.json", clear_existing: bool = False):
    """
    从JSON文件导入数据

    Args:
        input_file: 输入文件路径
        clear_existing: 是否清空现有数据（谨慎使用！）
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return

    db = SessionLocal()

    try:
        # 读取JSON文件
        print(f"读取数据文件: {input_path}...")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 可选：清空现有数据
        if clear_existing:
            print("⚠️  清空现有数据...")
            db.query(models.CompoundElement).delete()
            db.query(models.PaperImage).delete()
            db.query(models.Paper).delete()
            db.query(models.Compound).delete()
            # 不删除元素表，因为它是预定义的
            db.commit()

        # 1. 导入元素组合
        print("导入元素组合...")
        compound_id_mapping = {}  # 旧ID -> 新ID映射
        for comp_data in data["compounds"]:
            # 检查是否已存在
            existing = db.query(models.Compound).filter(
                models.Compound.element_symbols == comp_data["element_symbols"]
            ).first()

            if existing:
                compound_id_mapping[comp_data["id"]] = existing.id
            else:
                symbols_str = comp_data["element_symbols"]
                if "element_list" in comp_data and comp_data["element_list"]:
                    symbol_list = comp_data["element_list"]
                else:
                    symbol_list = [s for s in symbols_str.split("-") if s]
                compound = models.Compound(
                    element_symbols=symbols_str,
                    element_list=json.dumps(symbol_list),
                    created_at=datetime.fromisoformat(comp_data["created_at"])
                )
                db.add(compound)
                db.flush()
                compound_id_mapping[comp_data["id"]] = compound.id

        db.commit()
        print(f"   ✅ 导入了 {len(data['compounds'])} 个元素组合")

        # 2. 导入文献
        print("导入文献...")
        paper_id_mapping = {}  # 旧ID -> 新ID映射
        for paper_data in data["papers"]:
            # 检查是否已存在（根据DOI和compound_id）
            old_compound_id = paper_data["compound_id"]
            new_compound_id = compound_id_mapping.get(old_compound_id)

            if not new_compound_id:
                print(f"   ⚠️  跳过文献 {paper_data['doi']}（元素组合不存在）")
                continue

            existing = db.query(models.Paper).filter(
                models.Paper.compound_id == new_compound_id,
                models.Paper.doi == paper_data["doi"]
            ).first()

            if existing:
                print(f"   ⚠️  文献已存在，跳过: {paper_data['doi']}")
                paper_id_mapping[paper_data["id"]] = existing.id
                continue

            paper = models.Paper(
                compound_id=new_compound_id,
                doi=paper_data["doi"],
                title=paper_data["title"],
                article_type=paper_data["article_type"],
                superconductor_type=paper_data["superconductor_type"],
                authors=paper_data["authors"],
                journal=paper_data["journal"],
                volume=paper_data["volume"],
                pages=paper_data["pages"],
                year=paper_data["year"],
                abstract=paper_data["abstract"],
                citation_aps=paper_data["citation_aps"],
                citation_bibtex=paper_data["citation_bibtex"],
                chemical_formula=paper_data["chemical_formula"],
                crystal_structure=paper_data["crystal_structure"],
                contributor_name=paper_data["contributor_name"],
                contributor_affiliation=paper_data["contributor_affiliation"],
                notes=paper_data["notes"],
                created_at=datetime.fromisoformat(paper_data["created_at"])
            )
            db.add(paper)
            db.flush()
            paper_id_mapping[paper_data["id"]] = paper.id

        db.commit()
        print(f"   ✅ 导入了 {len(paper_id_mapping)} 篇文献")

        # 3. 导入文献截图
        print("导入文献截图...")
        imported_images = 0
        for img_data in data["paper_images"]:
            old_paper_id = img_data["paper_id"]
            new_paper_id = paper_id_mapping.get(old_paper_id)

            if not new_paper_id:
                continue

            # 解码Base64图片数据
            image_data = base64.b64decode(img_data["image_data"])
            thumbnail_data = base64.b64decode(img_data["thumbnail_data"])

            image = models.PaperImage(
                paper_id=new_paper_id,
                image_data=image_data,
                thumbnail_data=thumbnail_data,
                image_order=img_data["image_order"],
                file_size=img_data["file_size"],
                created_at=datetime.fromisoformat(img_data["created_at"])
            )
            db.add(image)
            imported_images += 1

        db.commit()
        print(f"   ✅ 导入了 {imported_images} 张截图")

        # 4. 导入元素组合关联
        print("导入元素组合关联...")
        for ce_data in data["compound_elements"]:
            old_compound_id = ce_data["compound_id"]
            new_compound_id = compound_id_mapping.get(old_compound_id)

            if not new_compound_id:
                continue

            # 检查是否已存在
            existing = db.query(models.CompoundElement).filter(
                models.CompoundElement.compound_id == new_compound_id,
                models.CompoundElement.element_id == ce_data["element_id"]
            ).first()

            if existing:
                continue

            ce = models.CompoundElement(
                compound_id=new_compound_id,
                element_id=ce_data["element_id"]
            )
            db.add(ce)

        db.commit()
        print(f"   ✅ 导入了元素组合关联")

        print("\n✅ 导入完成！")
        print(f"   元素组合: {len(compound_id_mapping)} 个")
        print(f"   文献: {len(paper_id_mapping)} 篇")
        print(f"   截图: {imported_images} 张")

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    input_file = "data/data_export.json"
    clear_existing = "--clear" in sys.argv

    if clear_existing:
        confirm = input("⚠️  确定要清空现有数据吗？(yes/no): ")
        if confirm.lower() != "yes":
            print("取消操作")
            sys.exit(0)

    import_all_data(input_file, clear_existing)
