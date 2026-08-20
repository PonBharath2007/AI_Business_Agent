from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import Task, Business
from backend.app.schemas.schemas import TaskCreate, TaskUpdate, TaskOut
from backend.app.auth.deps import get_current_business
from backend.app.services.activity_service import log_activity

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

@router.get("", response_model=List[TaskOut])
def get_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    query = db.query(Task).filter(Task.business_id == business.id)
    if status_filter and status_filter != "all":
        query = query.filter(Task.status.ilike(status_filter))
    if priority_filter and priority_filter != "all":
        query = query.filter(Task.priority.ilike(priority_filter))

    tasks = query.order_by(
        # High priority first, then due date
        desc(Task.priority == "High"),
        desc(Task.priority == "Medium"),
        Task.due_date.asc().nullslast()
    ).all()
    return tasks


@router.post("", response_model=TaskOut)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    task = Task(
        business_id=business.id,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority or "Medium",
        status=task_in.status or "Pending",
        due_date=task_in.due_date,
        source_type=task_in.source_type or "Manual",
        source_id=task_in.source_id,
        assigned_user=task_in.assigned_user or "Business Owner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Task Created",
        description=f"Created task: '{task.title}' [{task.priority} Priority].",
        metadata={"task_id": task.id}
    )

    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    task = db.query(Task).filter(Task.id == task_id, Task.business_id == business.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    task = db.query(Task).filter(Task.id == task_id, Task.business_id == business.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.status
    for key, val in task_in.model_dump(exclude_unset=True).items():
        setattr(task, key, val)

    db.commit()
    db.refresh(task)

    if task.status != old_status and task.status == "Completed":
        log_activity(
            db,
            business_id=business.id,
            actor_type="Business Owner",
            action="Task Completed",
            description=f"Marked task '{task.title}' as Completed."
        )

    return task


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    task = db.query(Task).filter(Task.id == task_id, Task.business_id == business.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "Completed"
    db.commit()
    db.refresh(task)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Task Completed",
        description=f"Marked task '{task.title}' as Completed."
    )

    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    task = db.query(Task).filter(Task.id == task_id, Task.business_id == business.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task removed successfully"}
