"""
Deprecated migration entrypoint.

The redesigned MySQL schema no longer stores `compound_id` or `element_id_list`.
Element identity is represented by `chemical_systems.elements_list` and
`superconductors.elements_list`.
"""


def migrate_compound_ids() -> None:
    print("无需执行：新 MySQL 结构不再使用旧 compound_id / element_id_list。")


if __name__ == "__main__":
    migrate_compound_ids()
