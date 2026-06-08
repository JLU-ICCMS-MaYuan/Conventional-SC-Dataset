"""
数据库初始化脚本
创建所有表并填充118个元素数据
"""
from backend.database import (
    metadata_engine,
    image_engine,
    MetadataSessionLocal,
    MetadataBase,
    ImageBase,
    METADATA_DATABASE_PATH,
    IMAGE_DATABASE_PATH,
)
from backend.models import Element
from sqlalchemy import text


# 118个元素数据（原子序数、符号、英文名、中文名）
ELEMENTS_DATA = [
    (1, "H", "Hydrogen", "氢"),
    (2, "He", "Helium", "氦"),
    (3, "Li", "Lithium", "锂"),
    (4, "Be", "Beryllium", "铍"),
    (5, "B", "Boron", "硼"),
    (6, "C", "Carbon", "碳"),
    (7, "N", "Nitrogen", "氮"),
    (8, "O", "Oxygen", "氧"),
    (9, "F", "Fluorine", "氟"),
    (10, "Ne", "Neon", "氖"),
    (11, "Na", "Sodium", "钠"),
    (12, "Mg", "Magnesium", "镁"),
    (13, "Al", "Aluminum", "铝"),
    (14, "Si", "Silicon", "硅"),
    (15, "P", "Phosphorus", "磷"),
    (16, "S", "Sulfur", "硫"),
    (17, "Cl", "Chlorine", "氯"),
    (18, "Ar", "Argon", "氩"),
    (19, "K", "Potassium", "钾"),
    (20, "Ca", "Calcium", "钙"),
    (21, "Sc", "Scandium", "钪"),
    (22, "Ti", "Titanium", "钛"),
    (23, "V", "Vanadium", "钒"),
    (24, "Cr", "Chromium", "铬"),
    (25, "Mn", "Manganese", "锰"),
    (26, "Fe", "Iron", "铁"),
    (27, "Co", "Cobalt", "钴"),
    (28, "Ni", "Nickel", "镍"),
    (29, "Cu", "Copper", "铜"),
    (30, "Zn", "Zinc", "锌"),
    (31, "Ga", "Gallium", "镓"),
    (32, "Ge", "Germanium", "锗"),
    (33, "As", "Arsenic", "砷"),
    (34, "Se", "Selenium", "硒"),
    (35, "Br", "Bromine", "溴"),
    (36, "Kr", "Krypton", "氪"),
    (37, "Rb", "Rubidium", "铷"),
    (38, "Sr", "Strontium", "锶"),
    (39, "Y", "Yttrium", "钇"),
    (40, "Zr", "Zirconium", "锆"),
    (41, "Nb", "Niobium", "铌"),
    (42, "Mo", "Molybdenum", "钼"),
    (43, "Tc", "Technetium", "锝"),
    (44, "Ru", "Ruthenium", "钌"),
    (45, "Rh", "Rhodium", "铑"),
    (46, "Pd", "Palladium", "钯"),
    (47, "Ag", "Silver", "银"),
    (48, "Cd", "Cadmium", "镉"),
    (49, "In", "Indium", "铟"),
    (50, "Sn", "Tin", "锡"),
    (51, "Sb", "Antimony", "锑"),
    (52, "Te", "Tellurium", "碲"),
    (53, "I", "Iodine", "碘"),
    (54, "Xe", "Xenon", "氙"),
    (55, "Cs", "Cesium", "铯"),
    (56, "Ba", "Barium", "钡"),
    (57, "La", "Lanthanum", "镧"),
    (58, "Ce", "Cerium", "铈"),
    (59, "Pr", "Praseodymium", "镨"),
    (60, "Nd", "Neodymium", "钕"),
    (61, "Pm", "Promethium", "钷"),
    (62, "Sm", "Samarium", "钐"),
    (63, "Eu", "Europium", "铕"),
    (64, "Gd", "Gadolinium", "钆"),
    (65, "Tb", "Terbium", "铽"),
    (66, "Dy", "Dysprosium", "镝"),
    (67, "Ho", "Holmium", "钬"),
    (68, "Er", "Erbium", "铒"),
    (69, "Tm", "Thulium", "铥"),
    (70, "Yb", "Ytterbium", "镱"),
    (71, "Lu", "Lutetium", "镥"),
    (72, "Hf", "Hafnium", "铪"),
    (73, "Ta", "Tantalum", "钽"),
    (74, "W", "Tungsten", "钨"),
    (75, "Re", "Rhenium", "铼"),
    (76, "Os", "Osmium", "锇"),
    (77, "Ir", "Iridium", "铱"),
    (78, "Pt", "Platinum", "铂"),
    (79, "Au", "Gold", "金"),
    (80, "Hg", "Mercury", "汞"),
    (81, "Tl", "Thallium", "铊"),
    (82, "Pb", "Lead", "铅"),
    (83, "Bi", "Bismuth", "铋"),
    (84, "Po", "Polonium", "钋"),
    (85, "At", "Astatine", "砹"),
    (86, "Rn", "Radon", "氡"),
    (87, "Fr", "Francium", "钫"),
    (88, "Ra", "Radium", "镭"),
    (89, "Ac", "Actinium", "锕"),
    (90, "Th", "Thorium", "钍"),
    (91, "Pa", "Protactinium", "镤"),
    (92, "U", "Uranium", "铀"),
    (93, "Np", "Neptunium", "镎"),
    (94, "Pu", "Plutonium", "钚"),
    (95, "Am", "Americium", "镅"),
    (96, "Cm", "Curium", "锔"),
    (97, "Bk", "Berkelium", "锫"),
    (98, "Cf", "Californium", "锎"),
    (99, "Es", "Einsteinium", "锿"),
    (100, "Fm", "Fermium", "镄"),
    (101, "Md", "Mendelevium", "钔"),
    (102, "No", "Nobelium", "锘"),
    (103, "Lr", "Lawrencium", "铹"),
    (104, "Rf", "Rutherfordium", "鈩"),
    (105, "Db", "Dubnium", "𨧀"),
    (106, "Sg", "Seaborgium", "𨭎"),
    (107, "Bh", "Bohrium", "𨨏"),
    (108, "Hs", "Hassium", "𨭆"),
    (109, "Mt", "Meitnerium", "鿏"),
    (110, "Ds", "Darmstadtium", "𫟼"),
    (111, "Rg", "Roentgenium", "𬬻"),
    (112, "Cn", "Copernicium", "鿔"),
    (113, "Nh", "Nihonium", "鿭"),
    (114, "Fl", "Flerovium", "𫓧"),
    (115, "Mc", "Moscovium", "镆"),
    (116, "Lv", "Livermorium", "𫟷"),
    (117, "Ts", "Tennessine", "石田"),
    (118, "Og", "Oganesson", "气奥"),
]


