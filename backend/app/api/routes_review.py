from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from backend.app.schemas import ReviewCorrectionRequest, ReviewQueueItem
from backend.app.active_learning.review_queue_manager import ActiveLearningManager
from backend.app.shelf_pipeline.sku_matcher import SkuMatcher

router = APIRouter(prefix="/review-queue", tags=["Active Learning"])

sku_matcher = SkuMatcher()
review_manager = ActiveLearningManager(sku_matcher=sku_matcher)

@router.get("", response_model=List[ReviewQueueItem])
def get_review_queue(limit: int = 50):
    return review_manager.get_pending_reviews(limit=limit)

@router.post("/{item_id}/correct")
def submit_review_correction(item_id: str, req: ReviewCorrectionRequest):
    try:
        res = review_manager.submit_correction(
            item_id=item_id,
            corrected_sku_id=req.corrected_sku_id,
            corrected_by=req.corrected_by,
            create_as_new_sku=req.create_as_new_sku,
            new_sku_name=req.new_sku_name,
            new_sku_category=req.new_sku_category or "General"
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
