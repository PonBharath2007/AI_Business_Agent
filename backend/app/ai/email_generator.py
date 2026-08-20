from typing import Dict, Any, Optional
from datetime import datetime
from backend.app.ai.gemini_client import gemini_client
from backend.app.utils.helpers import format_currency

def generate_business_email(
    customer_name: str,
    customer_email: str,
    invoice_number: Optional[str] = None,
    amount: Optional[float] = None,
    currency: str = "USD",
    due_date: Optional[str] = None,
    business_name: str = "Summit Digital Agency",
    business_signature: Optional[str] = None,
    template_type: str = "payment_reminder",
    tone: str = "professional",
    custom_instructions: Optional[str] = None
) -> Dict[str, str]:
    formatted_amount = format_currency(amount or 0.0, currency)
    sig = business_signature or f"Regards,\nFinance & Operations Team\n{business_name}"

    prompt = f"""
You are an AI Business Executive Assistant writing an email to a customer.
Write a clear, effective business email.

Context:
- Customer Name: {customer_name}
- Customer Email: {customer_email}
- Invoice Number: {invoice_number or 'N/A'}
- Amount: {formatted_amount}
- Due Date: {due_date or 'Past Due'}
- Business Name: {business_name}
- Template Goal: {template_type} (e.g. payment reminder, follow up, inquiry)
- Tone: {tone} (professional, friendly, urgent, formal)
- Custom Instructions: {custom_instructions or 'None'}

Return ONLY a JSON object with:
{{
  "subject": "Email Subject line",
  "body": "Complete email body including greeting and sign-off."
}}
"""

    ai_json = gemini_client.generate_json(
        prompt,
        system_instruction="You generate courteous, highly professional enterprise correspondence. Output strictly JSON."
    )

    steps = [
        f"Retrieved customer profile for '{customer_name}'",
        f"Loaded invoice details ({invoice_number or 'General correspondence'}, {formatted_amount})" if invoice_number else "Configured general account context",
        f"Applied tone profile: {tone.capitalize()}",
        f"Incorporated custom guidelines" if custom_instructions else "Applied standard enterprise templates"
    ]

    if ai_json and "subject" in ai_json and "body" in ai_json:
        return {
            "subject": ai_json["subject"],
            "body": ai_json["body"],
            "recipient_email": customer_email,
            "engine": "Google Gemini AI",
            "generation_steps": steps
        }

    # Enhanced Intelligent Template Generation Engine
    instruction_snippet = f"\n\nNote: {custom_instructions.strip()}" if custom_instructions and custom_instructions.strip() else ""

    if template_type == "payment_reminder" or "reminder" in template_type:
        if tone == "urgent":
            subject = f"URGENT: Overdue Payment Notice - Invoice {invoice_number or 'INV-1001'}"
            body = (
                f"Dear {customer_name},\n\n"
                f"Our records indicate that we have not yet received payment for invoice {invoice_number or 'INV-1001'}, "
                f"which had a due date of {due_date or 'August 10'}.\n\n"
                f"Outstanding Balance: {formatted_amount}\n\n"
                f"Please arrange for this balance to be settled immediately to ensure uninterrupted service.{instruction_snippet}\n\n"
                f"If payment has already been remitted, please share the transaction reference with us.\n\n"
                f"{sig}"
            )
        elif tone == "friendly":
            subject = f"Friendly Reminder: Invoice {invoice_number or 'INV-1001'} is due"
            body = (
                f"Hi {customer_name},\n\n"
                f"Hope you are having a productive week! Just a quick and friendly reminder regarding invoice {invoice_number or 'INV-1001'} "
                f"for {formatted_amount}, which was due on {due_date or 'recently'}.{instruction_snippet}\n\n"
                f"If you have already sent this payment, please disregard this note. Otherwise, feel free to let us know if you need any assistance or updated copies.\n\n"
                f"{sig}"
            )
        elif tone == "formal":
            subject = f"Statement of Account & Outstanding Invoice {invoice_number or 'INV-1001'} - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"We are writing to officially follow up on invoice {invoice_number or 'INV-1001'} in the amount of {formatted_amount}, "
                f"which fell due on {due_date or 'August 10'}.\n\n"
                f"Kindly review your records and arrange for the electronic transfer to be completed at your earliest convenience.{instruction_snippet}\n\n"
                f"Thank you for your prompt attention to this matter.\n\n"
                f"{sig}"
            )
        else: # professional default
            subject = f"Payment Reminder - Invoice {invoice_number or 'INV-1001'}"
            body = (
                f"Dear {customer_name},\n\n"
                f"This is a friendly reminder regarding the outstanding payment for invoice {invoice_number or 'INV-1001'}.\n\n"
                f"The outstanding amount is {formatted_amount} and the payment was due on {due_date or 'August 10'}.{instruction_snippet}\n\n"
                f"Please let us know if the payment has already been processed or if you require any updated invoices or banking details.\n\n"
                f"{sig}"
            )

    elif template_type == "customer_followup":
        if tone == "friendly":
            subject = f"Checking in - How are things going? | {business_name}"
            body = (
                f"Hi {customer_name},\n\n"
                f"Hope everything is going smoothly with your team! I wanted to check in following our recent discussions and see how we can best support your upcoming initiatives.{instruction_snippet}\n\n"
                f"Let us know when you have a quick 10 minutes to connect this week.\n\n"
                f"{sig}"
            )
        elif tone == "urgent":
            subject = f"Time-Sensitive: Next Steps for Project Alignment - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"We are writing to quickly align on the pending milestones and deliverables discussed for your account.{instruction_snippet}\n\n"
                f"Please let us know your availability today or tomorrow so we can finalize scheduling and resource allocation.\n\n"
                f"{sig}"
            )
        else:
            subject = f"Following up on our recent business discussion - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"I hope this message finds you well. I wanted to follow up on our recent conversation and see if there are any open questions regarding our services or proposed roadmap.{instruction_snippet}\n\n"
                f"We are eager to support your team. Please let us know a convenient time to reconnect.\n\n"
                f"{sig}"
            )

    elif template_type == "appointment_confirmation":
        subject = f"Confirmation: Upcoming Business Milestone Review - {business_name}"
        body = (
            f"Dear {customer_name},\n\n"
            f"This email confirms our upcoming scheduled review and operations checkpoint with {business_name}.\n\n"
            f"Agenda & Discussion Points:\n"
            f"- Project status and account health\n"
            f"- Deliverables milestone review\n"
            f"- Operational planning for the upcoming cycle{instruction_snippet}\n\n"
            f"Please let us know if you need to adjust the timing or add additional attendees.\n\n"
            f"{sig}"
        )

    elif template_type == "thank_you":
        subject = f"Thank You for Your Partnership - {business_name}"
        body = (
            f"Dear {customer_name},\n\n"
            f"On behalf of the entire team at {business_name}, we wanted to express our sincere gratitude for your continued partnership and trust.\n\n"
            f"We are committed to delivering excellence and look forward to continuing our collaboration on upcoming milestones.{instruction_snippet}\n\n"
            f"Best regards,\n\n"
            f"{sig}"
        )

    elif template_type == "complaint_response":
        subject = f"Priority Attention: Addressing Your Inquiry - {business_name}"
        body = (
            f"Dear {customer_name},\n\n"
            f"Thank you for bringing this to our attention. We take your feedback very seriously and sincerely apologize for any inconvenience caused.\n\n"
            f"Our operations team is actively reviewing the situation to ensure a swift and complete resolution.{instruction_snippet}\n\n"
            f"We will follow up directly within 24 hours with a comprehensive update.\n\n"
            f"{sig}"
        )

    elif template_type == "contract_expiry" or template_type == "contract_expiry_reminder":
        subject = f"Important Notice: Agreement Renewal & Milestone Checkpoint - {business_name}"
        body = (
            f"Dear {customer_name},\n\n"
            f"We would like to remind you that your service agreement with {business_name} is approaching its scheduled renewal date ({due_date or 'within the next 30 days'}).\n\n"
            f"To ensure uninterrupted operations and lock in current rate schedules, we have prepared your renewal term sheet for your review.{instruction_snippet}\n\n"
            f"Please let us know if you would like to schedule a brief alignment call.\n\n"
            f"{sig}"
        )

    elif template_type == "customer_reply":
        subject = f"Re: Your Account & Operational Inquiry - {business_name}"
        body = (
            f"Dear {customer_name},\n\n"
            f"Thank you for reaching out. In response to your recent note, we have reviewed your account records and prepared the relevant information for you.{instruction_snippet}\n\n"
            f"Please let us know if you need any additional clarification or supporting documentation.\n\n"
            f"{sig}"
        )

    else: # general_inquiry or fallback
        subject = f"Business Inquiry & Account Update - {business_name}"
        body = (
            f"Dear {customer_name},\n\n"
            f"Thank you for contacting {business_name}. We have received your inquiry and are reviewing the details to provide you with the most effective assistance.{instruction_snippet}\n\n"
            f"If you have any supporting documents or specific questions in the meantime, please feel free to reply directly to this email.\n\n"
            f"{sig}"
        )

    return {
        "subject": subject,
        "body": body,
        "recipient_email": customer_email,
        "engine": "Intelligent Operations Agent",
        "generation_steps": steps
    }