def init_database():
    """初始化数据库：创建主库与图片库表，并填充元素数据"""
    print("正在创建主数据库表...")
    MetadataBase.metadata.create_all(bind=metadata_engine)
    ensure_app_columns()
    print("✓ 主数据库表创建完成")

    print("正在创建图片数据库表...")
    ImageBase.metadata.create_all(bind=image_engine)
    ensure_image_indexes()
    print("✓ 图片数据库表创建完成")

    db = MetadataSessionLocal()

    try:
        existing_count = db.query(Element).count()
        if existing_count > 0:
            print(f"数据库中已有 {existing_count} 个元素，跳过填充")
            return

        print("正在填充118个元素数据...")
        elements = []
        for atomic_number, symbol, name, name_zh in ELEMENTS_DATA:
            element = Element(
                atomic_number=atomic_number,
                symbol=symbol,
                name=name,
                name_zh=name_zh
            )
            elements.append(element)

        db.bulk_save_objects(elements)
        db.commit()
        print(f"✓ 成功填充 {len(elements)} 个元素")

    except Exception as e:
        print(f"✗ 错误: {e}")
        db.rollback()
    finally:
        db.close()

    print("\n数据库初始化完成！")
    print(f"主数据库文件位置: {METADATA_DATABASE_PATH}")
    print(f"图片数据库文件位置: {IMAGE_DATABASE_PATH}")


def ensure_app_columns():
    """为导入脚本生成的新库补齐网站业务字段。

    SQLAlchemy 的 create_all 不会修改已有表结构，因此这里对 papers 和 paper_data 做幂等补列。
    """
    paper_columns = {
        "contributor_name": "VARCHAR(100) DEFAULT 'Data Import'",
        "contributor_affiliation": "VARCHAR(200) DEFAULT 'System'",
        "notes": "TEXT",
        "review_status": "VARCHAR(20) NOT NULL DEFAULT 'unreviewed'",
        "reviewed_by": "INTEGER",
        "reviewed_at": "DATETIME",
        "review_comment": "TEXT",
        "show_in_chart": "BOOLEAN NOT NULL DEFAULT 0",
        "created_at": "DATETIME",
    }
    paper_data_columns = {
        "tc": "TEXT",
    }
    with metadata_engine.begin() as conn:
        existing_papers = {row[1] for row in conn.execute(text("PRAGMA table_info(papers)")).fetchall()}
        for name, col_type in paper_columns.items():
            if name not in existing_papers:
                conn.execute(text(f'ALTER TABLE papers ADD COLUMN "{name}" {col_type}'))

        existing_paper_data = {row[1] for row in conn.execute(text("PRAGMA table_info(paper_data)")).fetchall()}
        for name, col_type in paper_data_columns.items():
            if name not in existing_paper_data:
                conn.execute(text(f'ALTER TABLE paper_data ADD COLUMN "{name}" {col_type}'))

        conn.execute(text("UPDATE papers SET created_at = COALESCE(created_at, datetime('now'))"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_papers_review_status ON papers (review_status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_papers_year ON papers (year)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_papers_doi ON papers (doi)"))


def ensure_image_indexes():
    """为图片库补充索引。"""
    with image_engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_paper_images_paper_id ON paper_images (paper_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_paper_images_image_order ON paper_images (image_order)"))


if __name__ == "__main__":
    init_database()
