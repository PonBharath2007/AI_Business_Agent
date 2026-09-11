import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import time
import threading
from backend.app.ai.gemini_client import gemini_client
from backend.app.ai.document_intelligence import is_valid_customer_name
from backend.app.utils.helpers import format_currency
from backend.app.utils.logger import logger

# In-memory LRU cache for high-speed response on repeated generation queries
_comm_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_comm_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = 60

def sanitize_greeting(raw_body: str, customer_name: Optional[str] = None, language: str = "en") -> str:
    """
    Enforces greeting rules:
    - Never uses 'Invoice Details', 'Customer', or 'Invoice'.
    - If valid customer name exists: 'Dear <Name>,' or Tamil 'வணக்கம் <Name>,'.
    - If no valid name exists: neutral 'Hello,' or Tamil 'வணக்கம்,'.
    """
    text = (raw_body or "").strip()
    cname_clean = (customer_name or "").strip()
    if not is_valid_customer_name(cname_clean):
        cname_clean = ""

    if cname_clean:
        text = re.sub(r'Dear\s+(?:Invoice\s+Details|Customer|Invoice),?', f'Dear {cname_clean},', text, flags=re.IGNORECASE)
        text = re.sub(r'வணக்கம்\s+(?:Invoice\s+Details|Customer|Invoice),?', f'வணக்கம் {cname_clean},', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'Dear\s+(?:Invoice\s+Details|Customer|Invoice),?', 'Hello,', text, flags=re.IGNORECASE)
        text = re.sub(r'Dear\s*,', 'Hello,', text)
        text = re.sub(r'வணக்கம்\s+(?:Invoice\s+Details|Customer|Invoice),?', 'வணக்கம்,', text, flags=re.IGNORECASE)
        text = re.sub(r'வணக்கம்\s*,', 'வணக்கம்,', text)
    return text

