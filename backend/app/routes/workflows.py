from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.database.session import get_db
from backend.app.models.models import WorkflowRule, WorkflowExecution, Business
from backend.app.schemas.schemas import (
    WorkflowRuleOut, WorkflowRuleCreate, WorkflowRuleUpdate, WorkflowExecutionOut
)
from backend.app.auth.deps import get_current_business
from backend.app.services.workflow_engine import execute_workflow_rule
from backend.app.services.activity_service import log_activity

router = APIRouter(prefix="/api/workflows", tags=["AI Workflows"])

@router.get("", response_model=List[WorkflowRuleOut])
def get_workflow_rules(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return db.query(WorkflowRule).filter(
        WorkflowRule.business_id == business.id
    ).order_by(WorkflowRule.id.asc()).all()


@router.post("", response_model=WorkflowRuleOut)
def create_workflow_rule(
    rule_in: WorkflowRuleCreate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    rule = WorkflowRule(
        business_id=business.id,
        name=rule_in.name,
        description=rule_in.description,
        trigger_event=rule_in.trigger_event,
        condition_json=rule_in.condition_json or {},
        action_type=rule_in.action_type,
        require_approval=rule_in.require_approval if rule_in.require_approval is not None else True,
        is_active=rule_in.is_active if rule_in.is_active is not None else True
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    log_activity(
        db,
        business_id=business.id,
        actor_type="Business Owner",
        action="Workflow Rule Configured",
        description=f"Created automated workflow rule '{rule.name}'."
    )
    return rule


@router.put("/{rule_id}", response_model=WorkflowRuleOut)
def update_workflow_rule(
    rule_id: int,
    update_in: WorkflowRuleUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    rule = db.query(WorkflowRule).filter(
        WorkflowRule.id == rule_id,
        WorkflowRule.business_id == business.id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Workflow rule not found")

    for key, val in update_in.model_dump(exclude_unset=True).items():
        setattr(rule, key, val)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
def delete_workflow_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    rule = db.query(WorkflowRule).filter(
        WorkflowRule.id == rule_id,
        WorkflowRule.business_id == business.id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Workflow rule not found")

    db.delete(rule)
    db.commit()
    return {"message": "Workflow rule deleted successfully"}


@router.post("/{rule_id}/execute")
def trigger_workflow_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    res = execute_workflow_rule(db, business, rule_id)
    return res


@router.get("/executions", response_model=List[WorkflowExecutionOut])
def get_workflow_executions(
    limit: int = 30,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    executions = db.query(WorkflowExecution).filter(
        WorkflowExecution.business_id == business.id
    ).order_by(desc(WorkflowExecution.created_at)).limit(limit).all()

    results = []
    for ex in executions:
        results.append({
            "id": ex.id,
            "business_id": ex.business_id,
            "rule_id": ex.rule_id,
            "rule_name": ex.rule.name if ex.rule else "Auto Golden Workflow",
            "status": ex.status,
            "trigger_data_json": ex.trigger_data_json,
            "execution_log_json": ex.execution_log_json,
            "created_at": ex.created_at,
            "completed_at": ex.completed_at
        })
    return results
