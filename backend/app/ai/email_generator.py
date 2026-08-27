from typing import Dict, Any, Optional
from datetime import datetime
from backend.app.ai.gemini_client import gemini_client
from backend.app.utils.helpers import format_currency

def generate_customer_communication(
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    invoice_number: Optional[str] = None,
    amount: Optional[float] = None,
    currency: str = "USD",
    due_date: Optional[str] = None,
    business_name: str = "Summit Digital Agency",
    business_signature: Optional[str] = None,
    template_type: str = "payment_reminder",
    tone: str = "professional",
    language: str = "en",  # "en", "ta", "en_ta"
    channel: str = "email",  # "email", "sms"
    custom_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates professional customer communication in English, Tamil, or Bilingual (English + Tamil)
    for Email or SMS channels.
    """
    formatted_amount = format_currency(amount or 0.0, currency)
    sig_en = business_signature or f"Regards,\nFinance & Operations Team\n{business_name}"
    sig_ta = f"நன்றி,\nநிதி மற்றும் செயல்பாட்டுக் குழு\n{business_name}"
    sig_bilingual = f"Thank you / நன்றி\n{business_name}"

    lang_desc = {
        "en": "English only",
        "ta": "Tamil (தமிழ்) only",
        "en_ta": "Bilingual (BOTH English and Tamil in the SAME message - English first, followed by Tamil translation below)"
    }.get(language, "English only")

    channel_guideline = (
        "This is an SMS text message. Keep it concise, punchy, and under 300 characters while including all critical details (amount, due date, invoice #)."
        if channel == "sms"
        else "This is a formal business email. Include an appropriate subject line and well-formatted body with greeting and sign-off."
    )

    prompt = f"""
You are an AI Business Executive Assistant writing customer communication.

Channel: {channel.upper()}
Language Requirement: {lang_desc}
Context:
- Customer Name: {customer_name}
- Customer Email: {customer_email or 'N/A'}
- Customer Phone: {customer_phone or 'N/A'}
- Invoice Number: {invoice_number or 'N/A'}
- Amount: {formatted_amount}
- Due Date: {due_date or 'Past Due'}
- Business Name: {business_name}
- Template Goal: {template_type} (e.g. payment reminder, follow up, appointment confirmation, general inquiry)
- Tone: {tone} (professional, friendly, urgent, formal)
- Custom Instructions: {custom_instructions or 'None'}

Formatting Rules:
1. {channel_guideline}
2. Language rules:
   - If language is 'English' ('en'): Produce only English text.
   - If language is 'Tamil' ('ta'): Produce only grammatically correct, formal Tamil (தமிழ்) text with proper Tamil Unicode characters.
   - If language is 'English + Tamil' ('en_ta'): Produce BOTH the English text and the Tamil text within the SAME message. Place the English message first, then a divider or blank line, then the complete Tamil translation.
3. Do NOT include meta-talk, notes, or explanations outside the JSON.

Return strictly a JSON object with:
{{
  "subject": "Subject line (in requested language)",
  "body": "Complete message body (in requested language / bilingual)"
}}
"""

    ai_json = gemini_client.generate_json(
        prompt,
        system_instruction="You generate courteous, highly professional enterprise customer communications in English, Tamil, or Bilingual. Output strictly JSON."
    )

    steps = [
        f"Retrieved profile for '{customer_name}'",
        f"Configured language mode: {lang_desc}",
        f"Loaded invoice context ({invoice_number or 'General correspondence'}, {formatted_amount})" if invoice_number else "Applied general business context",
        f"Applied tone profile: {tone.capitalize()}",
        f"Channel: {channel.upper()}"
    ]

    if ai_json and "body" in ai_json:
        subj = ai_json.get("subject", "")
        if channel == "sms" and not subj:
            subj = f"SMS: {invoice_number or 'Notice'}"
        return {
            "subject": subj,
            "body": ai_json["body"].strip(),
            "recipient_email": customer_email or "",
            "recipient_phone": customer_phone or "",
            "language": language,
            "channel": channel,
            "engine": "Google Gemini AI",
            "generation_steps": steps
        }

    # =========================================================================
    # HIGH-QUALITY LOCAL MULTILINGUAL TEMPLATES (TAMIL, ENGLISH, BILINGUAL)
    # =========================================================================
    inv_str = invoice_number or "INV-1001"
    due_str = due_date or "recent date"
    instruction_snippet = f"\n\nNote: {custom_instructions.strip()}" if custom_instructions and custom_instructions.strip() else ""

    # 1. SMS CHANNEL TEMPLATES
    if channel == "sms":
        if "reminder" in template_type or template_type == "payment_reminder":
            if language == "ta":
                subj = f"விலைப்பட்டியல் {inv_str} நினைவூட்டல்"
                body = (
                    f"வணக்கம் {customer_name},\n"
                    f"உங்கள் {formatted_amount} மதிப்பிலான விலைப்பட்டியல் ({inv_str}) பணம் செலுத்த வேண்டிய தேதி ({due_str}) முடிவடைந்துள்ளது. "
                    f"தயவுசெய்து விரைவில் பணம் செலுத்தவும்.\n"
                    f"- {business_name}"
                )
            elif language == "en_ta":
                subj = f"Payment Reminder / பணம் செலுத்தும் நினைவூட்டல் - {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"Your invoice {inv_str} of {formatted_amount} is overdue (Due: {due_str}). Please complete the payment.\n\n"
                    f"வணக்கம் {customer_name},\n"
                    f"உங்கள் {formatted_amount} விலைப்பட்டியலுக்கான ({inv_str}) பணம் செலுத்த வேண்டிய தேதி முடிவடைந்துள்ளது. தயவுசெய்து விரைவில் செலுத்தவும்.\n"
                    f"- {business_name}"
                )
            else:  # English default
                subj = f"Payment Reminder: Invoice {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"Your invoice {inv_str} for {formatted_amount} is overdue (Due: {due_str}). "
                    f"Please arrange payment at your earliest convenience.\n"
                    f"- {business_name}"
                )
        elif template_type == "appointment_confirmation":
            if language == "ta":
                subj = "சந்திப்பு உறுதிப்படுத்தல்"
                body = f"வணக்கம் {customer_name}, {business_name} உடனான உங்கள் வணிகச் சந்திப்பு உறுதி செய்யப்பட்டுள்ளது. நன்றி."
            elif language == "en_ta":
                subj = "Meeting Confirmation / சந்திப்பு உறுதிப்படுத்தல்"
                body = (
                    f"Dear {customer_name}, your meeting with {business_name} is confirmed.\n\n"
                    f"வணக்கம் {customer_name}, {business_name} உடனான உங்கள் சந்திப்பு உறுதி செய்யப்பட்டுள்ளது."
                )
            else:
                subj = "Meeting Confirmation"
                body = f"Dear {customer_name}, your business checkpoint with {business_name} is confirmed. Thank you."
        else:  # General SMS
            if language == "ta":
                subj = f"{business_name} அறிவிப்பு"
                body = f"வணக்கம் {customer_name}, {business_name} இலிருந்து ஒரு முக்கிய வணிகத் தகவல். மேலும் தகவலுக்கு எங்களைத் தொடர்பு கொள்ளவும்."
            elif language == "en_ta":
                subj = f"Update / அறிவிப்பு - {business_name}"
                body = (
                    f"Dear {customer_name}, important business update from {business_name}. Please contact us if needed.\n\n"
                    f"வணக்கம் {customer_name}, {business_name} இலிருந்து ஒரு முக்கிய வணிகத் தகவல்."
                )
            else:
                subj = f"Notice from {business_name}"
                body = f"Dear {customer_name}, an important update regarding your account with {business_name}. Please reach out if you have questions."

        return {
            "subject": subj,
            "body": body,
            "recipient_email": customer_email or "",
            "recipient_phone": customer_phone or "",
            "language": language,
            "channel": "sms",
            "engine": "Intelligent Operations Agent (Local)",
            "generation_steps": steps
        }

    # 2. EMAIL CHANNEL TEMPLATES
    if "reminder" in template_type or template_type == "payment_reminder":
        if language == "ta":
            if tone == "urgent":
                subj = f"முக்கியமானது: நிலுவைத் தொகை அறிவிப்பு - விலைப்பட்டியல் {inv_str}"
                body = (
                    f"அன்புள்ள {customer_name},\n\n"
                    f"எங்கள் கணக்கு பதிவுகளின்படி, {due_str} அன்று செலுத்த வேண்டிய விலைப்பட்டியல் {inv_str}-க்கான தொகை இன்னும் பெறப்படவில்லை.\n\n"
                    f"நிலுவைத் தொகை: {formatted_amount}\n\n"
                    f"சேவைகள் தடையின்றி தொடர, தயவுசெய்து இந்தத் தொகையை உடனடியாகச் செலுத்துமாறு கேட்டுக்கொள்கிறோம்.{instruction_snippet}\n\n"
                    f"ஏற்கனவே பணம் செலுத்தியிருந்தால், தயவுசெய்து பரிவர்த்தனை விவரங்களைப் பகிரவும்.\n\n"
                    f"{sig_ta}"
                )
            elif tone == "friendly":
                subj = f"நட்பான நினைவூட்டல்: விலைப்பட்டியல் {inv_str}"
                body = (
                    f"வணக்கம் {customer_name},\n\n"
                    f"உங்களுக்கு ஒரு நட்பான நினைவூட்டல். உங்கள் {formatted_amount} மதிப்பிலான விலைப்பட்டியல் {inv_str}-க்கான பணம் செலுத்த வேண்டிய தேதி ({due_str}) முடிவடைந்துள்ளது.{instruction_snippet}\n\n"
                    f"ஏற்கனவே பணம் செலுத்தியிருந்தால் இந்த செய்தியைப் புறக்கணிக்கவும். ஏதேனும் உதவி தேவைப்பட்டால் எங்களுக்குத் தெரிவிக்கவும்.\n\n"
                    f"{sig_ta}"
                )
            else:  # professional default
                subj = f"பணம் செலுத்தும் நினைவூட்டல் - விலைப்பட்டியல் {inv_str}"
                body = (
                    f"வணக்கம் {customer_name},\n\n"
                    f"உங்கள் விலைப்பட்டியல் {inv_str}-க்கான நிலுவைத் தொகை பற்றிய நினைவூட்டல் இது.\n\n"
                    f"நிலுவைத் தொகை {formatted_amount} மற்றும் செலுத்த வேண்டிய தேதி {due_str} ஆகும்.{instruction_snippet}\n\n"
                    f"தயவுசெய்து விரைவில் பணப்பரிவர்த்தனையை நிறைவு செய்யுமாறு கேட்டுக்கொள்கிறோம்.\n\n"
                    f"{sig_ta}"
                )
        elif language == "en_ta":
            # Bilingual (English + Tamil in SAME EMAIL)
            subj = f"Payment Reminder / பணம் செலுத்தும் நினைவூட்டல் - Invoice {inv_str}"
            body = (
                f"Dear {customer_name},\n\n"
                f"This is a reminder regarding the outstanding payment for invoice {inv_str}.\n"
                f"Outstanding Balance: {formatted_amount}\n"
                f"Due Date: {due_str}\n\n"
                f"Please arrange for this payment to be completed at your earliest convenience.{instruction_snippet}\n\n"
                f"--------------------------------------------------\n\n"
                f"வணக்கம் {customer_name},\n\n"
                f"உங்கள் விலைப்பட்டியல் {inv_str}-க்கான நிலுவைத் தொகை பற்றிய நினைவூட்டல் இது.\n"
                f"நிலுவைத் தொகை: {formatted_amount}\n"
                f"செலுத்த வேண்டிய தேதி: {due_str}\n\n"
                f"தயவுசெய்து இந்தத் தொகையை விரைவில் செலுத்துமாறு கேட்டுக்கொள்கிறோம்.\n\n"
                f"{sig_bilingual}"
            )
        else:  # English
            if tone == "urgent":
                subj = f"URGENT: Overdue Payment Notice - Invoice {inv_str}"
                body = (
                    f"Dear {customer_name},\n\n"
                    f"Our records indicate that we have not yet received payment for invoice {inv_str}, "
                    f"which had a due date of {due_str}.\n\n"
                    f"Outstanding Balance: {formatted_amount}\n\n"
                    f"Please arrange for this balance to be settled immediately to ensure uninterrupted service.{instruction_snippet}\n\n"
                    f"If payment has already been remitted, please share the transaction reference with us.\n\n"
                    f"{sig_en}"
                )
            elif tone == "friendly":
                subj = f"Friendly Reminder: Invoice {inv_str} is due"
                body = (
                    f"Hi {customer_name},\n\n"
                    f"Hope you are having a productive week! Just a quick and friendly reminder regarding invoice {inv_str} "
                    f"for {formatted_amount}, which was due on {due_str}.{instruction_snippet}\n\n"
                    f"If you have already sent this payment, please disregard this note. Otherwise, feel free to let us know if you need any assistance.\n\n"
                    f"{sig_en}"
                )
            else:  # professional default
                subj = f"Payment Reminder - Invoice {inv_str}"
                body = (
                    f"Dear {customer_name},\n\n"
                    f"This is a friendly reminder regarding the outstanding payment for invoice {inv_str}.\n\n"
                    f"The outstanding amount is {formatted_amount} and the payment was due on {due_str}.{instruction_snippet}\n\n"
                    f"Please let us know if the payment has already been processed or if you require any updated invoices or banking details.\n\n"
                    f"{sig_en}"
                )

    elif template_type == "customer_followup":
        if language == "ta":
            subj = f"வணிகத் தொடர்பு மற்றும் பின்தொடர்தல் - {business_name}"
            body = (
                f"வணக்கம் {customer_name},\n\n"
                f"நலமாக இருக்கிறீர்கள் என நம்புகிறோம். எங்களது சமீபத்திய உரையாடலைத் தொடர்ந்து, உங்கள் திட்டங்களுக்கு நாங்கள் எவ்வாறு உதவ முடியும் என்பதை அறிய விரும்புகிறோம்.{instruction_snippet}\n\n"
                f"உங்களுக்கு வசதியான நேரத்தில் எங்களைத் தொடர்பு கொள்ளவும்.\n\n"
                f"{sig_ta}"
            )
        elif language == "en_ta":
            subj = f"Following up / பின்தொடர்தல் - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"I hope this message finds you well. I wanted to follow up on our recent conversation and see how we can best support your initiatives.{instruction_snippet}\n\n"
                f"--------------------------------------------------\n\n"
                f"வணக்கம் {customer_name},\n\n"
                f"எங்களது சமீபத்திய உரையாடலைத் தொடர்ந்து, உங்கள் திட்டங்களுக்கு நாங்கள் எவ்வாறு உதவ முடியும் என்பதை அறிய தொடர்பு கொள்கிறோம்.\n\n"
                f"{sig_bilingual}"
            )
        else:
            subj = f"Following up on our recent business discussion - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"I hope this message finds you well. I wanted to follow up on our recent conversation and see if there are any open questions regarding our services.{instruction_snippet}\n\n"
                f"We are eager to support your team. Please let us know a convenient time to reconnect.\n\n"
                f"{sig_en}"
            )

    elif template_type == "appointment_confirmation":
        if language == "ta":
            subj = f"வணிகச் சந்திப்பு உறுதிப்படுத்தல் - {business_name}"
            body = (
                f"வணக்கம் {customer_name},\n\n"
                f"{business_name} உடனான உங்கள் வரவிருக்கும் வணிகச் சந்திப்பு உறுதி செய்யப்பட்டுள்ளது என்பதைத் தெரிவித்துக் கொள்கிறோம்.{instruction_snippet}\n\n"
                f"நன்றி,\n{sig_ta}"
            )
        elif language == "en_ta":
            subj = f"Meeting Confirmation / சந்திப்பு உறுதிப்படுத்தல் - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"This email confirms our upcoming scheduled review checkpoint with {business_name}.{instruction_snippet}\n\n"
                f"--------------------------------------------------\n\n"
                f"வணக்கம் {customer_name},\n\n"
                f"{business_name} உடனான உங்கள் வணிகச் சந்திப்பு உறுதி செய்யப்பட்டுள்ளது என்பதைத் தெரிவித்துக் கொள்கிறோம்.\n\n"
                f"{sig_bilingual}"
            )
        else:
            subj = f"Confirmation: Upcoming Business Milestone Review - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"This email confirms our upcoming scheduled review and operations checkpoint with {business_name}.{instruction_snippet}\n\n"
                f"Please let us know if you need to adjust the timing or add additional attendees.\n\n"
                f"{sig_en}"
            )

    else:  # General
        if language == "ta":
            subj = f"வணிகத் தகவல் மற்றும் கணக்கு புதுப்பிப்பு - {business_name}"
            body = (
                f"வணக்கம் {customer_name},\n\n"
                f"{business_name} ஐ தொடர்பு கொண்டதற்கு நன்றி. உங்கள் கணக்கு தொடர்பான விவரங்களை மதிப்பாய்வு செய்து வருகிறோம்.{instruction_snippet}\n\n"
                f"{sig_ta}"
            )
        elif language == "en_ta":
            subj = f"Account Update / கணக்கு புதுப்பிப்பு - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"Thank you for reaching out to {business_name}. We are reviewing your account details and will assist you shortly.{instruction_snippet}\n\n"
                f"--------------------------------------------------\n\n"
                f"வணக்கம் {customer_name},\n\n"
                f"{business_name} ஐ தொடர்பு கொண்டதற்கு நன்றி. உங்கள் விவரங்களை மதிப்பாய்வு செய்து வருகிறோம்.\n\n"
                f"{sig_bilingual}"
            )
        else:
            subj = f"Business Inquiry & Account Update - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"Thank you for contacting {business_name}. We have received your inquiry and are reviewing the details to provide you with the most effective assistance.{instruction_snippet}\n\n"
                f"{sig_en}"
            )

    return {
        "subject": subj,
        "body": body,
        "recipient_email": customer_email or "",
        "recipient_phone": customer_phone or "",
        "language": language,
        "channel": channel,
        "engine": "Intelligent Operations Agent (Local)",
        "generation_steps": steps
    }


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
    custom_instructions: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for generate_customer_communication.
    """
    return generate_customer_communication(
        customer_name=customer_name,
        customer_email=customer_email,
        invoice_number=invoice_number,
        amount=amount,
        currency=currency,
        due_date=due_date,
        business_name=business_name,
        business_signature=business_signature,
        template_type=template_type,
        tone=tone,
        language=language,
        channel="email",
        custom_instructions=custom_instructions
    )


def transform_email_content(
    text: str,
    action: str,  # "make_urgent", "make_professional", "shorten", "translate"
    target_language: Optional[str] = "Tamil"
) -> Dict[str, str]:
    """
    Transforms existing communication draft (tone shift, shortening, or translation into Tamil/English).
    """
    prompt = f"""
Transform the following message text according to the requested action.

Action: {action}
Target Language (if translating): {target_language}

Original Text:
\"\"\"
{text}
\"\"\"

Guidelines:
- If 'make_urgent': Enhance urgency, highlight overdue deadlines and immediate required actions while remaining business appropriate.
- If 'make_professional': Refine vocabulary, format with clear executive tone and courteous sign-off.
- If 'shorten': Condense to 2-3 crisp sentences without losing critical data (amounts, invoice #, dates).
- If 'translate': Provide an accurate, culturally appropriate business translation into {target_language} using authentic Unicode script (e.g. தமிழ் if Tamil).

Return ONLY the transformed text without commentary.
"""
    ai_text = gemini_client.generate_text(
        prompt,
        system_instruction="You are an expert executive business communication editor and translator. Output only the modified text."
    )

    if ai_text and len(ai_text.strip()) > 5:
        return {"transformed_text": ai_text.strip(), "engine": "Google Gemini AI"}

    # Fallback local heuristics
    cleaned = text.strip()
    if action == "make_urgent":
        transformed = f"⚠️ TIME-SENSITIVE NOTICE\n\n{cleaned}\n\n[Immediate settlement requested within 24 hours]."
    elif action == "shorten":
        lines = [l for l in cleaned.split("\n") if l.strip()]
        transformed = "\n\n".join(lines[:2]) + "\n\nBest regards,\nOperations Team"
    elif action == "translate" and "tamil" in (target_language or "").lower():
        transformed = f"வணக்கம்,\n\nஇது உங்கள் நிலுவைத் தொகை மற்றும் கணக்கு தொடர்பான முக்கியமான தகவல். தயவுசெய்து விரைவில் பரிசீலிக்கவும்.\n\nநன்றி,\nசெயல்பாட்டுக் குழு"
    else:
        transformed = f"Dear Client,\n\n{cleaned}\n\nSincerely,\nOperations & Finance Team"

    return {"transformed_text": transformed, "engine": "Local Transformation Engine"}
