from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import Business
from backend.app.schemas.schemas import (
    BusinessHealthScoreOut, CashFlowForecastOut,
    RootCauseAnalysisRequest, RootCauseAnalysisOut,
    WhatIfSimulationRequest, WhatIfSimulationOut
)
from backend.app.auth.deps import get_current_business
from backend.app.services.business_intelligence import (
    calculate_business_health_score, calculate_cash_flow_forecast,
    analyze_root_cause_for_delays, run_what_if_simulation, get_customer_360
)

router = APIRouter(prefix="/api/intelligence", tags=["Business Intelligence & AI Analytics"])

@router.get("/health-score", response_model=BusinessHealthScoreOut)
def get_health_score(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return calculate_business_health_score(db, business)


@router.get("/cash-flow", response_model=CashFlowForecastOut)
def get_cash_flow(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return calculate_cash_flow_forecast(db, business)


@router.post("/root-cause", response_model=RootCauseAnalysisOut)
def run_root_cause(
    req: RootCauseAnalysisRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return analyze_root_cause_for_delays(db, business, req.query or "Why are payments getting delayed?")


@router.post("/what-if", response_model=WhatIfSimulationOut)
def run_simulation(
    req: WhatIfSimulationRequest,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    return run_what_if_simulation(db, business, req.model_dump())


@router.get("/customer-360/{customer_id}")
def get_customer_360_data(
    customer_id: int,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    data = get_customer_360(db, business, customer_id)
    if not data:
        raise HTTPException(status_code=404, detail="Customer not found")
    return data
