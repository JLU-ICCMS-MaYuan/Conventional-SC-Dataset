"""
Superconductor search API.

The route keeps the historical /api/compounds prefix so the frontend can
transition without changing every caller at once.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import schemas
from backend.database import get_db
from backend.repositories.superconductors import search_superconductors


router = APIRouter(prefix="/api/compounds", tags=["compounds"])


@router.post("/search", response_model=schemas.SuperconductorSearchResponse)
def search_compounds(
    request: schemas.SuperconductorSearchRequest,
    db: Session = Depends(get_db),
):
    """Search superconductors by formula or element-set mode."""
    result = search_superconductors(
        db,
        request.mode,
        formula=request.formula,
        elements=request.elements,
        limit=request.limit,
        offset=request.offset,
    )

    return {
        "items": [
            {
                "id": item.id,
                "chemical_system_id": item.chemical_system_id,
                "chemical_formula": item.chemical_formula,
                "formula_normalized": item.formula_normalized,
                "display_name": item.display_name,
                "elements_list": item.elements_list,
                "composition": item.composition,
                "element_ratio": item.element_ratio,
            }
            for item in result.items
        ],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "has_prev": result.has_prev,
        "has_next": result.has_next,
    }
