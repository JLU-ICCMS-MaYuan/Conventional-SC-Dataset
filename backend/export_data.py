"""
数据导出工具
将数据库中的所有数据导出为JSON文件
"""
import json
import sys
from pathlib import Path

from backend.database import MetadataSessionLocal, ImageSessionLocal
from backend import models


def export_all_data(output_file: str = "data_export.json"):
    """
    导出所有数据到JSON文件

    Args:
        output_file: 输出文件路径
    """
    db = MetadataSessionLocal()
    image_db = ImageSessionLocal()

    try:
        print("开始导出数据...")

        data = {
            "elements": [],
            "compounds": [],
            "papers": [],
            "paper_data": [],
            "paper_images": []
        }

        print("导出元素数据...")
        elements = db.query(models.Element).all()
        for elem in elements:
            data["elements"].append({
                "id": elem.id,
                "symbol": elem.symbol,
                "name": elem.name,
                "atomic_number": elem.atomic_number
            })

        print("导出元素组合数据...")
        compounds = db.query(models.Compound).all()
        for comp in compounds:
            data["compounds"].append({
                "id": comp.id,
                "chemical_formula": comp.chemical_formula,
                "element_list": json.loads(comp.element_list) if comp.element_list else [],
                "element_id_list": json.loads(comp.element_id_list) if comp.element_id_list else [],
                "composition": json.loads(comp.composition) if comp.composition else [],
                "element_ratio": json.loads(comp.element_ratio) if comp.element_ratio else [],
            })

        print("导出文献数据...")
        papers = db.query(models.Paper).all()
        for paper in papers:
            data["papers"].append({
                "id": paper.id,
                "doi": paper.doi,
                "title": paper.title,
                "authors": paper.authors,
                "journal": paper.journal,
                "volume": paper.volume,
                "pages": paper.pages,
                "year": paper.year,
                "abstract": paper.abstract,
                "contributor_name": paper.contributor_name,
                "contributor_affiliation": paper.contributor_affiliation,
                "notes": paper.notes,
                "review_status": paper.review_status,
                "review_comment": paper.review_comment,
                "show_in_chart": paper.show_in_chart,
                "created_at": paper.created_at.isoformat() if paper.created_at else None,
            })

        print("导出物理参数数据...")
        physical_params = db.query(models.PaperData).all()
        for p in physical_params:
            data["paper_data"].append({
                "id": p.id,
                "paper_id": p.paper_id,
                "compound_id": p.compound_id,
                "article_type": p.article_type,
                "superconductor_type": p.superconductor_type,
                "chemical_formula": p.chemical_formula,
                "crystal_structure": p.crystal_structure,
                "tc": p.tc_range,
                "tc_press": p.pressure_range,
                "lambda_val": p.lambda_val,
                "omega_log": p.omega_log,
                "n_ef": p.n_ef,
                "s_factor": p.s_factor,
                "sample_name": p.sample_name,
                "data_source_note": p.data_source_note,
                "sequence_in_paper": p.sequence_in_paper,
            })

        print("导出文献截图数据...")
        images_dir = Path("data/images")
        images_dir.mkdir(parents=True, exist_ok=True)

        images = image_db.query(models.PaperImage).all()
        for img in images:
            if img.image_data:
                image_filename = f"paper_{img.paper_id}_order_{img.image_order or 1}.jpg"
                image_path = images_dir / image_filename
                with open(image_path, 'wb') as f:
                    f.write(img.image_data)
                data["paper_images"].append({
                    "id": img.id,
                    "paper_id": img.paper_id,
                    "file_path": str(image_path),
                    "image_order": img.image_order or 1,
                    "file_size": img.file_size,
                    "created_at": img.created_at.isoformat() if img.created_at else None
                })
                continue

            figs = []
            for i in range(1, 41):
                blob = getattr(img, f"fig{i}", None)
                if not blob:
                    continue
                image_filename = f"paper_{img.paper_id}_fig_{i}.jpg"
                image_path = images_dir / image_filename
                with open(image_path, 'wb') as f:
                    f.write(blob)
                figs.append({
                    "id": img.id * 100 + i,
                    "paper_id": img.paper_id,
                    "file_path": str(image_path),
                    "image_order": i,
                    "file_size": len(blob),
                    "created_at": img.created_at.isoformat() if img.created_at else None
                })
            data["paper_images"].extend(figs)

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
        image_db.close()


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "data/data_export.json"
    export_all_data(output_path)