def generate_customer_communication(
    customer_name: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    invoice_number: Optional[str] = None,
    amount: Optional[float] = None,
    currency: str = "USD",
    due_date: Optional[str] = None,
    business_name: str = "My Business",
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
    Includes caching for repeated calls and token-bounded fast generation.
    """
    t_start = time.perf_counter()
    formatted_amount = format_currency(amount or 0.0, currency)
    sig_en = business_signature or f"Regards,\nFinance & Operations Team\n{business_name}"
    sig_ta = f"நன்றி,\nநிதி மற்றும் செயல்பாட்டுக் குழு\n{business_name}"
    sig_bilingual = f"Thank you / நன்றி\n{business_name}"

    lang_desc = {
        "en": "English only",
        "ta": "Tamil (தமிழ்) only",
        "en_ta": "Bilingual (BOTH English and Tamil in the SAME message - English first, followed by Tamil translation below)"
    }.get(language, "English only")

    # 1. Sanitize customer name according to enterprise rules
    cname_clean = (customer_name or "").strip()
    if not is_valid_customer_name(cname_clean):
        cname_clean = ""

    _sanitize_greeting = lambda b: sanitize_greeting(b, cname_clean, language)

    # Check in-memory cache for exact repeat requests
    cache_key = f"{channel}:{language}:{template_type}:{tone}:{cname_clean}:{customer_phone or ''}:{invoice_number or ''}:{formatted_amount}:{due_date or ''}:{business_name}:{(custom_instructions or '').strip()}"
    with _comm_cache_lock:
        cached_entry = _comm_cache.get(cache_key)
        if cached_entry:
            cached_time, cached_data = cached_entry
            if time.time() - cached_time < CACHE_TTL_SECONDS:
                result = dict(cached_data)
                result["cached"] = True
                elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
                result["generation_time_ms"] = elapsed_ms
                logger.info(f"[Cache Hit] Returned message generation draft in {elapsed_ms}ms")
                return result

    # 2. Optimized concise prompt based on channel
    max_tokens = 250 if channel == "sms" else 550

    if channel == "sms":
        greeting_instruction = (
            f"The recipient's actual customer name is '{cname_clean}'. The message greeting MUST address them by their actual name: 'Dear {cname_clean},' (or Tamil 'வணக்கம் {cname_clean},')."
            if cname_clean else
            "The recipient's name is not available. The message MUST use the neutral greeting: 'Hello,' (or Tamil 'வணக்கம்,')."
        )
        prompt = f"""
Write a personalized, concise business SMS message.

Recipient Name: {cname_clean or 'Not available'}
Recipient Contact: {customer_phone or 'N/A'}
Business: {business_name}
Goal: {template_type} (Invoice: {invoice_number or 'N/A'}, Amount: {formatted_amount}, Due: {due_date or 'Recent'})
Tone: {tone}
{f"Special Note: {custom_instructions}" if custom_instructions else ""}

Language requirement: {lang_desc}.

MANDATORY GREETING & RECIPIENT RULES:
1. {greeting_instruction}
2. The recipient name must come ONLY from the provided structured data.
3. NEVER use field names, object names, UI labels, or placeholder text (such as 'Invoice Details', 'Invoice', 'Customer', 'Client') as a recipient name.
4. NEVER generate "Dear Invoice Details".
5. {"NEVER generate 'Dear Customer' because the actual customer name is available." if cname_clean else "NEVER generate 'Dear Invoice Details'."}
6. NEVER invent or hallucinate a person's name.
7. Max length: under 250 characters. Punchy, clear, polite.
8. Output strictly valid JSON: {{"body": "SMS message text here"}}
"""
    else:
        greeting_instruction = (
            f"The customer's actual name is '{cname_clean}'. The email greeting MUST use the customer's real name: 'Dear {cname_clean},' (or Tamil 'வணக்கம் {cname_clean},')."
            if cname_clean else
            "The customer's name is not available. The email greeting MUST use the neutral greeting: 'Hello,' (or Tamil 'வணக்கம்,')."
        )
        prompt = f"""
Write a professional business email.

Channel: EMAIL
Language: {lang_desc}
Customer Name: {cname_clean or 'Not available'}
Customer Email: {customer_email or 'N/A'}
Business: {business_name}
Goal: {template_type} (Invoice: {invoice_number or 'N/A'}, Amount: {formatted_amount}, Due: {due_date or 'Recent'})
Tone: {tone}
{f"Instructions: {custom_instructions}" if custom_instructions else ""}

MANDATORY GREETING & RECIPIENT RULES:
1. {greeting_instruction}
2. The customer name must come ONLY from the provided structured data.
3. NEVER use field names, object names, UI labels, or placeholder text (such as 'Invoice Details', 'Invoice', 'Customer', 'Client', 'Details') as a person's name.
4. NEVER generate "Dear Invoice Details".
5. {"NEVER generate 'Dear Customer' because the actual customer name is available." if cname_clean else "NEVER generate 'Dear Invoice Details'."}
6. NEVER invent or hallucinate a person's name.

Output strictly valid JSON with:
{{"subject": "Appropriate subject line", "body": "Complete email body with greeting and sign-off"}}
"""

    t_prep = time.perf_counter() - t_start
    t_api_start = time.perf_counter()

    ai_json = gemini_client.generate_json(
        prompt,
        system_instruction=(
            "You generate courteous, highly professional enterprise customer communications in English, Tamil, or Bilingual. "
            "Strictly adhere to greeting rules: address the customer by their actual name ('Dear <Name>,') when provided, "
            "or use 'Hello,' if no name is available. NEVER use 'Invoice Details', 'Customer', or field labels as a person's name. Output strictly JSON."
        ),
        max_output_tokens=max_tokens
    )

    t_api = time.perf_counter() - t_api_start

    steps = [
        f"Retrieved profile for '{cname_clean or 'Customer'}'",
        f"Configured language mode: {lang_desc}",
        f"Loaded invoice context ({invoice_number or 'General correspondence'}, {formatted_amount})" if invoice_number else "Applied general business context",
        f"Applied tone profile: {tone.capitalize()}",
        f"Channel: {channel.upper()}"
    ]

    if ai_json and "body" in ai_json:
        subj = ai_json.get("subject", "")
        if channel == "sms" and not subj:
            subj = f"SMS: {invoice_number or 'Notice'}"
        total_time_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(f"[AI Timing] prep={t_prep:.3f}s | gemini_api={t_api:.3f}s | total={total_time_ms}ms")

        result = {
            "subject": subj,
            "body": _sanitize_greeting(ai_json["body"]),
            "recipient_email": customer_email or "",
            "recipient_phone": customer_phone or "",
            "language": language,
            "channel": channel,
            "engine": "Google Gemini 2.0 Flash",
            "generation_steps": steps,
            "generation_time_ms": total_time_ms
        }

        # Cache result
        with _comm_cache_lock:
            if len(_comm_cache) > 150:
                oldest_k = min(_comm_cache.keys(), key=lambda k: _comm_cache[k][0])
                _comm_cache.pop(oldest_k, None)
            _comm_cache[cache_key] = (time.time(), result)

        return result

    # =========================================================================
    # HIGH-QUALITY LOCAL MULTILINGUAL TEMPLATES (TAMIL, ENGLISH, BILINGUAL)
    # =========================================================================
    customer_name = cname_clean
    inv_str = invoice_number or "Invoice"
    due_str = due_date or "recent date"
    instruction_snippet = f"\n\nNote: {custom_instructions.strip()}" if custom_instructions and custom_instructions.strip() else ""

    # Normalize template_type / purpose
    t_type = (template_type or "payment_reminder").lower()

    # 1. SMS CHANNEL TEMPLATES
    if channel == "sms":
        if "overdue" in t_type or t_type == "overdue_invoice":
            if language == "ta":
                subj = f"விலைப்பட்டியல் {inv_str} நிலுவைத் தொகை"
                body = (
                    f"வணக்கம் {customer_name},\n"
                    f"உங்கள் {formatted_amount} மதிப்பிலான விலைப்பட்டியல் ({inv_str}) செலுத்த வேண்டிய காலம் முடிவடைந்துள்ளது. தயவுசெய்து உடனடியாக பணம் செலுத்தவும்.\n"
                    f"- {business_name}"
                )
            elif language == "en_ta":
                subj = f"Overdue Invoice / நிலுவைத் தொகை - {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"This is a reminder that your invoice {inv_str} of {formatted_amount} is overdue. Please complete the payment at your earliest convenience.\n\n"
                    f"வணக்கம் {customer_name},\n"
                    f"உங்கள் {formatted_amount} விலைப்பட்டியலுக்கான ({inv_str}) பணம் செலுத்த வேண்டிய தேதி முடிவடைந்துள்ளது. தயவுசெய்து விரைவில் பணம் செலுத்தவும்.\n\n"
                    f"Thank you / நன்றி.\n"
                    f"- {business_name}"
                )
            else:  # English
                subj = f"Overdue Notice: Invoice {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"This is a reminder that your invoice {inv_str} of {formatted_amount} is overdue. "
                    f"Please complete the payment at your earliest convenience.\n"
                    f"Thank you.\n"
                    f"- {business_name}"
                )
        elif "reminder" in t_type or t_type == "payment_reminder":
            if language == "ta":
                subj = f"விலைப்பட்டியல் {inv_str} நினைவூட்டல்"
                body = (
                    f"வணக்கம் {customer_name},\n"
                    f"உங்கள் {formatted_amount} மதிப்பிலான விலைப்பட்டியல் ({inv_str}) பணம் செலுத்த வேண்டிய தேதி ({due_str}) முடிவடைந்துள்ளது. "
                    f"தயவுசெய்து விரைவில் பணம் செலுத்தவும்.\n"
                    f"நன்றி.\n"
                    f"- {business_name}"
                )
            elif language == "en_ta":
                subj = f"Payment Reminder / பணம் செலுத்தும் நினைவூட்டல் - {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"This is a reminder that your invoice of {formatted_amount} is overdue. Please complete the payment at your earliest convenience.\n\n"
                    f"வணக்கம் {customer_name},\n"
                    f"உங்கள் {formatted_amount} விலைப்பட்டியலுக்கான பணம் செலுத்த வேண்டிய தேதி முடிவடைந்துள்ளது. தயவுசெய்து விரைவில் பணம் செலுத்தவும்.\n\n"
                    f"Thank you / நன்றி.\n"
                    f"- {business_name}"
                )
            else:  # English default
                subj = f"Payment Reminder: Invoice {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"This is a reminder that your invoice of {formatted_amount} is overdue. "
                    f"Please complete the payment at your earliest convenience.\n"
                    f"Thank you.\n"
                    f"- {business_name}"
                )
        elif "appointment" in t_type or t_type == "appointment_reminder":
            if language == "ta":
                subj = "சந்திப்பு நினைவூட்டல்"
                body = f"வணக்கம் {customer_name}, {business_name} உடனான உங்கள் வரவிருக்கும் சந்திப்பு நினைவூட்டப்படுகிறது. நன்றி."
            elif language == "en_ta":
                subj = "Appointment Reminder / சந்திப்பு நினைவூட்டல்"
                body = (
                    f"Dear {customer_name}, reminder for your upcoming appointment with {business_name}.\n\n"
                    f"வணக்கம் {customer_name}, {business_name} உடனான உங்கள் சந்திப்பு நினைவூட்டப்படுகிறது.\n\n"
                    f"Thank you / நன்றி."
                )
            else:
                subj = "Appointment Reminder"
                body = f"Dear {customer_name}, this is a reminder for your upcoming appointment with {business_name}. Thank you."
        elif "follow" in t_type or t_type == "followup":
            if language == "ta":
                subj = f"பின்தொடர்தல் - {business_name}"
                body = f"வணக்கம் {customer_name}, எங்களது சமீபத்திய உரையாடலைத் தொடர்ந்து தொடர்பு கொள்கிறோம். உங்களுக்கு ஏதேனும் உதவி தேவைப்பட்டால் தெரிவிக்கவும். நன்றி."
            elif language == "en_ta":
                subj = f"Follow-up / பின்தொடர்தல் - {business_name}"
                body = (
                    f"Dear {customer_name}, following up on our recent conversation. Please let us know if you have any questions.\n\n"
                    f"வணக்கம் {customer_name}, எங்களது சமீபத்திய உரையாடலைத் தொடர்ந்து தொடர்பு கொள்கிறோம். உதவி தேவைப்பட்டால் தெரிவிக்கவும்.\n\n"
                    f"Thank you / நன்றி."
                )
            else:
                subj = f"Follow-up from {business_name}"
                body = f"Dear {customer_name}, following up on our recent discussion. Please let us know if we can assist you further. Thank you."
        elif "order" in t_type or t_type == "order_update":
            if language == "ta":
                subj = f"ஆர்டர் தகவல் - {business_name}"
                body = f"வணக்கம் {customer_name}, உங்கள் ஆர்டர் / கணக்கு நிலை புதுப்பிக்கப்பட்டுள்ளது. மேலும் விவரங்களுக்கு எங்களைத் தொடர்பு கொள்ளவும். நன்றி."
            elif language == "en_ta":
                subj = f"Order Update / ஆர்டர் தகவல் - {business_name}"
                body = (
                    f"Dear {customer_name}, your order/account status has been updated with {business_name}.\n\n"
                    f"வணக்கம் {customer_name}, உங்கள் ஆர்டர் நிலை புதுப்பிக்கப்பட்டுள்ளது.\n\n"
                    f"Thank you / நன்றி."
                )
            else:
                subj = f"Order Update: {business_name}"
                body = f"Dear {customer_name}, your order with {business_name} has been updated. Please contact us for details. Thank you."
        elif "confirmation" in t_type or t_type == "payment_confirmation":
            if language == "ta":
                subj = f"பணம் பெறப்பட்டது - {inv_str}"
                body = (
                    f"வணக்கம் {customer_name},\n"
                    f"விலைப்பட்டியல் {inv_str}-க்கான உங்கள் {formatted_amount} பணம் வெற்றிகரமாகப் பெறப்பட்டது. மிக்க நன்றி!\n"
                    f"- {business_name}"
                )
            elif language == "en_ta":
                subj = f"Payment Received / பணம் பெறப்பட்டது - {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"We have successfully received your payment of {formatted_amount} for invoice {inv_str}.\n\n"
                    f"வணக்கம் {customer_name},\n"
                    f"விலைப்பட்டியல் {inv_str}-க்கான உங்கள் {formatted_amount} பணம் பெறப்பட்டது.\n\n"
                    f"Thank you / நன்றி.\n"
                    f"- {business_name}"
                )
            else:
                subj = f"Payment Received: Invoice {inv_str}"
                body = (
                    f"Dear {customer_name},\n"
                    f"We have received your payment of {formatted_amount} for invoice {inv_str}. "
                    f"Thank you for your prompt payment!\n"
                    f"- {business_name}"
                )
        elif "notification" in t_type or t_type == "customer_notification":
            if language == "ta":
                subj = f"வாடிக்கையாளர் அறிவிப்பு - {business_name}"
                body = f"வணக்கம் {customer_name}, {business_name} இலிருந்து ஒரு முக்கிய அறிவிப்பு. மேலும் தகவலுக்கு எங்களைத் தொடர்பு கொள்ளவும்."
            elif language == "en_ta":
                subj = f"Notification / அறிவிப்பு - {business_name}"
                body = (
                    f"Dear {customer_name}, important customer notification from {business_name}.\n\n"
                    f"வணக்கம் {customer_name}, {business_name} இலிருந்து ஒரு முக்கிய அறிவிப்பு.\n\n"
                    f"Thank you / நன்றி."
                )
            else:
                subj = f"Notification from {business_name}"
                body = f"Dear {customer_name}, an important update regarding your account with {business_name}. Thank you."
        else:  # General SMS
            if language == "ta":
                subj = f"{business_name} தகவல்"
                body = f"வணக்கம் {customer_name}, {business_name} இலிருந்து ஒரு முக்கிய வணிகத் தகவல். மேலும் தகவலுக்கு எங்களைத் தொடர்பு கொள்ளவும். நன்றி."
            elif language == "en_ta":
                subj = f"Notice / அறிவிப்பு - {business_name}"
                body = (
                    f"Dear {customer_name}, important business notice from {business_name}. Please contact us if needed.\n\n"
                    f"வணக்கம் {customer_name}, {business_name} இலிருந்து ஒரு முக்கிய வணிகத் தகவல்.\n\n"
                    f"Thank you / நன்றி."
                )
            else:
                subj = f"Notice from {business_name}"
                body = f"Dear {customer_name}, an important message regarding your business relationship with {business_name}. Thank you."

        sms_time_ms = round((time.perf_counter() - t_start) * 1000, 2)
        sms_result = {
            "subject": subj,
            "body": body,
            "recipient_email": customer_email or "",
            "recipient_phone": customer_phone or "",
            "language": language,
            "channel": "sms",
            "engine": "Intelligent Operations Agent (Local)",
            "generation_steps": steps,
            "generation_time_ms": sms_time_ms
        }
        with _comm_cache_lock:
            if len(_comm_cache) > 150:
                oldest_k = min(_comm_cache.keys(), key=lambda k: _comm_cache[k][0])
                _comm_cache.pop(oldest_k, None)
            _comm_cache[cache_key] = (time.time(), sms_result)

        return sms_result

    # 2. EMAIL CHANNEL TEMPLATES
    if "overdue" in t_type or t_type == "overdue_invoice":
        if language == "ta":
            subj = f"முக்கியமானது: நிலுவைத் தொகை அறிவிப்பு - விலைப்பட்டியல் {inv_str}"
            body = (
                f"வணக்கம் {customer_name},\n\n"
                f"உங்கள் {formatted_amount} மதிப்பிலான விலைப்பட்டியல் ({inv_str}) பணம் செலுத்த வேண்டிய தேதி ({due_str}) முடிவடைந்துள்ளது. "
                f"தயவுசெய்து உடனடியாக பணப்பரிவர்த்தனையை நிறைவு செய்யுமாறு கேட்டுக்கொள்கிறோம்.{instruction_snippet}\n\n"
                f"ஏற்கனவே பணம் செலுத்தியிருந்தால், தயவுசெய்து இந்த செய்தியை புறக்கணிக்கவும்.\n\n"
                f"{sig_ta}"
            )
        elif language == "en_ta":
            subj = f"Overdue Invoice / நிலுவைத் தொகை - Invoice {inv_str}"
            body = (
                f"Dear {customer_name},\n\n"
                f"This is an urgent reminder that your invoice {inv_str} of {formatted_amount} is overdue (Due Date: {due_str}). "
                f"Please arrange payment at your earliest convenience.{instruction_snippet}\n\n"
                f"--------------------------------------------------\n\n"
                f"வணக்கம் {customer_name},\n\n"
                f"உங்கள் {formatted_amount} விலைப்பட்டியலுக்கான ({inv_str}) பணம் செலுத்த வேண்டிய தேதி ({due_str}) முடிவடைந்துள்ளது. "
                f"தயவுசெய்து உடனடியாக பணம் செலுத்தவும்.\n\n"
                f"{sig_bilingual}"
            )
        else:
            subj = f"URGENT: Overdue Invoice {inv_str}"
            body = (
                f"Dear {customer_name},\n\n"
                f"Our records indicate that invoice {inv_str} for {formatted_amount} is overdue (Due Date: {due_str}). "
                f"Please arrange for this balance to be settled immediately.{instruction_snippet}\n\n"
                f"If payment has already been sent, please share the confirmation reference.\n\n"
                f"{sig_en}"
            )
    elif "reminder" in t_type or t_type == "payment_reminder":
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

    elif "follow" in t_type or t_type == "customer_followup" or t_type == "followup":
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

    elif "appointment" in t_type or t_type == "appointment_confirmation" or t_type == "appointment_reminder":
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

    elif "order" in t_type or t_type == "order_update":
        if language == "ta":
            subj = f"ஆர்டர் நிலை புதுப்பிப்பு - {business_name}"
            body = (
                f"வணக்கம் {customer_name},\n\n"
                f"உங்கள் கணக்கு மற்றும் ஆர்டர் தொடர்பான புதிய விவரங்கள் புதுப்பிக்கப்பட்டுள்ளன.{instruction_snippet}\n\n"
                f"மேலும் ஏதேனும் கேள்விகள் இருந்தால் எங்களைத் தொடர்பு கொள்ளவும்.\n\n"
                f"{sig_ta}"
            )
        elif language == "en_ta":
            subj = f"Order Update / ஆர்டர் புதுப்பிப்பு - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"This is an update regarding your order and account activity with {business_name}.{instruction_snippet}\n\n"
                f"--------------------------------------------------\n\n"
                f"வணக்கம் {customer_name},\n\n"
                f"உங்கள் கணக்கு மற்றும் ஆர்டர் தொடர்பான புதிய விவரங்கள் புதுப்பிக்கப்பட்டுள்ளன.\n\n"
                f"{sig_bilingual}"
            )
        else:
            subj = f"Order & Activity Update - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"We are pleased to provide an update regarding your ongoing order and account services with {business_name}.{instruction_snippet}\n\n"
                f"Please feel free to reach out if you require any further information.\n\n"
                f"{sig_en}"
            )

    elif "notification" in t_type or t_type == "customer_notification":
        if language == "ta":
            subj = f"வாடிக்கையாளர் அறிவிப்பு - {business_name}"
            body = (
                f"வணக்கம் {customer_name},\n\n"
                f"{business_name} இலிருந்து ஒரு முக்கிய வாடிக்கையாளர் அறிவிப்பு.{instruction_snippet}\n\n"
                f"தயவுசெய்து இந்த தகவலைப் பரிசீலிக்கவும். நன்றி.\n\n"
                f"{sig_ta}"
            )
        elif language == "en_ta":
            subj = f"Customer Notification / அறிவிப்பு - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"Please find an important notification regarding your account with {business_name}.{instruction_snippet}\n\n"
                f"--------------------------------------------------\n\n"
                f"வணக்கம் {customer_name},\n\n"
                f"{business_name} இலிருந்து ஒரு முக்கிய வாடிக்கையாளர் அறிவிப்பு.\n\n"
                f"{sig_bilingual}"
            )
        else:
            subj = f"Customer Notification - {business_name}"
            body = (
                f"Dear {customer_name},\n\n"
                f"Please review this important operational notification regarding your account with {business_name}.{instruction_snippet}\n\n"
                f"Thank you for your continued partnership.\n\n"
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

    fallback_time_ms = round((time.perf_counter() - t_start) * 1000, 2)
    return {
        "subject": subj,
        "body": _sanitize_greeting(body),
        "recipient_email": customer_email or "",
        "recipient_phone": customer_phone or "",
        "language": language,
        "channel": channel,
        "engine": "Intelligent Operations Agent (Local)",
        "generation_steps": steps,
        "generation_time_ms": fallback_time_ms
    }


def generate_business_email(
    customer_name: str,
    customer_email: str,
    invoice_number: Optional[str] = None,
    amount: Optional[float] = None,
    currency: str = "USD",
    due_date: Optional[str] = None,
    business_name: str = "My Business",
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
