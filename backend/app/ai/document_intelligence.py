import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import Customer
from backend.app.ai.gemini_client import gemini_client
from backend.app.services.document_processor import get_file_bytes_and_mimetype
from backend.app.utils.helpers import parse_date, parse_amount
from backend.app.utils.logger import logger


def analyze_document_with_ai(
    file_name: str,
    raw_text: str,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tiered Enterprise Document Intelligence Pipeline:
    1. Tier 1 (Multimodal Vision): If file_path is provided and Gemini is configured,
       processes complete document/image bytes directly using Gemini multimodal vision.
    2. Tier 2 (Text-based LLM): If Gemini configured, processes full multi-page text + tables.
    3. Tier 3 (Deterministic Multi-Page Financial Parser): Extracts tables, regex financial patterns,
       line items, totals, dates, customer info directly from full document text and layout.
    All outputs are strictly normalized, validated for mathematical consistency, and NEVER
    fall back to fake demo records (e.g. ABC Ltd or INV-1001).
    """
    ai_result = None

    structured_prompt = f"""
You are an expert enterprise financial document intelligence system.
You must use only the information extracted from the uploaded invoice. Do not invent, assume, or guess values. If information is missing, return null or "Not found". Output strictly valid JSON.

Document Filename: {file_name}

Extract complete invoice information into a single JSON object with these exact keys:
{{
  "document_type": "invoice" | "receipt" | "contract" | "statement" | "purchase_order" | "general",
  "invoice_number": "Exact invoice number or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "customer_id": "Customer identifier or null",
  "customer_name": "Full customer/client name from Bill To, or null",
  "customer_email": "Customer email or null",
  "customer_phone": "Customer phone or null",
  "billing_address": "Customer billing address or null",
  "seller_name": "Vendor / Seller / Issuer business name, or null",
  "seller_address": "Vendor / Seller address or null",
  "tax_number": "GSTIN / VAT / Tax ID or null",
  "currency": "Currency code (INR, USD, EUR, GBP)",
  "subtotal": 0.0,
  "tax": 0.0,
  "discount": 0.0,
  "total_amount": 0.0,
  "paid_amount": 0.0,
  "pending_amount": 0.0,
  "payment_status": "paid" | "partially_paid" | "pending" | "overdue",
  "priority": "High" | "Medium" | "Low",
  "summary": "1-2 sentence executive summary of this actual invoice",
  "recommended_action": "Operational next step based on actual payment balance",
  "line_items": [
     {{
       "description": "Item description",
       "quantity": 1,
       "unit_price": 0.0,
       "tax": 0.0,
       "discount": 0.0,
       "line_total": 0.0
     }}
  ],
  "notes": "Bank payment details, terms or notes found on document, or null"
}}
"""

    system_instruction = (
        "You are an enterprise financial document extraction system. "
        "You must use only the information extracted from the uploaded invoice. "
        "Do not invent, assume, or guess values. If information is missing, return null. "
        "Output strictly valid JSON."
    )

    # 1. Try Gemini Multimodal directly on document bytes (PDF / Image)
    if file_path and os.path.exists(file_path) and gemini_client.is_configured:
        try:
            file_bytes, mime_type = get_file_bytes_and_mimetype(file_path)
            if file_bytes and len(file_bytes) > 0:
                ai_result = gemini_client.generate_json_multimodal(
                    file_bytes=file_bytes,
                    mime_type=mime_type,
                    prompt=structured_prompt,
                    system_instruction=system_instruction
                )
                if ai_result and isinstance(ai_result, dict) and ("invoice_number" in ai_result or "total_amount" in ai_result or "customer_name" in ai_result):
                    logger.info("Successfully extracted structured data using Gemini multimodal vision.")
                    normalized = normalize_extracted_document(ai_result, file_name, raw_text)
                    return validate_invoice_extraction(normalized)
        except Exception as exc:
            logger.warning(f"Multimodal Gemini extraction failed: {exc}")

    # 2. Try Gemini Text-based if configured and text is available
    clean_text = (raw_text or "").strip()
    if not ai_result and gemini_client.is_configured and len(clean_text) > 20:
        try:
            text_prompt = f"{structured_prompt}\n\nFull Document Text & Tables:\n\"\"\"\n{clean_text[:60000]}\n\"\"\""
            ai_result = gemini_client.generate_json(
                text_prompt,
                system_instruction=system_instruction
            )
            if ai_result and isinstance(ai_result, dict) and ("invoice_number" in ai_result or "total_amount" in ai_result or "customer_name" in ai_result):
                logger.info("Successfully extracted structured data using Gemini text intelligence.")
                normalized = normalize_extracted_document(ai_result, file_name, raw_text)
                return validate_invoice_extraction(normalized)
        except Exception as exc:
            logger.warning(f"Text Gemini extraction failed: {exc}")

    # 3. Deterministic High-Precision Multi-Page Parser
    parsed = deterministic_invoice_parser(file_name, clean_text)
    normalized = normalize_extracted_document(parsed, file_name, clean_text)
    return validate_invoice_extraction(normalized)


def parse_clean_date(date_str: Optional[str]) -> Optional[date]:
    """Parses various date formats commonly found in Indian, US, and international invoices."""
    if not date_str:
        return None
    cleaned = re.sub(r'[\r\n|]+', ' ', str(date_str)).strip()

    month_patterns = [
        r'%d-%b-%Y', r'%d %b %Y', r'%d-%B-%Y', r'%d %B %Y',
        r'%B %d, %Y', r'%b %d, %Y', r'%d/%m/%Y', r'%d-%m-%Y',
        r'%Y-%m-%d', r'%m/%d/%Y', r'%m-%d-%Y'
    ]
    for fmt in month_patterns:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except (ValueError, TypeError):
            continue

    return parse_date(cleaned)


def deterministic_invoice_parser(file_name: str, raw_text: str) -> Dict[str, Any]:
    """
    High-precision, rule-based financial invoice and document parser.
    Processes full multi-page content, tables, and financial layouts.
    Extracts honest values and nulls if missing, NEVER fabricated demo records.
    """
    text_lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    text_lower = raw_text.lower()
    file_lower = file_name.lower()
    today = date.today()

    # 1. Document Type Detection
    doc_type = "invoice"
    if "tax invoice" in text_lower or "tax-invoice" in text_lower or "invoice" in text_lower:
        doc_type = "invoice"
    elif "receipt" in text_lower or "receipt" in file_lower:
        doc_type = "receipt"
    elif "purchase order" in text_lower or "po #" in text_lower:
        doc_type = "purchase_order"
    elif "statement" in text_lower:
        doc_type = "statement"
    elif "contract" in text_lower or "agreement" in text_lower:
        doc_type = "contract"

    # 2. Invoice Number Extraction
    invoice_number = None
    inv_table_match = re.search(r'\|\s*Invoice\s*No\.?\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if inv_table_match and inv_table_match.group(1).strip():
        val = inv_table_match.group(1).strip()
        if not re.match(r'^(invoice|tax invoice|no|number)$', val, re.IGNORECASE):
            invoice_number = val

    if not invoice_number:
        inv_text_match = re.search(r'(?:Invoice\s*No\.?|Bill\s*No\.?|Invoice\s*#|Inv\s*#|Invoice\s*Number)[:\s]+([A-Za-z0-9\-_/]+)', raw_text, re.IGNORECASE)
        if inv_text_match:
            candidate = inv_text_match.group(1).strip()
            if candidate.lower() not in ["invoice", "tax", "no", "date"]:
                invoice_number = candidate

    if not invoice_number:
        code_match = re.search(r'\b(INV-[A-Za-z0-9\-_]+|BILL-[A-Za-z0-9\-_]+)\b', raw_text, re.IGNORECASE)
        if code_match:
            invoice_number = code_match.group(1).strip()

    # 3. Vendor / Seller Extraction
    seller_name = None
    vendor_match = re.search(r'(?:From|Sold\s*By|Seller|Vendor|Issuer|Supplier)[:\s]+([^\n\r,]+)', raw_text, re.IGNORECASE)
    if vendor_match:
        cand = vendor_match.group(1).strip()
        if cand.lower() not in ["name", "address", "phone", "gstin"]:
            seller_name = cand

    if not seller_name:
        for line in text_lines[:6]:
            if not any(k in line.lower() for k in ["===", "page", "table", "tax invoice", "bill to", "invoice no", "date"]):
                if len(line) > 3 and not re.search(r'\b(inv-|date|phone|gstin|email)\b', line, re.IGNORECASE):
                    seller_name = line
                    break

    seller_address = None
    addr_match = re.search(r'(?:Seller\s*Address|Vendor\s*Address|From\s*Address)[:\s]+([^\n\r]+)', raw_text, re.IGNORECASE)
    if addr_match:
        seller_address = addr_match.group(1).strip()

    # 4. Tax Number / GSTIN
    tax_number = None
    gst_m = re.search(r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b', raw_text)
    if gst_m:
        tax_number = gst_m.group(1).strip()
    else:
        tax_m = re.search(r'(?:GSTIN|Tax\s*ID|VAT\s*No|Tax\s*Number)[:\s|]+([A-Za-z0-9\-]+)', raw_text, re.IGNORECASE)
        if tax_m:
            tax_number = tax_m.group(1).strip()

    # 5. Customer / "Bill To" Extraction
    customer_name = None
    customer_id = None
    customer_phone = None
    customer_email = None
    billing_address = None

    cid_m = re.search(r'(?:Customer\s*ID|Client\s*ID|Cust\s*ID)[:\s]+([A-Za-z0-9\-]+)', raw_text, re.IGNORECASE)
    if cid_m:
        customer_id = cid_m.group(1).strip()

    bill_to_table_match = re.search(r'\|\s*Bill\s*To\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if bill_to_table_match:
        cand = bill_to_table_match.group(1).strip()
        if cand and cand.lower() not in ["name", "customer", "client", "address"]:
            customer_name = cand

    if not customer_name:
        bill_to_text_match = re.search(r'(?:Bill\s*To|Billed\s*To|Customer\s*Name|Invoice\s*To|Buyer|M/s)[:\s\n]+([^\n\r,]+)', raw_text, re.IGNORECASE)
        if bill_to_text_match:
            cand = bill_to_text_match.group(1).strip()
            if cand and cand.lower() not in ["phone", "address", "gstin", "email"]:
                customer_name = cand

    phone_match = re.search(r'(?:Phone|Mobile|Tel)[:\s|]+(\+?[\d\s-]{10,15})', raw_text, re.IGNORECASE)
    if phone_match:
        customer_phone = phone_match.group(1).strip()

    email_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
    if email_matches:
        customer_email = email_matches[0]

    b_addr_m = re.search(r'(?:Billing\s*Address|Bill\s*To\s*Address)[:\s]+([^\n\r]+)', raw_text, re.IGNORECASE)
    if b_addr_m:
        billing_address = b_addr_m.group(1).strip()

    # 6. Dates Extraction
    issue_date = None
    due_date = None

    inv_date_m = re.search(r'\|\s*Invoice\s*Date\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if inv_date_m:
        issue_date = parse_clean_date(inv_date_m.group(1).strip())

    if not issue_date:
        inv_date_m2 = re.search(r'(?:Invoice\s*Date|Bill\s*Date|Issue\s*Date|Date)[:\s]+([A-Za-z0-9\s,\-/]+)', raw_text, re.IGNORECASE)
        if inv_date_m2:
            issue_date = parse_clean_date(inv_date_m2.group(1).strip())

    due_date_m = re.search(r'\|\s*Due\s*Date\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if due_date_m:
        due_date = parse_clean_date(due_date_m.group(1).strip())

    if not due_date:
        due_date_m2 = re.search(r'(?:Due\s*Date|Payment\s*Due)[:\s]+([A-Za-z0-9\s,\-/]+)', raw_text, re.IGNORECASE)
        if due_date_m2:
            due_date = parse_clean_date(due_date_m2.group(1).strip())

    if not issue_date or not due_date:
        all_dates = re.findall(r'(\d{1,2}-[A-Za-z]{3}-\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})', raw_text)
        parsed_dates = [d for d in [parse_clean_date(ds) for ds in all_dates] if d is not None]
        if parsed_dates:
            if not issue_date:
                issue_date = parsed_dates[0]
            if not due_date and len(parsed_dates) > 1:
                due_date = parsed_dates[1]

    if not issue_date:
        issue_date = today
    if not due_date:
        due_date = issue_date + timedelta(days=14)

    # 7. Currency Detection
    currency = "USD"
    if any(sym in raw_text for sym in ["₹", "INR", "Rs", "GSTIN", "Coimbatore", "Tamil Nadu"]) or re.search(r'\b(GST|CGST|SGST|IGST)\b', raw_text):
        currency = "INR"
    elif "€" in raw_text or "eur" in text_lower:
        currency = "EUR"
    elif "£" in raw_text or "gbp" in text_lower:
        currency = "GBP"

    # 8. Financial Totals
    grand_total = None
    subtotal = None
    total_tax = None
    discount = 0.0
    paid_amount = 0.0
    pending_amount = None

    gt_match = re.search(r'\|\s*(?:Grand\s*Total|Total\s*Amount|Net\s*Payable|Invoice\s*Total)\s*\|\s*([^|\r\n]*[\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if not gt_match:
        gt_match = re.search(r'\|\s*Total\s*\|\s*([^|\r\n]*[\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if gt_match:
        grand_total = parse_amount(gt_match.group(1))

    if grand_total is None:
        gt_text = re.search(r'(?:Grand\s*Total|Total\s*Amount|Net\s*Payable|Total\s*Due)[\s:]*[$₹€£nI]?\s*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
        if gt_text:
            grand_total = parse_amount(gt_text.group(1))

    sub_match = re.search(r'\|\s*Subtotal\s*\|\s*([^|\r\n]*[\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if sub_match:
        subtotal = parse_amount(sub_match.group(1))

    tax_m = re.search(r'\|\s*(?:Total\s*GST|Tax|Total\s*Tax)\s*\|\s*([^|\r\n]*[\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if tax_m:
        total_tax = parse_amount(tax_m.group(1))

    disc_m = re.search(r'\|\s*(?:Discount)\s*\|\s*([^|\r\n]*[\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if disc_m:
        discount = parse_amount(disc_m.group(1)) or 0.0

    paid_m = re.search(r'\|\s*(?:Paid|Amount\s*Paid|Advance\s*Paid|Received)\s*\|\s*([^|\r\n]*[\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if paid_m:
        paid_amount = parse_amount(paid_m.group(1)) or 0.0

    bal_match = re.search(r'\|\s*(?:Balance\s*Due|Pending\s*Amount|Amount\s*Due)\s*\|\s*([^|\r\n]*[\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if bal_match:
        pending_amount = parse_amount(bal_match.group(1))

    # 9. Line Items Extraction
    items = []
    for line in raw_text.split('\n'):
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 4 and parts[0].isdigit():
                desc = parts[1]
                qty_str = parts[2] if len(parts) > 2 else "1"
                price_str = parts[3] if len(parts) > 3 else "0"
                total_str = parts[-1] if len(parts) > 4 else "0"

                qty = float(qty_str) if qty_str.replace('.', '', 1).isdigit() else 1.0
                price_clean = re.sub(r'[^0-9.]', '', price_str)
                price = float(price_clean) if price_clean else 0.0
                total_clean = re.sub(r'[^0-9.]', '', total_str)
                line_tot = float(total_clean) if total_clean else (qty * price)

                items.append({
                    "description": desc,
                    "quantity": qty,
                    "unit_price": price,
                    "tax": 0.0,
                    "discount": 0.0,
                    "line_total": line_tot
                })

    if (grand_total is None or grand_total <= 0) and items:
        grand_total = sum(it["line_total"] for it in items)

    final_total = float(grand_total or 0.0)

    # 10. Status & Balance Calculation
    payment_status = "pending"
    status_match = re.search(r'\|\s*Payment\s*Status\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if status_match:
        st_val = status_match.group(1).strip().lower()
        if "partial" in st_val:
            payment_status = "partially_paid"
        elif "overdue" in st_val:
            payment_status = "overdue"
        elif "paid" in st_val:
            payment_status = "paid"
        elif "pending" in st_val:
            payment_status = "pending"

    if payment_status == "paid":
        paid_amount = final_total
        pending_amount = 0.0
    else:
        if pending_amount is None:
            pending_amount = max(0.0, final_total - paid_amount)
        if paid_amount > 0 and pending_amount > 0:
            payment_status = "partially_paid"
        elif due_date < today and payment_status != "paid":
            payment_status = "overdue"

    notes = None
    notes_m = re.search(r'(?:Notes|Terms|Payment\s*Instructions)[:\s]+([^\n\r]+)', raw_text, re.IGNORECASE)
    if notes_m:
        notes = notes_m.group(1).strip()

    return {
        "document_type": doc_type,
        "invoice_number": invoice_number,
        "invoice_date": issue_date.isoformat(),
        "issue_date": issue_date.isoformat(),
        "due_date": due_date.isoformat(),
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "billing_address": billing_address,
        "seller_name": seller_name,
        "seller_address": seller_address,
        "tax_number": tax_number,
        "currency": currency,
        "subtotal": subtotal or final_total,
        "tax": total_tax or 0.0,
        "discount": discount,
        "total_amount": final_total,
        "amount": final_total,
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "payment_status": payment_status,
        "line_items": items,
        "notes": notes
    }


def normalize_extracted_document(data: Dict[str, Any], file_name: str, raw_text: str) -> Dict[str, Any]:
    """
    Standardizes field names, calculates missing balances, and ensures consistent structures.
    NEVER substitutes fake demo values.
    """
    today = date.today()

    issue_date_val = parse_clean_date(data.get("issue_date") or data.get("invoice_date")) or today
    due_date_val = parse_clean_date(data.get("due_date")) or (issue_date_val + timedelta(days=14))

    total = parse_amount(data.get("total_amount") or data.get("amount") or 0.0)
    subtotal = parse_amount(data.get("subtotal") or total)
    tax = parse_amount(data.get("tax") or data.get("tax_amount") or 0.0)
    discount = parse_amount(data.get("discount") or data.get("discount_amount") or 0.0)
    paid = parse_amount(data.get("paid_amount") or 0.0)
    pending = parse_amount(data.get("pending_amount"))

    status = str(data.get("payment_status", "")).lower().strip()

    if "partial" in status:
        status = "partially_paid"
        if pending is None:
            pending = max(0.0, total - paid)
    elif "paid" in status:
        status = "paid"
        if paid == 0.0 and total > 0.0:
            paid = total
        pending = 0.0
    else:
        if pending is None:
            pending = max(0.0, total - paid)
        if paid > 0 and pending > 0:
            status = "partially_paid"
        elif due_date_val < today:
            status = "overdue"
        elif not status:
            status = "pending"

    # Line items formatting
    raw_items = data.get("line_items") or data.get("items") or []
    formatted_items = []
    for item in raw_items:
        if isinstance(item, dict):
            qty = float(item.get("quantity") or 1.0)
            u_price = parse_amount(item.get("unit_price") or 0.0)
            l_tot = parse_amount(item.get("line_total") or item.get("total") or (qty * u_price))
            formatted_items.append({
                "description": item.get("description") or "Item",
                "quantity": qty,
                "unit_price": u_price,
                "tax": parse_amount(item.get("tax") or 0.0),
                "discount": parse_amount(item.get("discount") or 0.0),
                "line_total": l_tot
            })

    # Summary & Action
    inv_num = data.get("invoice_number") or "Unnumbered Document"
    cust_disp = data.get("customer_name") or "Unspecified Customer"
    curr = data.get("currency") or ("INR" if ("₹" in raw_text or "inr" in raw_text.lower()) else "USD")

    summary = data.get("summary")
    if not summary:
        summary = f"Invoice {inv_num} for {cust_disp} totaling {curr} {total:,.2f} is currently {status.upper()}."

    action = data.get("recommended_action")
    if not action:
        if status == "paid":
            action = "Invoice is fully paid. No reminder needed. Reconcile and archive record."
        elif status == "overdue":
            action = f"Payment is overdue since {due_date_val.isoformat()}. Send urgent reminder for {curr} {pending:,.2f}."
        elif status == "partially_paid":
            action = f"Partially paid. Request remaining balance of {curr} {pending:,.2f}."
        else:
            action = f"Payment due on {due_date_val.isoformat()}. Monitor until due date."

    return {
        "document_type": data.get("document_type") or "invoice",
        "invoice_number": data.get("invoice_number"),
        "invoice_date": issue_date_val.isoformat(),
        "issue_date": issue_date_val.isoformat(),
        "due_date": due_date_val.isoformat(),
        "customer_id": data.get("customer_id"),
        "customer_name": data.get("customer_name"),
        "customer_email": data.get("customer_email"),
        "customer_phone": data.get("customer_phone"),
        "billing_address": data.get("billing_address"),
        "seller_name": data.get("seller_name") or data.get("vendor_name"),
        "seller_address": data.get("seller_address"),
        "tax_number": data.get("tax_number"),
        "currency": curr,
        "subtotal": subtotal,
        "tax": tax,
        "tax_amount": tax,
        "discount": discount,
        "discount_amount": discount,
        "total_amount": total,
        "amount": total,
        "paid_amount": paid,
        "pending_amount": pending,
        "payment_status": status,
        "priority": data.get("priority") or ("High" if status == "overdue" or total > 10000 else "Medium"),
        "is_overdue": (status == "overdue"),
        "days_overdue": (today - due_date_val).days if status == "overdue" else 0,
        "summary": summary,
        "recommended_action": action,
        "line_items": formatted_items,
        "items": formatted_items,
        "notes": data.get("notes")
    }


def validate_invoice_extraction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 5: Full Document Validation.
    Verifies mathematical consistency:
      subtotal + tax - discount ≈ total
      total - paid ≈ pending
    If values do not match within tolerance (1.50), marks document 'NEEDS_REVIEW'
    and adds human-readable verification warnings.
    """
    validation_warnings = []
    total = float(data.get("total_amount") or 0.0)
    subtotal = float(data.get("subtotal") or 0.0)
    tax = float(data.get("tax") or 0.0)
    discount = float(data.get("discount") or 0.0)
    paid = float(data.get("paid_amount") or 0.0)
    pending = float(data.get("pending_amount") if data.get("pending_amount") is not None else max(0.0, total - paid))

    # Math check 1: subtotal + tax - discount ≈ total
    if subtotal > 0 and total > 0:
        expected_total = subtotal + tax - discount
        if abs(expected_total - total) > 1.50:
            validation_warnings.append(
                f"Invoice total could not be verified: Subtotal ({subtotal:,.2f}) + Tax ({tax:,.2f}) - Discount ({discount:,.2f}) = {expected_total:,.2f}, but Total is {total:,.2f}."
            )

    # Math check 2: total - paid ≈ pending
    if total > 0:
        expected_pending = max(0.0, total - paid)
        if abs(expected_pending - pending) > 1.50:
            validation_warnings.append(
                f"Pending amount could not be verified: Total ({total:,.2f}) - Paid ({paid:,.2f}) = {expected_pending:,.2f}, but Pending is {pending:,.2f}."
            )

    # Missing critical fields
    if not data.get("invoice_number"):
        validation_warnings.append("Invoice number could not be found.")
    if not data.get("customer_name"):
        validation_warnings.append("Customer name could not be found.")
    if total <= 0:
        validation_warnings.append("Total amount was zero or could not be found.")

    validation_status = "VALID" if not validation_warnings else "NEEDS_REVIEW"
    data["validation_status"] = validation_status
    data["validation_warnings"] = validation_warnings
    data["validation_errors"] = validation_warnings
    data["ai_confidence"] = 95 if not validation_warnings else max(50, 95 - (len(validation_warnings) * 15))
    data["confidence_score"] = data["ai_confidence"]
    data["math_validation"] = {
        "is_valid": validation_status == "VALID",
        "warnings": validation_warnings
    }
    return data


def match_existing_customer(db: Session, business_id: int, extracted: Dict[str, Any]) -> Tuple[Optional[Customer], str]:
    """
    Step 6: Customer Matching Engine.
    Matches invoice with existing customer in order:
    1. Existing customer ID if present
    2. Exact email match
    3. Exact phone match
    4. Carefully normalized customer name
    Returns (customer, match_reason) or (None, "Customer match requires review")
    """
    # 1. Customer ID if present
    raw_cid = extracted.get("customer_id")
    if raw_cid:
        try:
            cid_int = int(str(raw_cid).strip())
            c = db.query(Customer).filter(Customer.id == cid_int, Customer.business_id == business_id).first()
            if c:
                return c, f"Matched by Customer ID #{c.id}"
        except (ValueError, TypeError):
            pass

    # 2. Exact email match
    email = (extracted.get("customer_email") or "").strip().lower()
    if email and "@" in email:
        c = db.query(Customer).filter(Customer.business_id == business_id, Customer.email.ilike(email)).first()
        if c:
            return c, f"Matched by exact Email '{c.email}'"

    # 3. Exact phone match (compare normalized digits)
    phone = (extracted.get("customer_phone") or "").strip()
    phone_digits = re.sub(r'\D', '', phone)
    if len(phone_digits) >= 10:
        for c in db.query(Customer).filter(Customer.business_id == business_id).all():
            if c.phone:
                c_digits = re.sub(r'\D', '', c.phone)
                if c_digits and (phone_digits.endswith(c_digits[-10:]) or c_digits.endswith(phone_digits[-10:])):
                    return c, f"Matched by Phone '{c.phone}'"

    # 4. Normalized customer name
    cust_name = (extracted.get("customer_name") or "").strip()
    if cust_name and len(cust_name) >= 3 and cust_name.lower() not in ["unspecified customer", "customer", "unknown", "bill to", "buyer", "client"]:
        clean_name = re.sub(r'[^\w\s]', '', cust_name).lower().strip()
        for c in db.query(Customer).filter(Customer.business_id == business_id).all():
            c_clean = re.sub(r'[^\w\s]', '', c.name or '').lower().strip()
            if clean_name == c_clean:
                return c, f"Matched by exact Name '{c.name}'"
            if len(clean_name) >= 4 and len(c_clean) >= 4:
                if clean_name in c_clean or c_clean in clean_name:
                    return c, f"Matched by Name similarity '{c.name}'"

    return None, "Customer match requires review"
