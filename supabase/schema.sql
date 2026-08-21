-- AI Business Operations Agent - Supabase PostgreSQL schema
-- Compatible with the current FastAPI + SQLAlchemy custom JWT authentication.
-- Run this file in Supabase Dashboard -> SQL Editor.

create table if not exists public.businesses (
    id serial primary key,
    name varchar(255) not null,
    category varchar(100) not null default 'General Services',
    currency varchar(10) not null default 'USD',
    timezone varchar(100) not null default 'America/New_York',
    payment_terms varchar(255) not null default 'Standard 30-day payment terms',
    email varchar(255),
    phone varchar(50),
    address text,
    email_signature text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.users (
    id serial primary key,
    name varchar(255) not null,
    email varchar(255) not null unique,
    password_hash varchar(255) not null,
    role varchar(50) not null default 'owner',
    business_id integer references public.businesses(id) on delete set null,
    created_at timestamptz not null default now()
);

create table if not exists public.customers (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    name varchar(255) not null,
    email varchar(255),
    phone varchar(50),
    company varchar(255),
    status varchar(50) not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.documents (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    file_name varchar(255) not null,
    file_path varchar(500) not null,
    file_type varchar(50),
    file_size integer,
    document_type varchar(50) not null default 'invoice',
    extracted_data jsonb,
    processing_status varchar(50) not null default 'pending',
    ocr_text text,
    created_at timestamptz not null default now()
);

create table if not exists public.invoices (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    customer_id integer references public.customers(id) on delete set null,
    invoice_number varchar(100) not null,
    amount numeric(12, 2) not null default 0.00,
    currency varchar(10) not null default 'USD',
    issue_date date not null,
    due_date date not null,
    status varchar(50) not null default 'pending',
    document_id integer references public.documents(id) on delete set null,
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (business_id, invoice_number)
);

create table if not exists public.tasks (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    title varchar(255) not null,
    description text,
    priority varchar(50) not null default 'Medium',
    status varchar(50) not null default 'Pending',
    due_date date,
    source_type varchar(50) not null default 'AI Workflow',
    source_id integer,
    assigned_user varchar(255) not null default 'Digital Employee',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.approvals (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    action_type varchar(100) not null,
    action_data jsonb not null,
    status varchar(50) not null default 'pending',
    recommendation text,
    requested_at timestamptz not null default now(),
    approved_at timestamptz,
    rejected_at timestamptz
);

create table if not exists public.activities (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    actor_type varchar(50) not null,
    action varchar(100) not null,
    description text not null,
    status varchar(50) not null default 'success',
    metadata jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.emails (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    customer_id integer references public.customers(id) on delete set null,
    subject varchar(255) not null,
    body text not null,
    recipient_email varchar(255) not null,
    status varchar(50) not null default 'draft',
    generated_by_ai boolean not null default true,
    approval_id integer references public.approvals(id) on delete set null,
    created_at timestamptz not null default now()
);

create table if not exists public.notifications (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    title varchar(255) not null,
    message text not null,
    priority varchar(50) not null default 'Medium',
    read boolean not null default false,
    action_url varchar(255),
    created_at timestamptz not null default now()
);

create table if not exists public.business_policies (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    policy_name varchar(255) not null,
    policy_type varchar(100) not null,
    threshold_value numeric(12, 2),
    condition_operator varchar(50) not null default 'gt',
    days_offset integer not null default 0,
    action_required varchar(100) not null default 'require_approval',
    is_active boolean not null default true,
    description text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.ai_memories (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    category varchar(100) not null default 'general',
    memory_key varchar(255) not null,
    memory_value text not null,
    confidence numeric(3, 2) not null default 0.95,
    source varchar(100) not null default 'AI Observation',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.workflow_rules (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    name varchar(255) not null,
    description text,
    trigger_event varchar(100) not null,
    condition_json jsonb,
    action_type varchar(100) not null,
    require_approval boolean not null default true,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.workflow_executions (
    id serial primary key,
    business_id integer not null references public.businesses(id) on delete cascade,
    rule_id integer references public.workflow_rules(id) on delete set null,
    status varchar(50) not null default 'running',
    trigger_data_json jsonb,
    execution_log_json jsonb,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index if not exists idx_users_business_id on public.users(business_id);
create index if not exists idx_customers_business_id on public.customers(business_id);
create index if not exists idx_documents_business_id on public.documents(business_id);
create index if not exists idx_invoices_business_status on public.invoices(business_id, status);
create index if not exists idx_invoices_due_date on public.invoices(business_id, due_date);
create index if not exists idx_tasks_business_priority on public.tasks(business_id, priority, status);
create index if not exists idx_approvals_business_status on public.approvals(business_id, status);
create index if not exists idx_activities_business_created on public.activities(business_id, created_at desc);
create index if not exists idx_notifications_business_read on public.notifications(business_id, read);
create index if not exists idx_policies_business_active on public.business_policies(business_id, is_active);
create index if not exists idx_memories_business_key on public.ai_memories(business_id, memory_key);
create index if not exists idx_workflow_rules_business_active on public.workflow_rules(business_id, is_active);
create index if not exists idx_workflow_executions_business_created on public.workflow_executions(business_id, created_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists businesses_set_updated_at on public.businesses;
create trigger businesses_set_updated_at before update on public.businesses
for each row execute function public.set_updated_at();
drop trigger if exists customers_set_updated_at on public.customers;
create trigger customers_set_updated_at before update on public.customers
for each row execute function public.set_updated_at();
drop trigger if exists invoices_set_updated_at on public.invoices;
create trigger invoices_set_updated_at before update on public.invoices
for each row execute function public.set_updated_at();
drop trigger if exists tasks_set_updated_at on public.tasks;
create trigger tasks_set_updated_at before update on public.tasks
for each row execute function public.set_updated_at();
drop trigger if exists business_policies_set_updated_at on public.business_policies;
create trigger business_policies_set_updated_at before update on public.business_policies
for each row execute function public.set_updated_at();
drop trigger if exists ai_memories_set_updated_at on public.ai_memories;
create trigger ai_memories_set_updated_at before update on public.ai_memories
for each row execute function public.set_updated_at();
drop trigger if exists workflow_rules_set_updated_at on public.workflow_rules;
create trigger workflow_rules_set_updated_at before update on public.workflow_rules
for each row execute function public.set_updated_at();

-- Create this private bucket after enabling Supabase Storage in the project.
insert into storage.buckets (id, name, public)
values ('business-documents', 'business-documents', false)
on conflict (id) do nothing;

-- The current application uses FastAPI custom JWTs and accesses the database
-- through SQLAlchemy. Enable RLS only after migrating authentication to
-- Supabase Auth and adding auth.uid()-based business membership policies.
