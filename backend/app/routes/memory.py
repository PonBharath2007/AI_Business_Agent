from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import AIMemory, Business
from backend.app.schemas.schemas import AIMemoryOut, AIMemoryCreate, AIMemoryUpdate
from backend.app.auth.deps import get_current_business
from backend.app.services.activity_service import log_activity

router = APIRouter(prefix="/api/memory", tags=["AI Business Memory"])

@router.get("", response_model=List[AIMemoryOut])
def get_memories(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    query = db.query(AIMemory).filter(AIMemory.business_id == business.id)
    if category and category != "all":
        query = query.filter(AIMemory.category == category)
    return query.order_by(AIMemory.updated_at.desc()).all()


@router.post("", response_model=AIMemoryOut)
def create_memory(
    mem_in: AIMemoryCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    mem = AIMemory(
        business_id=business.id,
        category=mem_in.category or "general",
        memory_key=mem_in.memory_key,
        memory_value=mem_in.memory_value,
        confidence=mem_in.confidence or 0.95,
        source=mem_in.source or "Owner Setting"
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="AI Memory Added",
        description=f"Recorded business knowledge item: '{mem.memory_key}'."
    )
    return mem


@router.put("/{memory_id}", response_model=AIMemoryOut)
def update_memory(
    memory_id: int,
    update_in: AIMemoryUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    mem = db.query(AIMemory).filter(
        AIMemory.id == memory_id,
        AIMemory.business_id == business.id
    ).first()

    if not mem:
        raise HTTPException(status_code=404, detail="AI Memory record not found")

    for key, val in update_in.model_dump(exclude_unset=True).items():
        setattr(mem, key, val)

    db.commit()
    db.refresh(mem)
    return mem


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    mem = db.query(AIMemory).filter(
        AIMemory.id == memory_id,
        AIMemory.business_id == business.id
    ).first()

    if not mem:
        raise HTTPException(status_code=404, detail="AI Memory record not found")

    db.delete(mem)
    db.commit()
    return {"message": "Memory item removed successfully"}
