"""
数据导出工具
将数据库中的所有数据导出为JSON文件
"""
import json
import base64
import sys
from pathlib import Path
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend import models


def export_all_data(output_file: str = "data_export.json"):
    """
    导出所有数据到JSON文件

    Args:
        output_file: 输出文件路径
    """
    db = SessionLocal()

    try:
        print("开始导出数据...")

        data = {
            "elements": [],
            "compounds": [],
            "papers": [],
            "paper_data": [],
            "paper_images": []
        }

        # 1. 导出元素（通常不需要，因为会自动初始化）
        print("导出元素数据...")
        elements = db.query(models.Element).all()
        for elem in elements:
            data["elements"].append({
                "id": elem.id,
                "symbol": elem.symbol,
                "name": elem.name,
                "atomic_number": elem.atomic_number
            })

        # 2. 导出元素组合
        print("导出元素组合数据...")
        compounds = db.query(models.Compound).all()
        compound_symbol_map = {}
        for comp in compounds:
            data["compounds"].append({
                "id": comp.id,
                "element_symbols": comp.element_symbols,
                "element_list": json.loads(comp.element_list) if comp.element_list else comp.element_symbols.split("-"),
                "created_at": comp.created_at.isoformat()
            })
            compound_symbol_map[comp.id] = comp.element_symbols

        # 3. 导出文献
        print("导出文献数据...")
        papers = db.query(models.Paper).all()
        for paper in papers:
            data["papers"].append({
                "id": paper.id,
                "element_symbols": compound_symbol_map.get(paper.compound_id),
                "doi": paper.doi,
                "title": paper.title,
                "article_type": paper.article_type,
                "superconductor_type": paper.superconductor_type,
                "authors": paper.authors,
                "journal": paper.journal,
                "volume": paper.volume,
                "pages": paper.pages,
                "year": paper.year,
                "abstract": paper.abstract,
                "citation_aps": paper.citation_aps,
                "citation_bibtex": paper.citation_bibtex,
                "chemical_formula": paper.chemical_formula,
                "crystal_structure": paper.crystal_structure,
                "contributor_name": paper.contributor_name,
                "contributor_affiliation": paper.contributor_affiliation,
                "notes": paper.notes,
                "created_at": paper.created_at.isoformat()
            })

        # 4. 导出物理参数 (PaperData)
        print("导出物理参数数据...")
        physical_params = db.query(models.PaperData).all()
        for p in physical_params:
            data["paper_data"].append({
                "id": p.id,
                "paper_id": p.paper_id,
                "pressure": p.pressure,
                "tc": p.tc,
                "lambda_val": p.lambda_val,
                "omega_log": p.omega_log,
                "n_ef": p.n_ef,
                "s_factor": p.s_factor
            })

        # 5. 导出文献截图（保存为文件并在JSON中使用链接）
        print("导出文献截图数据...")
        images_dir = Path("data/images")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        images = db.query(models.PaperImage).all()
        for img in images:
            # 生成文件名: paper_{paper_id}_order_{order}.jpg
            image_filename = f"paper_{img.paper_id}_order_{img.image_order}.jpg"
            image_path = images_dir / image_filename
            
            # 写入原图文件
            with open(image_path, 'wb') as f:
                f.write(img.image_data)
            
            data["paper_images"].append({
                "id": img.id,
                "paper_id": img.paper_id,
                "file_path": str(image_path),  # 使用本地路径
                "image_order": img.image_order,
                "file_size": img.file_size,
                "created_at": img.created_at.isoformat()
            })

        # 写入JSON文件
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 导出完成！")
        print(f"   文件位置: {output_path.absolute()}")
        print(f"   元素: {len(data['elements'])} 个")
        print(f"   元素组合: {len(data['compounds'])} 个")
        print(f"   文献: {len(data['papers'])} 篇")
        print(f"   物理参数: {len(data['paper_data'])} 条")
        print(f"   截图: {len(data['paper_images'])} 张")
        print(f"   文件大小: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

    except Exception as e:
        print(f"❌ 导出失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "data/data_export.json"
    export_all_data(output_path)
