from fastapi import APIRouter, HTTPException, Path
from datetime import datetime
from typing import List
from datetime import datetime

from src.services.besluit_service import BesluitService
from src.config.settings import get_settings
from src.api.models.besluiten import VerkeersBesluitResponse

router = APIRouter()
settings = get_settings()
besluit_service = BesluitService(settings=settings)

@router.get("/{date_str}", summary="Get traffic decisions for a specific date range")
async def get_besluiten_by_date(
    date_str: str = Path(..., description="Date in YYYY-MM-DD format", regex=r"^\d{4}-\d{2}-\d{2}$")
) -> List[VerkeersBesluitResponse]:
    """
    Retrieves all traffic decisions for a given date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        List of processed verkeersbesluit data including metadata, text, and image URLs
    """
    try:
        return besluit_service.get_besluiten_for_date(date_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")