from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date,
    DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database.base import Base

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="General Services")
    currency = Column(String(10), default="USD")
    timezone = Column(String(50), default="America/New_York")
    payment_terms = Column(String(255), default="Standard 30-day payment terms")
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    email_signature = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="business", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="business", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="business", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="business", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="business", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="business", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="business", cascade="all, delete-orphan")
    emails = relationship("Email", back_populates="business", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="business", cascade="all, delete-orphan")
    policies = relationship("BusinessPolicy", back_populates="business", cascade="all, delete-orphan")
    memories = relationship("AIMemory", back_populates="business", cascade="all, delete-orphan")
    workflow_rules = relationship("WorkflowRule", back_populates="business", cascade="all, delete-orphan")
    workflow_executions = relationship("WorkflowExecution", back_populates="business", cascade="all, delete-orphan")
    communications = relationship("CommunicationLog", back_populates="business", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    role = Column(String(50), default="owner")
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    auth_provider = Column(String(50), default="local")  # local, google
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    profile_picture = Column(String(500), nullable=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="users")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    status = Column(String(50), default="active") # active, inactive, lead
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")
    emails = relationship("Email", back_populates="customer")
    communications = relationship("CommunicationLog", back_populates="customer", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True) # pdf, png, jpg, docx
    file_size = Column(Integer, nullable=True)
    document_type = Column(String(50), default="invoice") # invoice, receipt, contract, statement, general
    extracted_data = Column(JSON, nullable=True)
    processing_status = Column(String(50), default="pending") # pending, processing, completed, failed
    ocr_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="documents")
    invoices = relationship("Invoice", back_populates="document")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_number = Column(String(100), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    currency = Column(String(10), default="USD")
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), default="pending", index=True) # paid, pending, overdue
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    document = relationship("Document", back_populates="invoices")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(50), default="Medium", index=True) # High, Medium, Low
    status = Column(String(50), default="Pending", index=True) # Pending, In Progress, Completed, Rejected
    due_date = Column(Date, nullable=True)
    source_type = Column(String(50), default="AI Workflow") # AI Workflow, AI Document, Manual, System
    source_id = Column(Integer, nullable=True)
    assigned_user = Column(String(255), default="Digital Employee")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="tasks")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False) # send_payment_reminder, dispatch_task, customer_followup, etc.
    action_data = Column(JSON, nullable=False)
    status = Column(String(50), default="pending", index=True) # pending, approved, rejected, executed
    recommendation = Column(Text, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="approvals")
    emails = relationship("Email", back_populates="approval")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_type = Column(String(50), nullable=False) # AI Agent, Business Owner, System
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="success") # success, warning, failed
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    business = relationship("Business", back_populates="activities")


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    recipient_email = Column(String(255), nullable=False)
    status = Column(String(50), default="draft") # draft, sent, queued, failed
    generated_by_ai = Column(Boolean, default=True)
    approval_id = Column(Integer, ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="emails")
    customer = relationship("Customer", back_populates="emails")
    approval = relationship("Approval", back_populates="emails")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(50), default="Medium") # High, Medium, Low
    read = Column(Boolean, default=False, index=True)
    action_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="notifications")


class BusinessPolicy(Base):
    __tablename__ = "business_policies"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_name = Column(String(255), nullable=False)
    policy_type = Column(String(100), nullable=False) # payment_terms, approval_threshold, overdue_reminder, escalation, external_comm_hitl
    threshold_value = Column(Numeric(12, 2), nullable=True) # e.g. 50000.00
    condition_operator = Column(String(50), default="gt") # gt, gte, lt, lte, eq, days_past
    days_offset = Column(Integer, default=0) # e.g. 7 for 7 days overdue
    action_required = Column(String(100), default="require_approval") # require_approval, auto_reminder, escalate_task, block_action
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="policies")


class AIMemory(Base):
    __tablename__ = "ai_memories"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), default="general") # customer_preference, payment_behavior, business_instruction, workflow_rule
    memory_key = Column(String(255), nullable=False, index=True)
    memory_value = Column(Text, nullable=False)
    confidence = Column(Numeric(3, 2), default=0.95) # 0.00 to 1.00
    source = Column(String(100), default="AI Observation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="memories")


class WorkflowRule(Base):
    __tablename__ = "workflow_rules"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_event = Column(String(100), nullable=False) # invoice_overdue, invoice_uploaded, high_amount, contract_expiring
    condition_json = Column(JSON, nullable=True) # e.g. {"amount_gt": 50000, "days_overdue": 7}
    action_type = Column(String(100), nullable=False) # generate_reminder, create_task, alert_owner, send_email
    require_approval = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="workflow_rules")
    executions = relationship("WorkflowExecution", back_populates="rule", cascade="all, delete-orphan")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(Integer, ForeignKey("workflow_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="running") # running, pending_approval, executed, failed, skipped
    trigger_data_json = Column(JSON, nullable=True)
    execution_log_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="workflow_executions")
    rule = relationship("WorkflowRule", back_populates="executions")


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    communication_type = Column(String(50), nullable=False, index=True)  # email, sms, call
    language = Column(String(20), default="en", index=True)  # en, ta, en_ta
    recipient = Column(String(255), nullable=False)  # email address or phone number
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="draft", index=True)  # draft, pending, approved, sent, failed, rejected
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    business = relationship("Business", back_populates="communications")
    customer = relationship("Customer", back_populates="communications")

