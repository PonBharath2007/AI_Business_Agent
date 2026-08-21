import sys
import os
from datetime import date, datetime, timedelta

# Add repository root to pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.app.database.session import SessionLocal
from backend.app.models.models import Business, Task, Invoice, Customer, Approval
from backend.app.services.business_intelligence import get_active_exceptions

def run_test():
    db = SessionLocal()
    try:
        # Get or create test business
        biz = db.query(Business).first()
        if not biz:
            biz = Business(name="Test Biz", email="testbiz@example.com", currency="USD")
            db.add(biz)
            db.commit()
            db.refresh(biz)

        today = date.today()

        # Clean up existing test tasks
        db.query(Task).filter(Task.business_id == biz.id, Task.title.like("TEST_EXC_%")).delete()
        db.commit()

        # 1. Critical: Overdue Task
        t_overdue = Task(
            business_id=biz.id,
            title="TEST_EXC_Overdue_Task",
            description="Sample overdue task",
            priority="Medium",
            status="Pending",
            due_date=today - timedelta(days=5),
            created_at=datetime.utcnow() - timedelta(days=6)
        )

        # 2. Critical: High Priority Overdue Task
        t_high_overdue = Task(
            business_id=biz.id,
            title="TEST_EXC_High_Overdue_Task",
            description="Sample high priority overdue task",
            priority="High",
            status="In Progress",
            due_date=today - timedelta(days=2),
            created_at=datetime.utcnow() - timedelta(days=3)
        )

        # 3. High Priority: Pending < 15 days (e.g. 4 days old, not overdue)
        t_recent_pending = Task(
            business_id=biz.id,
            title="TEST_EXC_Recent_Pending_Task",
            description="Sample recent pending task",
            priority="Low",
            status="Pending",
            due_date=today + timedelta(days=10),
            created_at=datetime.utcnow() - timedelta(days=4)
        )

        # 4. Medium Priority: Pending >= 15 days (e.g. 20 days old, not overdue)
        t_aging_pending = Task(
            business_id=biz.id,
            title="TEST_EXC_Aging_Pending_Task",
            description="Sample aging pending task",
            priority="Medium",
            status="Pending",
            due_date=today + timedelta(days=5),
            created_at=datetime.utcnow() - timedelta(days=20)
        )

        # 5. Completed Task (Should NOT be in exceptions)
        t_completed = Task(
            business_id=biz.id,
            title="TEST_EXC_Completed_Task",
            description="Sample completed task",
            priority="High",
            status="Completed",
            due_date=today - timedelta(days=10),
            created_at=datetime.utcnow() - timedelta(days=12)
        )

        db.add_all([t_overdue, t_high_overdue, t_recent_pending, t_aging_pending, t_completed])
        db.commit()
        db.refresh(t_overdue)
        db.refresh(t_high_overdue)
        db.refresh(t_recent_pending)
        db.refresh(t_aging_pending)
        db.refresh(t_completed)

        # Run get_active_exceptions
        exceptions = get_active_exceptions(db, biz)
        task_exceptions = [e for e in exceptions if e.get("entity_type") == "task" and "TEST_EXC_" in e.get("title", "")]

        print(f"\n--- Found {len(task_exceptions)} Test Task Exceptions ---")
        for exc in task_exceptions:
            print(f"ID: {exc['id']} | Severity: {exc['severity']} | Category: {exc['category']} | Title: {exc['title']}")

        # Verify Test 1: Overdue Task is CRITICAL
        exc1 = next((e for e in task_exceptions if e["entity_id"] == t_overdue.id), None)
        assert exc1 is not None, "t_overdue not found in exceptions"
        assert exc1["severity"] == "CRITICAL", f"Expected CRITICAL, got {exc1['severity']}"
        assert exc1["category"] == "Overdue Task"
        print("[PASS] Test 1: Overdue Task -> CRITICAL")

        # Verify Test 2: High Priority Overdue Task is CRITICAL
        exc2 = next((e for e in task_exceptions if e["entity_id"] == t_high_overdue.id), None)
        assert exc2 is not None, "t_high_overdue not found in exceptions"
        assert exc2["severity"] == "CRITICAL", f"Expected CRITICAL, got {exc2['severity']}"
        assert exc2["category"] == "Overdue Task"
        print("[PASS] Test 2: High Priority Overdue Task -> CRITICAL")

        # Verify Test 3: Pending < 15 days is HIGH
        exc3 = next((e for e in task_exceptions if e["entity_id"] == t_recent_pending.id), None)
        assert exc3 is not None, "t_recent_pending not found in exceptions"
        assert exc3["severity"] == "HIGH", f"Expected HIGH, got {exc3['severity']}"
        assert "Active Task (< 15d)" in exc3["category"]
        print("[PASS] Test 3: Pending < 15 days -> HIGH")

        # Verify Test 4: Pending >= 15 days is MEDIUM
        exc4 = next((e for e in task_exceptions if e["entity_id"] == t_aging_pending.id), None)
        assert exc4 is not None, "t_aging_pending not found in exceptions"
        assert exc4["severity"] == "MEDIUM", f"Expected MEDIUM, got {exc4['severity']}"
        assert "Aging Task (> 15d)" in exc4["category"]
        print("[PASS] Test 4: Pending >= 15 days -> MEDIUM")

        # Verify Test 5: Completed Task is NOT in exceptions
        exc5 = next((e for e in task_exceptions if e["entity_id"] == t_completed.id), None)
        assert exc5 is None, "Completed task should NOT appear in exceptions"
        print("[PASS] Test 5: Completed Task -> Excluded")

        # Clean up test tasks
        db.query(Task).filter(Task.business_id == biz.id, Task.title.like("TEST_EXC_%")).delete()
        db.commit()

        print("\nALL TASK EXCEPTION CLASSIFICATION TESTS PASSED SUCCESSFULLY! [OK]\n")
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
