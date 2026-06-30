from __future__ import annotations

from sqlalchemy.orm import Session

from backend import models


_SYMBOLS = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
]

_NAMES = {
    "H": ("Hydrogen", "氢"),
    "He": ("Helium", "氦"),
}


def seed_periodic_table_elements(db: Session) -> None:
    for atomic_number, symbol in enumerate(_SYMBOLS, start=1):
        existing = db.query(models.PeriodicTableElement).filter_by(symbol=symbol).first()
        english_name, chinese_name = _NAMES.get(symbol, (symbol, None))
        if existing:
            existing.atomic_number = atomic_number
            existing.english_name = english_name
            existing.chinese_name = chinese_name
            continue
        db.add(
            models.PeriodicTableElement(
                atomic_number=atomic_number,
                symbol=symbol,
                english_name=english_name,
                chinese_name=chinese_name,
            )
        )
    db.commit()
