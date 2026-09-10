import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, date
from backend.app.database.session import SessionLocal, init_db
from backend.app.models.models import Business, Customer, Invoice, Approval, Task, Activity, User
from backend.app.routes.approvals import resolve_approval_execution_context, approve_action
from backend.app.schemas.schemas import EmailSendRequest, SMSSendRequest
from backend.app.routes.ai import send_email_direct
from backend.app.routes.sms import send_sms_endpoint

def run_tests():
    print("=== Starting Approval Workflow Automated Tests ===")
    init_db()
    db = SessionLocal()

    try:
        # 1. Setup Business & User
        biz = db.query(Business).first()
        if not biz:
            biz = Business(name="Test Operations Corp", currency="USD")
            db.add(biz)
            db.commit()
            db.refresh(biz)

        user = db.query(User).filter(User.business_id == biz.id).first()
        if not user:
            user = User(business_id=biz.id, email="owner@example.com", name="Test Owner", role="Owner")
            db.add(user)
            db.commit()
            db.refresh(user)

        print(f"Using Business ID: {biz.id}, User ID: {user.id}")

        # ----------------------------------------------------------------------
        # TEST 1: Email Approval with Email Contact
        # ----------------------------------------------------------------------
        print("\n--- TEST 1: Email Approval with Valid Email Contact ---")
        cust_a = Customer(
            business_id=biz.id,
            name="Alice Walker",
            email="alice.walker@example.com",
            phone="+12025550143",
            company="Walker Media"
        )
        db.add(cust_a)
        db.commit()
        db.refresh(cust_a)

        inv_a = Invoice(
            business_id=biz.id,
            customer_id=cust_a.id,
            invoice_number=f"INV-TEST-{int(datetime.utcnow().timestamp())}",
            amount=1500.00,
            paid_amount=500.00,
            pending_amount=1000.00,
            issue_date=date.today(),
            due_date=date.today(),
            status="partially_paid"
        )
        db.add(inv_a)
        db.commit()
        db.refresh(inv_a)

        app_email = Approval(
            business_id=biz.id,
            action_type="send_payment_reminder",
            action_data={
                "customer_id": cust_a.id,
                "invoice_id": inv_a.id,
                "invoice_number": inv_a.invoice_number,
                "amount": 1000.00,
                "recipient_email": cust_a.email,
                "subject": f"Payment Reminder: Invoice {inv_a.invoice_number}",
                "body": "Dear Alice, please remit pending payment of $1,000.",
                "channel": "email"
            },
            status="pending"
        )
        db.add(app_email)
        db.commit()
        db.refresh(app_email)

        ctx_a = resolve_approval_execution_context(db, app_email, biz.id)
        assert ctx_a["customer_id"] == cust_a.id, f"Expected customer_id {cust_a.id}, got {ctx_a['customer_id']}"
        assert ctx_a["invoice_id"] == inv_a.id, f"Expected invoice_id {inv_a.id}, got {ctx_a['invoice_id']}"
        assert ctx_a["communication_channel"] == "email", f"Expected email channel, got {ctx_a['communication_channel']}"
        assert ctx_a["fallback"] is False, "Expected fallback to be False"
        assert ctx_a["no_contact"] is False, "Expected no_contact to be False"
        assert ctx_a["pending_amount"] == 1000.00, f"Expected pending 1000.0, got {ctx_a['pending_amount']}"
        print("PASS: Execution context resolved accurately with email channel.")

        # Approve action
        res_approve_a = approve_action(approval_id=app_email.id, edited_data=None, db=db, business=biz)
        assert res_approve_a["success"] is True
        assert res_approve_a["status"] == "communication_ready"
        assert res_approve_a["channel"] == "email"
        db.refresh(app_email)
        assert app_email.status == "communication_ready"
        print("PASS: Approval successfully transitioned to 'communication_ready'.")

        # Now send the email direct
        email_req = EmailSendRequest(
            recipient_email=cust_a.email,
            subject=ctx_a["subject"],
            body=ctx_a["generated_message"],
            customer_id=cust_a.id,
            invoice_id=inv_a.id,
            approval_id=app_email.id
        )
        res_send_email = send_email_direct(req=email_req, db=db, business=biz)
        db.refresh(app_email)
        assert app_email.status == "sent", f"Expected approval status 'sent', got '{app_email.status}'"
        print(f"PASS: Email sent and approval #{app_email.id} status updated to 'sent'.")

        # Verify dispatched log activity
        act_email = db.query(Activity).filter(
            Activity.business_id == biz.id,
            Activity.action == "Email Dispatched"
        ).order_by(Activity.id.desc()).first()
        assert act_email is not None
        assert act_email.metadata_json.get("approval_id") == app_email.id
        assert act_email.metadata_json.get("customer_id") == cust_a.id
        assert act_email.metadata_json.get("invoice_id") == inv_a.id
        assert act_email.metadata_json.get("channel") == "Email"
        assert act_email.metadata_json.get("status") in ["SENT", "SIMULATED"]
        print(f"PASS: Dispatched Log preserved relation: {act_email.metadata_json}")

        # ----------------------------------------------------------------------
        # TEST 2: Channel Fallback (No email, but has phone)
        # ----------------------------------------------------------------------
        print("\n--- TEST 2: Channel Fallback (No Email, Has Phone) ---")
        cust_b = Customer(
            business_id=biz.id,
            name="Bob Builder",
            email="", # No email
            phone="+12025550188",
            company="BuildCo"
        )
        db.add(cust_b)
        db.commit()
        db.refresh(cust_b)

        inv_b = Invoice(
            business_id=biz.id,
            customer_id=cust_b.id,
            invoice_number=f"INV-TEST-{int(datetime.utcnow().timestamp()) + 1}",
            amount=800.00,
            paid_amount=0.00,
            pending_amount=800.00,
            issue_date=date.today(),
            due_date=date.today(),
            status="overdue"
        )
        db.add(inv_b)
        db.commit()
        db.refresh(inv_b)

        app_fallback = Approval(
            business_id=biz.id,
            action_type="send_payment_reminder",
            action_data={
                "customer_id": cust_b.id,
                "invoice_id": inv_b.id,
                "amount": 800.00,
                "channel": "email" # Originally email requested
            },
            status="pending"
        )
        db.add(app_fallback)
        db.commit()
        db.refresh(app_fallback)

        ctx_b = resolve_approval_execution_context(db, app_fallback, biz.id)
        assert ctx_b["communication_channel"] == "sms", f"Expected fallback to 'sms', got {ctx_b['communication_channel']}"
        assert ctx_b["fallback"] is True, "Expected fallback to be True"
        assert "Email is not available" in ctx_b["fallback_reason"]
        print(f"PASS: Successfully fell back to SMS with reason: '{ctx_b['fallback_reason']}'")

        # Approve fallback action
        res_approve_b = approve_action(approval_id=app_fallback.id, edited_data=None, db=db, business=biz)
        assert res_approve_b["channel"] == "sms"
        assert res_approve_b["fallback"] is True

        # Send via SMS
        sms_req = SMSSendRequest(
            customer_id=cust_b.id,
            phone_number=cust_b.phone,
            message="Payment reminder: $800 overdue for Invoice.",
            approval_id=app_fallback.id,
            invoice_id=inv_b.id
        )
        send_sms_endpoint(req=sms_req, db=db, current_user=user, business=biz)
        db.refresh(app_fallback)
        assert app_fallback.status == "sent", f"Expected approval status 'sent', got '{app_fallback.status}'"
        print(f"PASS: SMS dispatched and approval #{app_fallback.id} status updated to 'sent'.")

        act_sms = db.query(Activity).filter(
            Activity.business_id == biz.id,
            Activity.action == "SMS Communication Dispatched"
        ).order_by(Activity.id.desc()).first()
        assert act_sms is not None
        assert act_sms.metadata_json.get("approval_id") == app_fallback.id
        assert act_sms.metadata_json.get("channel") == "SMS"
        assert act_sms.metadata_json.get("status") == "SENT"
        print(f"PASS: Dispatched Log for SMS preserved relation: {act_sms.metadata_json}")

        # ----------------------------------------------------------------------
        # TEST 3: No Contact Workflow (Neither email nor phone)
        # ----------------------------------------------------------------------
        print("\n--- TEST 3: No Contact Available Workflow ---")
        cust_c = Customer(
            business_id=biz.id,
            name="Charlie Ghost",
            email=None,
            phone=None,
            company="Ghost Holdings"
        )
        db.add(cust_c)
        db.commit()
        db.refresh(cust_c)

        app_no_contact = Approval(
            business_id=biz.id,
            action_type="send_payment_reminder",
            action_data={"customer_id": cust_c.id, "amount": 350.00},
            status="pending"
        )
        db.add(app_no_contact)
        db.commit()
        db.refresh(app_no_contact)

        res_no_contact = approve_action(approval_id=app_no_contact.id, edited_data=None, db=db, business=biz)
        assert res_no_contact["success"] is False
        assert res_no_contact["no_contact"] is True
        print(f"PASS: Correctly rejected immediate execution for customer without contact.")

        # Verify follow-up task was generated
        followup_task = db.query(Task).filter(
            Task.business_id == biz.id,
            Task.title == "No communication contact available for this customer",
            Task.source_id == app_no_contact.id
        ).first()
        assert followup_task is not None, "Expected follow-up Task to be created"
        assert followup_task.priority == "High"
        print(f"PASS: Follow-up Task #{followup_task.id} successfully created: '{followup_task.description}'")

        # ----------------------------------------------------------------------
        # TEST 4: Invoice Auto-Selection Order
        # ----------------------------------------------------------------------
        print("\n--- TEST 4: Invoice Auto-Selection Order ---")
        # Customer with multiple invoices
        cust_d = Customer(business_id=biz.id, name="Diana Prince", email="diana@example.com")
        db.add(cust_d)
        db.commit()
        db.refresh(cust_d)

        # 1. Paid invoice
        inv_paid = Invoice(
            business_id=biz.id, customer_id=cust_d.id, invoice_number="INV-PAID-01",
            amount=500.0, paid_amount=500.0, pending_amount=0.0, status="paid",
            issue_date=date.today(), due_date=date(2026, 1, 1)
        )
        # 2. Overdue invoice
        inv_overdue = Invoice(
            business_id=biz.id, customer_id=cust_d.id, invoice_number="INV-OVERDUE-02",
            amount=1200.0, paid_amount=0.0, pending_amount=1200.0, status="overdue",
            issue_date=date.today(), due_date=date(2026, 2, 1)
        )
        # 3. Pending/Partially paid invoice
        inv_pending = Invoice(
            business_id=biz.id, customer_id=cust_d.id, invoice_number="INV-PENDING-03",
            amount=2000.0, paid_amount=500.0, pending_amount=1500.0, status="partially_paid",
            issue_date=date.today(), due_date=date(2026, 3, 1)
        )
        db.add_all([inv_paid, inv_overdue, inv_pending])
        db.commit()

        # Create approval with NO explicit invoice_id
        app_d = Approval(
            business_id=biz.id,
            action_type="send_payment_reminder",
            action_data={"customer_id": cust_d.id},
            status="pending"
        )
        db.add(app_d)
        db.commit()
        db.refresh(app_d)

        ctx_d = resolve_approval_execution_context(db, app_d, biz.id)
        # Priority #1 is pending/partially paid
        assert ctx_d["invoice_id"] == inv_pending.id, f"Expected pending invoice {inv_pending.id}, got {ctx_d['invoice_id']}"
        print(f"PASS: Correctly auto-selected partially paid invoice #{ctx_d['invoice_number']} for customer.")

        print("\n=== ALL AUTOMATED TESTS PASSED SUCCESSFULLY ===")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
