#!/usr/bin/env python3
"""SQLite dev.db → MySQL 数据迁移"""
import sqlite3, pymysql, json, sys

SRC = "data/dev.db"
MYSQL = {"host": "127.0.0.1", "user": "work", "password": "12345678", "database": "superconductor_dataset", "charset": "utf8mb4"}

def main():
    s = sqlite3.connect(SRC)
    m = pymysql.connect(**MYSQL)
    mc = m.cursor()
    mc.execute("SET FOREIGN_KEY_CHECKS=0")

    def copy(tbl, cols, transform=None):
        rows = s.execute(f"SELECT {','.join(cols)} FROM {tbl}").fetchall()
        if not rows: return 0
        ph = ','.join(['%s']*len(cols))
        sql = f"INSERT IGNORE INTO {tbl} ({','.join(cols)}) VALUES ({ph})"
        for r in rows:
            r = list(r)
            if transform:
                for i in transform:
                    r[i] = transform[i](r[i]) if r[i] is not None else None
            mc.execute(sql, r)
        m.commit()
        return len(rows)

    # 无外键依赖表
    n = copy("periodic_table_elements",
             ["id","atomic_number","symbol","english_name","chinese_name","atomic_mass","period_number","group_number","category"],
             {2: str, 3: str, 4: str, 8: str})
    print(f"elements: {n}")

    n = copy("chemical_systems",
             ["id","system_key","elements_list","element_count","created_at","updated_at"],
             {1: str, 2: lambda v: json.dumps(v) if isinstance(v, (list,dict)) else v})
    print(f"chemical_systems: {n}")

    n = copy("users",
             ["id","email","password_hash","real_name","affiliation","role","is_approved","is_email_verified","created_at","updated_at"],
             {1: str, 2: str, 3: str, 4: str, 5: str, 6: lambda v: bool(v), 7: lambda v: bool(v)})
    print(f"users: {n}")

    n = copy("superconductors",
             ["id","chemical_system_id","chemical_formula","formula_normalized","display_name","elements_list","composition","element_ratio","created_at","updated_at"],
             {2: str, 3: str, 4: str, 5: str, 6: str, 7: str})
    print(f"superconductors: {n}")

    n = copy("papers",
             ["id","doi","title","journal","volume","pages","year","abstract","authors","uploaded_by_user_id","reviewed_by_user_id","review_status","reviewed_at","review_comment","created_at","updated_at"],
             {1: str, 2: str, 3: str, 4: str, 5: str, 7: str, 8: str, 12: str})
    print(f"papers: {n}")

    n = copy("superconductor_records",
             ["id","superconductor_id","paper_id","source_label","pressure_gpa","space_group_symbol","space_group_number","crystal_structure",
              "thermodynamically_stable","dynamically_stable","energy_above_hull","mcmillan_tc","allen_dynes_tc","isotropic_eliashberg_tc",
              "anisotropic_eliashberg_tc","experimental_tc","lambda_value","omega_log","n_ef_total","element_n_ef","pseudopotential_type",
              "pseudopotential_name","exchange_correlation_functional","calculation_code","k_grid","q_grid","energy_cutoff_value",
              "energy_cutoff_unit","show_in_chart","article_type","superconductor_type","s_factor","method","note","created_at","updated_at"],
             {3: str, 5: str, 7: str, 19: str, 20: str, 21: str, 22: str, 23: str, 24: str, 25: str, 27: str, 28: lambda v: bool(v), 29: str, 30: str, 32: str, 33: str})
    print(f"records: {n}")

    # superconductors_structures 在 SQLite 中不存在，跳过
    s_tables = {r[0] for r in s.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "superconductors_structures" in s_tables:
        n = copy("superconductors_structures",
                 ["id","superconductor_id","pressure_gpa","space_group_symbol","space_group_number","structure_format","structure_text",
                  "structure_hash","atom_count","elements_list","cell_parameters","volume","review_status","is_default","source_type",
                  "source_label","created_by_user_id","created_at","updated_at"],
                 {3: str, 5: str, 6: str, 7: str, 9: str, 10: str, 12: str, 13: lambda v: bool(v), 14: str, 15: str})
        print(f"structures: {n}")
    else:
        print("structures: 跳过 (SQLite 无此表)")

    mc.execute("SET FOREIGN_KEY_CHECKS=1")
    s.close(); m.close()
    print("\n迁移完成")

if __name__ == "__main__":
    main()
