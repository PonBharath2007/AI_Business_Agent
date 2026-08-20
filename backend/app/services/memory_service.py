from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import AIMemory, Business
from backend.app.utils.logger import logger

def get_business_memories(db: Session, business_id: int, category: Optional[str] = None) -> List[AIMemory]:
    query = db.query(AIMemory).filter(AIMemory.business_id == business_id)
    if category and category != "all":
        query = query.filter(AIMemory.category == category)
    return query.order_by(AIMemory.updated_at.desc()).all()

def format_memories_for_ai(db: Session, business_id: int) -> str:
    memories = get_business_memories(db, business_id)
    if not memories:
        return "No specific business memories recorded yet."
    
    lines = []
    for m in memories:
        lines.append(f"- [{m.category.upper()}] {m.memory_key}: {m.memory_value} (Confidence: {int(float(m.confidence or 0.95)*100)}%)")
    return "\n".join(lines)

def add_or_update_memory(
    db: Session,
    business_id: int,
    key: str,
    value: str,
    category: str = "general",
    confidence: float = 0.95,
    source: str = "AI Observation"
) -> AIMemory:
    existing = db.query(AIMemory).filter(
        AIMemory.business_id == business_id,
        AIMemory.memory_key == key
    ).first()

    if existing:
        existing.memory_value = value
        existing.category = category
        existing.confidence = confidence
        existing.source = source
        db.commit()
        db.refresh(existing)
        return existing
    
    new_mem = AIMemory(
        business_id=business_id,
        category=category,
        memory_key=key,
        memory_value=value,
        confidence=confidence,
        source=source
    )
    db.add(new_mem)
    db.commit()
    db.refresh(new_mem)
    return new_mem
