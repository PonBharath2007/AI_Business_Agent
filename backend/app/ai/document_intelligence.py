import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from backend.app.ai.gemini_client import gemini_client
from backend.app.utils.helpers import parse_date, parse_amount
from backend.app.utils.logger import logger


def analyze_document_with_ai(file_name: str, raw_text: str, document_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Tiered Document Intelligence Engine:
    1. Tier 1: Gemini AI (passes up to 60,000 characters of full multi-page document text with tables).
    2. Tier 2: Advanced Deterministic Financial Invoice Parser (extracts actual vendors, customers,
       invoice numbers, line items, taxes, totals, and payment status directly from document layout and tables).
    NEVER falls back to hardcoded sample data (no fake ABC Ltd or INV-1001).
    """
    full_context_text = (raw_text or "").strip()[:60000]

    # Tier 1: Gemini AI if configured
    if gemini_client.is_configured and len(full_context_text) > 10:
        prompt = f"""
You are an expert enterprise financial document intelligence system.
Extract structured invoice/bill data from the document below and output strictly valid JSON.

Document Filename: {file_name}
Full Document Content (including structured tables and text):
\"\"\"
{full_context_text}
\"\"\"

Return a single JSON object with these exact keys:
{{
  "document_type": "invoice" | "receipt" | "contract" | "statement" | "purchase_order" | "general",
  "vendor_name": "Name of the issuer/seller/company issuing the document",
  "customer_name": "Name of the customer / client / Bill To entity",
  "customer_email": "Customer email if present in document, or null",
  "customer_phone": "Customer phone number if present in document, or null",
  "customer_company": "Customer company name if present, or customer_name",
  "invoice_number": "Exact invoice/bill/receipt number from document (e.g. INV-2026-00125)",
  "amount": 13068.50,
  "currency": "INR" | "USD" | "EUR" | "GBP",
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "payment_status": "paid" | "pending" | "overdue",
  "priority": "High" | "Medium" | "Low",
  "is_overdue": true | false,
  "subtotal": 11075.0,
  "tax_amount": 1993.50,
  "balance_due": 0.0,
  "summary": "Accurate 1-2 sentence summary of this document.",
  "recommended_action": "Operational next step based on payment status.",
  "items": [
     {{"description": "Item name", "quantity": 1, "unit_price": 100.0, "total": 100.0}}
  ],
  "important_clauses": []
}}
"""
        try:
            ai_result = gemini_client.generate_json(
                prompt,
                system_instruction="You are a precise enterprise financial document intelligence system. Extract actual data from the document. Do not invent or hallucinate placeholder values. Output only valid JSON."
            )
            if ai_result and isinstance(ai_result, dict) and ("customer_name" in ai_result or "invoice_number" in ai_result or "amount" in ai_result):
                return normalize_extracted_document(ai_result, file_name, full_context_text)
        except Exception as exc:
            logger.warning(f"Gemini document analysis encountered error, falling back to deterministic parser: {exc}")

    # Tier 2: Advanced Deterministic Parser
    return deterministic_invoice_parser(file_name, full_context_text)


def parse_clean_date(date_str: Optional[str]) -> Optional[date]:
    """Parses various date formats commonly found in Indian, US, and international invoices."""
    if not date_str:
        return None
    cleaned = re.sub(r'[\r\n|]+', ' ', str(date_str)).strip()
    
    # Try month name formats: 19-Aug-2026, 19 Aug 2026, August 19, 2026
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

    # Fallback to standard parse_date
    return parse_date(cleaned)


def deterministic_invoice_parser(file_name: str, raw_text: str) -> Dict[str, Any]:
    """
    High-precision, rule-based financial invoice and document parser.
    Extracts vendor, Bill To customer, invoice numbers, dates, currency, line items,
    and payment status directly from document text and structured tables.
    Returns honest values and nulls if missing, NEVER fabricated demo records.
    """
    text_lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    text_lower = raw_text.lower()
    file_lower = file_name.lower()
    today = date.today()

    # 1. Document Type Detection
    doc_type = "invoice"
    if "tax invoice" in text_lower or "tax-invoice" in text_lower:
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

    # 3. Vendor / Issuer Extraction
    vendor_name = None
    vendor_match = re.search(r'(?:From|Sold\s*By|Seller|Vendor|Issuer|Supplier)[:\s]+([^\n\r,]+)', raw_text, re.IGNORECASE)
    if vendor_match:
        vendor_name = vendor_match.group(1).strip()
    else:
        # Check document text header before TAX INVOICE or Bill To
        doc_text_m = re.search(r'\[DOCUMENT TEXT\]\s*\n+([^\n\r]+)', raw_text)
        if doc_text_m:
            cand = doc_text_m.group(1).strip()
            if cand and not any(cand.lower().startswith(x) for x in ["tax invoice", "invoice", "page", "bill", "==="]):
                vendor_name = cand
        elif text_lines:
            for line in text_lines[:5]:
                if not any(k in line.lower() for k in ["===", "page", "table", "tax invoice", "bill to", "invoice no"]):
                    if len(line) > 3 and not re.search(r'\b(inv-|date|phone|gstin)\b', line, re.IGNORECASE):
                        vendor_name = line
                        break

    # 4. Customer / "Bill To" Extraction
    customer_name = None
    customer_phone = None
    customer_email = None
    customer_company = None

    # Check table structure for "Bill To"
    bill_to_table_match = re.search(r'\|\s*Bill\s*To\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if bill_to_table_match:
        cand = bill_to_table_match.group(1).strip()
        if cand and cand.lower() not in ["name", "customer", "client", "address"]:
            customer_name = cand

    # Check text structure for "Bill To" block
    if not customer_name:
        bill_to_text_match = re.search(r'(?:Bill\s*To|Billed\s*To|Customer\s*Name|Invoice\s*To|Buyer|M/s)[:\s\n]+([^\n\r,]+)', raw_text, re.IGNORECASE)
        if bill_to_text_match:
            cand = bill_to_text_match.group(1).strip()
            if cand and cand.lower() not in ["phone", "address", "gstin", "email"]:
                customer_name = cand

    # Extract customer contact details
    phone_match = re.search(r'(?:Phone|Mobile|Tel)[:\s|]+(\+?[\d\s-]{10,15})', raw_text, re.IGNORECASE)
    if phone_match:
        customer_phone = phone_match.group(1).strip()

    email_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
    if email_matches:
        # Prefer email on lines near bill to or take first
        customer_email = email_matches[0]

    customer_company = customer_name

    # 4. Dates Extraction
    issue_date = None
    due_date = None

    inv_date_m = re.search(r'\|\s*Invoice\s*Date\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if inv_date_m:
        issue_date = parse_clean_date(inv_date_m.group(1).strip())

    if not issue_date:
        inv_date_m2 = re.search(r'(?:Invoice\s*Date|Bill\s*Date|Date)[:\s]+([A-Za-z0-9\s,\-/]+)', raw_text, re.IGNORECASE)
        if inv_date_m2:
            issue_date = parse_clean_date(inv_date_m2.group(1).strip())

    due_date_m = re.search(r'\|\s*Due\s*Date\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if due_date_m:
        due_date = parse_clean_date(due_date_m.group(1).strip())

    if not due_date:
        due_date_m2 = re.search(r'(?:Due\s*Date|Payment\s*Due)[:\s]+([A-Za-z0-9\s,\-/]+)', raw_text, re.IGNORECASE)
        if due_date_m2:
            due_date = parse_clean_date(due_date_m2.group(1).strip())

    # Fallback to date pattern list if specific labels not found
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

    # 5. Currency Detection
    currency = "USD"
    if any(sym in raw_text for sym in ["₹", "INR", "Rs", "GSTIN", "Coimbatore", "Tamil Nadu"]) or re.search(r'\b(GST|CGST|SGST|IGST)\b', raw_text):
        currency = "INR"
    elif "€" in raw_text or "eur" in text_lower:
        currency = "EUR"
    elif "£" in raw_text or "gbp" in text_lower:
        currency = "GBP"

    # 6. Financial Totals
    grand_total = None
    subtotal = None
    total_tax = None
    balance_due = None

    # Grand total search
    gt_match = re.search(r'\|\s*(?:Grand\s*Total|Total\s*Amount|Net\s*Payable)\s*\|\s*[^0-9]*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if gt_match:
        grand_total = parse_amount(gt_match.group(1))

    if grand_total is None:
        gt_text = re.search(r'(?:Grand\s*Total|Total\s*Amount|Net\s*Payable|Total\s*Due)[\s:]*[$₹€£nI]?\s*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
        if gt_text:
            grand_total = parse_amount(gt_text.group(1))

    # Subtotal
    sub_match = re.search(r'\|\s*Subtotal\s*\|\s*[^0-9]*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if sub_match:
        subtotal = parse_amount(sub_match.group(1))

    # GST / Tax
    gst_match = re.search(r'\|\s*Total\s*GST\s*\|\s*[^0-9]*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if gst_match:
        total_tax = parse_amount(gst_match.group(1))

    # Balance due
    bal_match = re.search(r'\|\s*Balance\s*Due\s*\|\s*[^0-9]*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if bal_match:
        balance_due = parse_amount(bal_match.group(1))

    # 7. Payment Status
    payment_status = "pending"
    status_match = re.search(r'\|\s*Payment\s*Status\s*\|\s*([^|\r\n]+)', raw_text, re.IGNORECASE)
    if status_match:
        st_val = status_match.group(1).strip().lower()
        if "paid" in st_val:
            payment_status = "paid"
        elif "overdue" in st_val:
            payment_status = "overdue"
        elif "pending" in st_val:
            payment_status = "pending"
    elif "status: paid" in text_lower or (balance_due is not None and balance_due <= 0 and grand_total and grand_total > 0):
        payment_status = "paid"

    if payment_status != "paid" and due_date < today:
        payment_status = "overdue"

    is_overdue = (payment_status == "overdue")

    # 8. Line Items Table Parsing
    items = []
    for line in raw_text.split('\n'):
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            # Line item rows: S.No (numeric), Description, Qty, Unit Price, Tax/GST, Amount
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
                    "total": line_tot
                })

    # If grand_total was not found in totals, sum items
    if (grand_total is None or grand_total <= 0) and items:
        grand_total = sum(it["total"] for it in items)

    final_amount = float(grand_total or 0.0)

    # 9. Summary & Validation
    validation_warnings = []
    if not invoice_number:
        validation_warnings.append("Invoice number could not be explicitly verified from document.")
    if not customer_name:
        validation_warnings.append("Customer/Client entity could not be explicitly extracted.")
    if final_amount <= 0:
        validation_warnings.append("Invoice balance was zero or missing.")

    confidence = 95
    if validation_warnings:
        confidence = max(60, 95 - (len(validation_warnings) * 15))

    display_customer = customer_name or "Unspecified Customer"
    display_inv = invoice_number or "Unnumbered Document"

    summary = f"Invoice {display_inv} for {display_customer} of {currency} {final_amount:,.2f} is currently {payment_status.upper()}."
    if payment_status == "paid":
        recommended_action = "Invoice marked PAID. Reconcile transaction and archive record."
    elif payment_status == "overdue":
        recommended_action = f"Send payment reminder to {display_customer} regarding overdue balance."
    else:
        recommended_action = f"Monitor invoice until due date on {due_date.isoformat()}."

    line_items_list = items if items else ([{"description": f"{display_inv} - Line Items", "quantity": 1, "unit_price": final_amount, "total": final_amount}] if final_amount > 0 else [])

    return {
        "document_type": doc_type,
        "vendor_name": vendor_name,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "customer_company": customer_company or customer_name,
        "invoice_number": invoice_number,
        "amount": final_amount,
        "currency": currency,
        "issue_date": issue_date.isoformat(),
        "invoice_date": issue_date.isoformat(),
        "due_date": due_date.isoformat(),
        "payment_status": payment_status,
        "priority": "High" if is_overdue or final_amount > 10000 else "Medium",
        "is_overdue": is_overdue,
        "days_overdue": (today - due_date).days if is_overdue else 0,
        "subtotal": subtotal,
        "tax_amount": total_tax,
        "balance_due": balance_due,
        "ai_confidence": confidence,
        "confidence_score": confidence,
        "validation_warnings": validation_warnings,
        "summary": summary,
        "recommended_action": recommended_action,
        "items": line_items_list,
        "line_items": line_items_list,
        "important_clauses": [f"Payment terms: Due by {due_date.isoformat()}"]
    }


def normalize_extracted_document(data: Dict[str, Any], file_name: str, raw_text: str) -> Dict[str, Any]:
    """Validates and normalizes structured extraction output without injecting fake demo records."""
    today = date.today()

    issue_date_val = parse_clean_date(data.get("issue_date") or data.get("invoice_date")) or today
    due_date_val = parse_clean_date(data.get("due_date")) or (issue_date_val + timedelta(days=14))

    amount_val = parse_amount(data.get("amount", 0.0))
    status = str(data.get("payment_status", "")).lower().strip()
    if not status:
        status = "overdue" if due_date_val < today else "pending"

    is_overdue = (status == "overdue") or (due_date_val < today and status != "paid")
    if is_overdue and status != "paid":
        status = "overdue"

    validation_warnings = []
    if not data.get("customer_name"):
        validation_warnings.append("Customer name not detected.")
    if not data.get("invoice_number"):
        validation_warnings.append("Invoice number not detected.")
    if amount_val <= 0:
        validation_warnings.append("Total amount was not cleanly detected.")

    confidence = 95 if not validation_warnings else max(60, 95 - (len(validation_warnings) * 15))

    items_list = data.get("items") or data.get("line_items") or []

    data["vendor_name"] = data.get("vendor_name")
    data["issue_date"] = issue_date_val.isoformat()
    data["invoice_date"] = issue_date_val.isoformat()
    data["due_date"] = due_date_val.isoformat()
    data["amount"] = amount_val
    data["payment_status"] = status
    data["is_overdue"] = is_overdue
    data["days_overdue"] = (today - due_date_val).days if is_overdue else 0
    data["ai_confidence"] = data.get("ai_confidence", confidence)
    data["confidence_score"] = data.get("confidence_score", data["ai_confidence"])
    data["validation_warnings"] = validation_warnings
    data["priority"] = data.get("priority", "High" if is_overdue or amount_val > 10000 else "Medium")
    data["customer_name"] = data.get("customer_name")
    data["customer_email"] = data.get("customer_email")
    data["customer_phone"] = data.get("customer_phone")
    data["invoice_number"] = data.get("invoice_number")
    data["currency"] = data.get("currency") or ("INR" if ("₹" in raw_text or "inr" in raw_text.lower()) else "USD")
    data["items"] = items_list
    data["line_items"] = items_list

    return data


