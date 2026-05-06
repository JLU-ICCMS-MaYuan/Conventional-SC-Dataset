"""
数据导入工具
从JSON文件导入数据到数据库
"""
import json
import base64
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import MetadataSessionLocal, ImageSessionLocal
from backend import models, crud


def get_all_element_symbols(db: Session):
    """获取所有有效的元素符号"""
    return {e.symbol for e in db.query(models.Element).all()}


def standardize_elements(symbols_list, valid_elements):
    """过滤并排序元素符号，确保标准化"""
    if not symbols_list:
        return []
    # 过滤掉非有效元素的字符串（如 '170190', 'GPa' 等）
    valid_list = [s for s in symbols_list if s in valid_elements]
    return sorted(list(set(valid_list)))


def import_all_data(input_file: str = "data/data_export.json", clear_existing: bool = False):
    """
    从JSON文件导入数据，并强制执行元素符号标准化
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return

    db = MetadataSessionLocal()
    image_db = ImageSessionLocal()
    valid_elements = get_all_element_symbols(db)

    try:
        print(f"读取数据文件: {input_path}...")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if clear_existing:
            print("⚠️  清空现有数据...")
            image_db.query(models.PaperImage).delete()
            image_db.commit()
            db.query(models.PaperData).delete()
            db.query(models.Paper).delete()
            db.query(models.Compound).delete()
            db.commit()

        compound_id_mapping = {}
        paper_id_mapping = {}

        print("处理元素组合...")
        compounds_to_process = data.get("compounds", [])

        if not compounds_to_process and "papers" in data:
            print("   JSON中缺少compounds信息，正在从papers中推断...")
            seen_combos = set()
            for p in data["papers"]:
                raw_symbols = p.get("element_list") or p.get("element_symbols", "").split("-")
                std_list = standardize_elements(raw_symbols, valid_elements)
                if std_list:
                    combo_key = "-".join(std_list)
                    if combo_key not in seen_combos:
                        compounds_to_process.append({
                            "id": p.get("compound_id", -1),
                            "element_symbols": combo_key,
                            "element_list": std_list,
                            "created_at": p.get("created_at", datetime.now().isoformat())
                        })
                        seen_combos.add(combo_key)

        for comp_data in compounds_to_process:
            std_list = comp_data.get("element_list") or []
            chemical_formula = comp_data.get("chemical_formula")
            if chemical_formula:
                compound = crud.get_or_create_compound(db, std_list, chemical_formula)
            else:
                compound = crud.get_or_create_compound(db, std_list)
            if not compound:
                continue
            if "id" in comp_data:
                compound_id_mapping[comp_data["id"]] = compound.id
            if chemical_formula:
                compound_id_mapping[chemical_formula] = compound.id

        db.commit()
        print("   ✅ 元素组合准备就绪")

        print("导入文献...")
        for paper_data in data.get("papers", []):
            existing = db.query(models.Paper).filter(models.Paper.doi == paper_data["doi"]).first()
            if existing:
                paper_id_mapping[paper_data["id"]] = existing.id
                continue

            paper = models.Paper(
                doi=paper_data["doi"],
                title=paper_data.get("title"),
                authors=paper_data.get("authors"),
                journal=paper_data.get("journal"),
                volume=paper_data.get("volume"),
                pages=paper_data.get("pages"),
                year=paper_data.get("year"),
                abstract=paper_data.get("abstract"),
                contributor_name=paper_data.get("contributor_name", "Data Import"),
                contributor_affiliation=paper_data.get("contributor_affiliation", "System"),
                notes=paper_data.get("notes"),
                review_status=paper_data.get("review_status", "unreviewed"),
                review_comment=paper_data.get("review_comment"),
                show_in_chart=paper_data.get("show_in_chart", False),
                created_at=datetime.fromisoformat(paper_data["created_at"]) if paper_data.get("created_at") else datetime.now(),
            )
            db.add(paper)
            db.flush()
            paper_id_mapping[paper_data["id"]] = paper.id

        db.commit()
        print(f"   ✅ 文献导入完成 ({len(paper_id_mapping)} 篇)")

        print("导入物理参数...")
        imported_params = 0
        for param_data in data.get("paper_data", []):
            old_paper_id = param_data.get("paper_id")
            new_paper_id = paper_id_mapping.get(old_paper_id)
            if not new_paper_id:
                continue

            compound_id = None
            old_compound_id = param_data.get("compound_id")
            if old_compound_id in compound_id_mapping:
                compound_id = compound_id_mapping[old_compound_id]
            elif param_data.get("chemical_formula") in compound_id_mapping:
                compound_id = compound_id_mapping[param_data.get("chemical_formula")]
            elif param_data.get("chemical_formula"):
                compound = crud.get_or_create_compound(db, [], param_data.get("chemical_formula"))
                compound_id = compound.id if compound else None

            param = models.PaperData(
                paper_id=new_paper_id,
                compound_id=compound_id,
                article_type=param_data.get("article_type"),
                superconductor_type=param_data.get("superconductor_type"),
                chemical_formula=param_data.get("chemical_formula"),
                crystal_structure=param_data.get("crystal_structure"),
                tc=json.dumps(param_data.get("tc"), ensure_ascii=False) if param_data.get("tc") is not None else None,
                tc_press=json.dumps(param_data.get("tc_press"), ensure_ascii=False) if param_data.get("tc_press") is not None else None,
                lambda_val=param_data.get("lambda_val"),
                omega_log=param_data.get("omega_log"),
                n_ef=param_data.get("n_ef"),
                s_factor=param_data.get("s_factor"),
                sample_name=param_data.get("sample_name"),
                data_source_note=param_data.get("data_source_note"),
                sequence_in_paper=param_data.get("sequence_in_paper"),
            )
            db.add(param)
            imported_params += 1

        db.commit()
        print(f"   ✅ 物理参数导入完成 ({imported_params} 条)")

        print("导入文献截图...")
        imported_images = 0
        from backend.utils.image_processor import process_image

        for img_data in data.get("paper_images", []):
            new_paper_id = paper_id_mapping.get(img_data.get("paper_id"))
            if not new_paper_id:
                continue

            image_bin = None
            thumb_bin = None
            file_path = img_data.get("file_path")
            if file_path and Path(file_path).exists():
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    image_bin, thumb_bin = process_image(raw_data)
            elif "image_data" in img_data:
                image_bin = base64.b64decode(img_data["image_data"])
                if "thumbnail_data" in img_data:
                    thumb_bin = base64.b64decode(img_data["thumbnail_data"])
                else:
                    _, thumb_bin = process_image(image_bin)

            if image_bin and thumb_bin:
                image = models.PaperImage(
                    paper_id=new_paper_id,
                    image_data=image_bin,
                    thumbnail_data=thumb_bin,
                    image_order=img_data.get("image_order", 1),
                    file_size=len(image_bin)
                )
                image_db.add(image)
                imported_images += 1

        image_db.commit()
        print(f"   ✅ 截图导入完成 ({imported_images} 张)")

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        db.rollback()
        image_db.rollback()
        raise
    finally:
        db.close()
        image_db.close()


if __name__ == "__main__":
    import sys
    input_f = "data/data_export.json"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        input_f = sys.argv[1]
    
    clear = "--clear" in sys.argv
    
    if clear:
        confirm = input("⚠️  确定要清空现有数据吗？(yes/no): ")
        if confirm.lower() != "yes":
            print("取消操作")
            sys.exit(0)
            
    import_all_data(input_f, clear)