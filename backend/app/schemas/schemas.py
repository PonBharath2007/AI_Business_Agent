from datetime import datetime, date
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field

# ----------------- AUTH & USER SCHEMAS -----------------
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    business_name: Optional[str] = "My Business"
    currency: Optional[str] = "USD"

class UserForgotPassword(BaseModel):
    email: EmailStr
    new_password: Optional[str] = None

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    business_id: Optional[int] = None
    business_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ----------------- BUSINESS SCHEMAS -----------------
class BusinessBase(BaseModel):
    name: str
    category: Optional[str] = "General Services"
    currency: Optional[str] = "USD"
    timezone: Optional[str] = "America/New_York"
    payment_terms: Optional[str] = "Standard 30-day payment terms"
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email_signature: Optional[str] = None

class BusinessCreate(BusinessBase):
    pass

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    payment_terms: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email_signature: Optional[str] = None

class BusinessOut(BusinessBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- CUSTOMER SCHEMAS -----------------
class CustomerBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = "active"

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None

class CustomerOut(CustomerBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: datetime
    total_invoices: Optional[int] = 0
    pending_amount: Optional[float] = 0.0
    overdue_amount: Optional[float] = 0.0
    last_communication: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----------------- DOCUMENT SCHEMAS -----------------
class DocumentOut(BaseModel):
    id: int
    business_id: int
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    document_type: Optional[str] = "invoice"
    extracted_data: Optional[Dict[str, Any]] = None
    processing_status: str
    ocr_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentAnalysisRequest(BaseModel):
    create_entities: Optional[bool] = True

# ----------------- INVOICE SCHEMAS -----------------
class InvoiceBase(BaseModel):
    customer_id: Optional[int] = None
    invoice_number: str
    amount: float
    currency: Optional[str] = "USD"
    issue_date: date
    due_date: date
    status: Optional[str] = "pending" # paid, pending, overdue
    document_id: Optional[int] = None
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    customer_id: Optional[int] = None
    invoice_number: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class InvoiceOut(InvoiceBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_company: Optional[str] = None
    priority: Optional[str] = "Medium"

    class Config:
        from_attributes = True

# ----------------- TASK SCHEMAS -----------------
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "Medium" # High, Medium, Low
    status: Optional[str] = "Pending" # Pending, In Progress, Completed, Rejected
    due_date: Optional[date] = None
    source_type: Optional[str] = "Manual"
    source_id: Optional[int] = None
    assigned_user: Optional[str] = "Digital Employee"

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    assigned_user: Optional[str] = None

class TaskOut(TaskBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- APPROVAL SCHEMAS -----------------
class ApprovalBase(BaseModel):
    action_type: str
    action_data: Dict[str, Any]
    status: Optional[str] = "pending"
    recommendation: Optional[str] = None

class ApprovalCreate(ApprovalBase):
    pass

class ApprovalUpdate(BaseModel):
    action_data: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None

class ApprovalOut(ApprovalBase):
    id: int
    business_id: int
    requested_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----------------- ACTIVITY & AUDIT SCHEMAS -----------------
class ActivityOut(BaseModel):
    id: int
    business_id: int
    actor_type: str
    action: str
    description: str
    status: str
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- EMAIL SCHEMAS -----------------
class EmailGenerateRequest(BaseModel):
    customer_id: Optional[int] = None
    invoice_id: Optional[int] = None
    template_type: Optional[str] = "payment_reminder" # payment_reminder, customer_followup, appointment_confirmation, general_inquiry
    tone: Optional[str] = "professional" # professional, friendly, urgent, formal
    custom_instructions: Optional[str] = None

class EmailSendRequest(BaseModel):
    recipient_email: str
    subject: str
    body: str
    customer_id: Optional[int] = None
    approval_id: Optional[int] = None

class EmailOut(BaseModel):
    id: int
    business_id: int
    customer_id: Optional[int] = None
    subject: str
    body: str
    recipient_email: str
    status: str
    generated_by_ai: bool
    approval_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- NOTIFICATION SCHEMAS -----------------
class NotificationOut(BaseModel):
    id: int
    business_id: int
    title: str
    message: str
    priority: str
    read: bool
    action_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- AI & COMMAND CENTER SCHEMAS -----------------
class AIChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = []

class AIChatResponse(BaseModel):
    response: str
    suggested_actions: Optional[List[Dict[str, Any]]] = []
    data_references: Optional[Dict[str, Any]] = None

class AIDailyBriefResponse(BaseModel):
    headline: str
    overdue_count: int
    overdue_amount: float
    pending_tasks_count: int
    high_priority_tasks_count: int
    pending_approvals_count: int
    brief_markdown: str
    recommended_actions: List[Dict[str, Any]]

# ----------------- DASHBOARD & ANALYTICS SCHEMAS -----------------
class DashboardSummary(BaseModel):
    total_customers: int
    pending_invoices_count: int
    pending_invoices_amount: float
    overdue_invoices_count: int
    overdue_invoices_amount: float
    pending_tasks_count: int
    high_priority_tasks_count: int
    pending_approvals_count: int
    ai_actions_count: int
    completed_tasks_count: int
    currency: str

class AnalyticsOverview(BaseModel):
    summary: DashboardSummary
    invoice_status_distribution: Dict[str, int]
    invoice_amount_by_status: Dict[str, float]
    task_priority_distribution: Dict[str, int]
    task_status_distribution: Dict[str, int]
    monthly_activity_trend: List[Dict[str, Any]]
    automation_metrics: Dict[str, Any]

# ----------------- BUSINESS POLICIES SCHEMAS -----------------
class BusinessPolicyBase(BaseModel):
    policy_name: str
    policy_type: str # payment_terms, approval_threshold, overdue_reminder, escalation, external_comm_hitl
    threshold_value: Optional[float] = None
    condition_operator: Optional[str] = "gt"
    days_offset: Optional[int] = 0
    action_required: Optional[str] = "require_approval"
    is_active: Optional[bool] = True
    description: Optional[str] = None

class BusinessPolicyCreate(BusinessPolicyBase):
    pass

class BusinessPolicyUpdate(BaseModel):
    policy_name: Optional[str] = None
    policy_type: Optional[str] = None
    threshold_value: Optional[float] = None
    condition_operator: Optional[str] = None
    days_offset: Optional[int] = None
    action_required: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class BusinessPolicyOut(BusinessPolicyBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- AI BUSINESS MEMORY SCHEMAS -----------------
class AIMemoryBase(BaseModel):
    category: Optional[str] = "general" # customer_preference, payment_behavior, business_instruction, workflow_rule
    memory_key: str
    memory_value: str
    confidence: Optional[float] = 0.95
    source: Optional[str] = "AI Observation"

class AIMemoryCreate(AIMemoryBase):
    pass

class AIMemoryUpdate(BaseModel):
    category: Optional[str] = None
    memory_key: Optional[str] = None
    memory_value: Optional[str] = None
    confidence: Optional[float] = None

class AIMemoryOut(AIMemoryBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- WORKFLOW RULE & EXECUTION SCHEMAS -----------------
class WorkflowRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_event: str # invoice_overdue, invoice_uploaded, high_amount, contract_expiring
    condition_json: Optional[Dict[str, Any]] = None
    action_type: str # generate_reminder, create_task, alert_owner, send_email
    require_approval: Optional[bool] = True
    is_active: Optional[bool] = True

class WorkflowRuleCreate(WorkflowRuleBase):
    pass

class WorkflowRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_event: Optional[str] = None
    condition_json: Optional[Dict[str, Any]] = None
    action_type: Optional[str] = None
    require_approval: Optional[bool] = None
    is_active: Optional[bool] = None

class WorkflowRuleOut(WorkflowRuleBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkflowExecutionOut(BaseModel):
    id: int
    business_id: int
    rule_id: Optional[int] = None
    rule_name: Optional[str] = None
    status: str
    trigger_data_json: Optional[Dict[str, Any]] = None
    execution_log_json: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----------------- BUSINESS HEALTH SCORE & BI SCHEMAS -----------------
class HealthCategoryScore(BaseModel):
    name: str
    score: int # 0 to 100
    weight: float
    status: str # Excellent, Good, Fair, Critical
    insight: str

class BusinessHealthScoreOut(BaseModel):
    overall_score: int # 0 to 100
    rating: str # Optimal, Stable, Needs Attention, High Risk
    currency: str
    categories: List[HealthCategoryScore]
    ai_recommendations: List[str]

class CashFlowForecastOut(BaseModel):
    currency: str
    expected_inflow_30d: float
    outstanding_receivables: float
    overdue_receivables: float
    projected_net_position: float
    aging_buckets: Dict[str, float]
    ai_cashflow_summary: str
    confidence_level: str

class RootCauseAnalysisRequest(BaseModel):
    query: Optional[str] = "Why are payments getting delayed?"

class RootCauseFactor(BaseModel):
    factor: str
    severity: str # High, Medium, Low
    data_evidence: str
    suggested_fix: str

class RootCauseAnalysisOut(BaseModel):
    primary_finding: str
    delay_rate: str
    average_overdue_days: int
    key_factors: List[RootCauseFactor]
    ai_action_plan: List[str]

class WhatIfSimulationRequest(BaseModel):
    scenario: str # payment_delay, early_discount, reminder_blitz, custom
    param_days_delay: Optional[int] = 30
    param_discount_pct: Optional[float] = 5.0
    param_collection_boost_pct: Optional[float] = 25.0
    custom_prompt: Optional[str] = None

class WhatIfSimulationOut(BaseModel):
    scenario_title: str
    baseline_cash_inflow: float
    simulated_cash_inflow: float
    net_variance: float
    impact_percentage: str
    health_score_impact: str
    detailed_projection_markdown: str
    is_simulation: bool = True

class ExceptionItemOut(BaseModel):
    id: str
    severity: str # CRITICAL, HIGH, MEDIUM, LOW
    category: str # Overdue Invoice, Duplicate Detected, High Amount, Missing Fields, Expiring Contract, Pending Approval
    title: str
    description: str
    entity_type: str # invoice, customer, approval, task, document
    entity_id: Optional[int] = None
    suggested_action: str
    action_type: str # navigate, approve, generate_reminder, view
    action_target: str