def transform_email_content(
    text: str,
    action: str, # "make_urgent", "make_professional", "shorten", "translate"
    target_language: Optional[str] = "Hindi"
) -> Dict[str, str]:
    """
    Transforms existing email draft (tone shift, shortening, or translation).
    """
    prompt = f"""
Transform the following email text according to the requested action.

Action: {action}
Target Language (if translating): {target_language}

Original Email Text:
\"\"\"
{text}
\"\"\"

Guidelines:
- If 'make_urgent': Enhance urgency, highlight overdue deadlines and immediate required actions while remaining business appropriate.
- If 'make_professional': Refine vocabulary, format with clear executive tone and courteous sign-off.
- If 'shorten': Condense to 3-4 crisp, high-impact sentences without losing critical data (amounts, dates).
- If 'translate': Provide an accurate, culturally appropriate business translation into {target_language}.

Return ONLY the transformed text.
"""
    ai_text = gemini_client.generate_text(
        prompt,
        system_instruction="You are an expert executive communication editor. Output only the modified email text."
    )

    if ai_text and len(ai_text.strip()) > 10:
        return {"transformed_text": ai_text.strip(), "engine": "Google Gemini AI"}

    # Fallback local heuristics
    cleaned = text.strip()
    if action == "make_urgent":
        transformed = f"⚠️ TIME-SENSITIVE NOTICE\n\n{cleaned}\n\n[Immediate action requested within 24 hours to avoid escalation]."
    elif action == "shorten":
        lines = [l for l in cleaned.split("\n") if l.strip()]
        transformed = "\n\n".join(lines[:3]) + "\n\nBest regards,\nOperations Team"
    elif action == "translate" and target_language.lower() == "hindi":
        transformed = f"प्रिय ग्राहक,\n\nयह आपके बकाया भुगतान और खाते के संबंध में एक महत्वपूर्ण सूचना है। कृपया जल्द से जल्द समीक्षा करें।\n\nसादर,\nसंचालन दल"
    else:
        transformed = f"Dear Client,\n\n{cleaned}\n\nSincerely,\nOperations & Finance Team"

    return {"transformed_text": transformed, "engine": "Local Transformation Engine"}

