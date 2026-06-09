"""
Periodic-table element APIs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PeriodicTableElement


router = APIRouter(prefix="/api/elements", tags=["elements"])


def _element_to_dict(element: PeriodicTableElement) -> dict:
    return {
        "id": element.id,
        "symbol": element.symbol,
        "name": element.english_name,
        "name_zh": element.chinese_name,
        "atomic_number": element.atomic_number,
    }


@router.get("/")
def get_all_elements(db: Session = Depends(get_db)):
    elements = db.query(PeriodicTableElement).order_by(PeriodicTableElement.atomic_number).all()
    return [_element_to_dict(element) for element in elements]


@router.get("/{symbol}")
def get_element_by_symbol(symbol: str, db: Session = Depends(get_db)):
    element = db.query(PeriodicTableElement).filter(PeriodicTableElement.symbol == symbol).first()
    if not element:
        raise HTTPException(status_code=404, detail=f"元素 {symbol} 不存在")
    return _element_to_dict(element)
