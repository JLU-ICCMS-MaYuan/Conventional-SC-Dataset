"""
数据库初始化脚本
创建所有表并填充118个元素数据
"""
from backend.database import engine, SessionLocal, Base
from backend.models import Element


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
    """初始化数据库：创建表并填充元素数据"""
    print("正在创建数据库表...")

    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建完成")

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 检查是否已经有元素数据
        existing_count = db.query(Element).count()
        if existing_count > 0:
            print(f"数据库中已有 {existing_count} 个元素，跳过填充")
            return

        # 填充118个元素数据
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
    print(f"数据库文件位置: {engine.url.database}")


if __name__ == "__main__":
    init_database()
