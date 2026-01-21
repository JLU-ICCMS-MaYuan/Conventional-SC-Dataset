"""
数据导入工具
从JSON文件导入数据到数据库
"""
import json
import base64
import math
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine
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

    db = SessionLocal()
    valid_elements = get_all_element_symbols(db)

    try:
        print(f"读取数据文件: {input_path}...")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if clear_existing:
            print("⚠️  清空现有数据...")
            # 注意：不再删除 CompoundElement，因为它已被移除
            db.query(models.PaperImage).delete()
            db.query(models.PaperData).delete()
            db.query(models.Paper).delete()
            db.query(models.Compound).delete()
            db.commit()

        # 映射表
        compound_id_mapping = {}  # 旧ID -> 新ID
        paper_id_mapping = {}

        # 1. 导入或创建元素组合
        print("处理元素组合...")
        compounds_to_process = data.get("compounds", [])
        
        # 如果JSON里没有compounds，从papers中提取
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
                            "id": p.get("compound_id", -1), # 临时ID
                            "element_symbols": combo_key,
                            "element_list": std_list,
                            "created_at": p.get("created_at", datetime.now().isoformat())
                        })
                        seen_combos.add(combo_key)

        for comp_data in compounds_to_process:
            raw_symbols = comp_data.get("element_list") or comp_data["element_symbols"].split("-")
            std_list = standardize_elements(raw_symbols, valid_elements)
            
            if not std_list:
                print(f"   ⚠️ 跳过无效组合: {comp_data.get('element_symbols')}")
                continue

            # 使用 CRUD 逻辑确保标准化
            compound = crud.get_or_create_compound(db, std_list)
            compound_id_mapping[comp_data["id"]] = compound.id
            # 同时记录原始字符串到映射，以防paper引用它
            compound_id_mapping[comp_data["element_symbols"]] = compound.id

        db.commit()
        print(f"   ✅ 元素组合准备就绪")

        # 2. 导入文献
        print("导入文献...")
        for paper_data in data.get("papers", []):
            # 确定所属化合物
            new_compound_id = None
            
            # 尝试多种方式匹配化合物
            old_cid = paper_data.get("compound_id")
            if old_cid in compound_id_mapping:
                new_compound_id = compound_id_mapping[old_cid]
            
            if not new_compound_id:
                raw_symbols = paper_data.get("element_list") or paper_data.get("element_symbols", "").split("-")
                std_list = standardize_elements(raw_symbols, valid_elements)
                if std_list:
                    compound = crud.get_or_create_compound(db, std_list)
                    new_compound_id = compound.id

            if not new_compound_id:
                print(f"   ⚠️ 跳过文献 {paper_data.get('doi')} (无法识别元素组合)")
                continue

            # 检查重复
            existing = db.query(models.Paper).filter(
                models.Paper.compound_id == new_compound_id,
                models.Paper.doi == paper_data["doi"]
            ).first()

            if existing:
                paper_id_mapping[paper_data["id"]] = existing.id
                continue

            # 正常导入
            paper = models.Paper(
                compound_id=new_compound_id,
                doi=paper_data["doi"],
                title=paper_data["title"],
                article_type=paper_data["article_type"],
                superconductor_type=paper_data["superconductor_type"],
                authors=paper_data["authors"],
                journal=paper_data["journal"],
                volume=paper_data.get("volume", ""),
                pages=paper_data.get("pages", ""),
                year=paper_data.get("year"),
                abstract=paper_data.get("abstract", ""),
                citation_aps=paper_data.get("citation_aps", ""),
                citation_bibtex=paper_data.get("citation_bibtex", ""),
                chemical_formula=paper_data.get("chemical_formula"),
                crystal_structure=paper_data.get("crystal_structure"),
                contributor_name=paper_data.get("contributor_name", "Data Import"),
                contributor_affiliation=paper_data.get("contributor_affiliation", "System"),
                notes=paper_data.get("notes", ""),
                created_at=datetime.fromisoformat(paper_data["created_at"]) if "created_at" in paper_data else datetime.now()
            )
            db.add(paper)
            db.flush()
            paper_id_mapping[paper_data["id"]] = paper.id

        db.commit()
        print(f"   ✅ 文献导入完成 ({len(paper_id_mapping)} 篇)")

        # 3. 导入物理参数
        print("导入物理参数...")
        imported_params = 0
        for param_data in data.get("paper_data", []):
            old_paper_id = param_data.get("paper_id")
            new_paper_id = paper_id_mapping.get(old_paper_id)
            if not new_paper_id: continue

            param = models.PaperData(
                paper_id=new_paper_id,
                pressure=param_data.get("pressure"),
                tc=param_data.get("tc"),
                lambda_val=param_data.get("lambda_val"),
                omega_log=param_data.get("omega_log"),
                n_ef=param_data.get("n_ef"),
                s_factor=param_data.get("s_factor")
            )
            db.add(param)
            imported_params += 1

        db.commit()
        print(f"   ✅ 物理参数导入完成")

        # 4. 导入截图
        print("导入文献截图...")
        imported_images = 0
        from backend.utils.image_processor import process_image

        for img_data in data.get("paper_images", []):
            new_paper_id = paper_id_mapping.get(img_data.get("paper_id"))
            if not new_paper_id: continue

            image_bin = None
            thumb_bin = None

            # 优先从文件路径读取
            file_path = img_data.get("file_path")
            if file_path and Path(file_path).exists():
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    image_bin, thumb_bin = process_image(raw_data)
            # 否则从 Base64 读取
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
                    image_order=img_data["image_order"],
                    file_size=len(image_bin)
                )
                db.add(image)
                imported_images += 1

        db.commit()
        print(f"   ✅ 截图导入完成")

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


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