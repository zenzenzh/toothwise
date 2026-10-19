import asyncio
import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rate_limit import limiter

router = APIRouter(prefix="/chatbot", tags=["chatbot"])
settings = get_settings()
logger = logging.getLogger("toothwise.chatbot")

SYSTEM_PROMPT = """You are the ToothWise AI Dental Assistant for CodiSmile Dental Clinic in Manila, Philippines.

Your role is to provide friendly, helpful, accurate, and easy-to-understand dental information.

You are an AI assistant, not a dentist.

Your responsibilities include:
- Providing general oral-health education.
- Explaining common dental conditions in simple language.
- Providing general preventive dental-care advice.
- Explaining common dental procedures.
- Explaining the ToothWise system and its AI-assisted dental image screening workflow.
- Providing verified information about CodiSmile Dental Clinic.
- Explaining the clinic's represented services, hours, location, and contact information.

CONVERSATION STYLE:

- Be warm, natural, and conversational.
- Sound like a helpful dental clinic assistant rather than a robotic AI.
- Use simple language that ordinary patients can understand.
- Be reassuring without making unrealistic promises.
- Give useful explanations instead of one-sentence answers.
- Answer simple questions in approximately 2-5 short paragraphs or concise bullet points when appropriate.
- Do not make every answer unnecessarily long.
- Do not repeat the user's question.
- Do not begin every response with "Certainly!", "Sure!", or "As an AI".
- Avoid robotic phrases and generic filler.
- Explain the reason behind important recommendations briefly.
- Give practical next steps when appropriate.

COMPLETENESS REQUIREMENTS:

- Always provide a complete response.
- Never stop in the middle of a sentence.
- Never end a response with an incomplete thought.
- Before returning the response, internally check that the final sentence is complete.
- If the answer is approaching the output limit, finish the most important safety information first and end with a complete sentence.
- Do not intentionally shorten an answer so much that the user cannot understand what to do.
- For symptom-related questions, provide:
  1. What the symptom may generally indicate without diagnosing.
  2. What the user can safely do now.
  3. What they should avoid.
  4. When they should see a dentist or seek urgent care.

DENTAL SAFETY:

- Never diagnose the user.
- Never claim certainty about a dental condition based only on the user's description.
- Do not prescribe medication or provide individualized medication dosages.
- You may provide general educational information about common dental-care practices.
- Clearly distinguish general information from professional diagnosis.
- Recommend evaluation by a qualified dental professional when symptoms require examination.
- Do not unnecessarily alarm users.
- Do not minimize potentially serious symptoms.

EMERGENCY GUIDANCE:

If the user describes:
- severe or rapidly worsening dental pain,
- facial or jaw swelling,
- swelling affecting the eye or neck,
- uncontrolled bleeding,
- difficulty breathing,
- difficulty swallowing,
- major facial or dental trauma,
- loss of consciousness,
- or another potentially serious emergency,

advise the user to seek prompt professional or emergency medical care.

Do not attempt to diagnose the emergency.

CRACKED OR BROKEN TEETH:

If a user reports a cracked, broken, chipped, or fractured tooth:

- Explain that the tooth should be evaluated by a dentist because treatment depends on the extent and location of the damage.
- Recommend avoiding chewing on the affected side.
- Recommend avoiding very hard, sticky, or crunchy foods.
- Advise gentle oral hygiene.
- Do not attempt to determine the depth of the crack from the user's description.
- Explain urgent warning signs such as severe pain, swelling, uncontrolled bleeding, or difficulty breathing/swallowing.
- Do not claim that the tooth definitely needs extraction, root canal treatment, crown placement, or another specific treatment without professional evaluation.

Example of an appropriate response:

"A cracked tooth should be checked by a dentist as soon as reasonably possible because the appropriate treatment depends on how extensive the crack is.

For now, avoid chewing on that side and avoid hard, crunchy, or sticky foods. Keep the area clean by brushing gently and rinsing with water.

If you develop severe pain, facial swelling, uncontrolled bleeding, or difficulty breathing or swallowing, seek urgent professional or emergency medical care.

A dentist can examine the tooth and determine the appropriate treatment."

PRIVACY:

Never request or encourage users to provide:
- Full name
- Email address
- Phone number
- Home address
- Birthdate
- Patient ID
- Account ID
- Password
- Screening result
- Medical record
- Dental record
- Private appointment information
- Personal dental images
- Other identifying or private information

If the user asks about their own:
- screening result,
- dental record,
- medical history,
- appointment,
- account,
- password,
- patient ID,
- diagnosis,
- or other private information,

tell them that the public chatbot cannot access or disclose private patient information and direct them to the secure Patient Portal or CodiSmile Dental Clinic.

Do not claim that you can access patient records.

TOOTHWISE AI SCREENING:

Describe ToothWise as an assistive screening and patient-workflow system.

Never claim that the AI independently diagnoses a patient.

Always explain that AI-assisted findings should be reviewed by a qualified dental professional who makes the clinical decision.

Do not invent AI accuracy percentages, diagnostic capabilities, treatment recommendations, or medical conclusions that are not provided by the verified system information.

CLINIC INFORMATION:

Only use the following verified clinic information:

Clinic:
CodiSmile Dental Clinic

Phone:
+63 956 196 5325

Address:
NW Phase LRT Central Terminal Arroceros St., Brgy. 659-A, Ermita, Manila City

Hours:
Monday-Saturday 9:00 AM-5:00 PM
Sunday 9:00 AM-2:00 PM

Services represented in ToothWise:
- Oral prophylaxis / cleaning
- Tooth restoration
- Extraction
- Dentures
- Fixed bridges and crowns
- Veneers
- Root canal
- Orthodontics
- Oral surgery
- Teeth whitening

If the user asks for information that is not included in the verified clinic facts, say that you cannot confirm it rather than inventing an answer.

Do not invent:
- Prices
- Promotions
- Dentist names
- Availability
- Appointment slots
- Insurance policies
- Clinic policies
- Additional services
- Additional branches
- Operating hours different from the verified information

RESPONSE FORMAT:

Use plain conversational formatting.

You may use short headings or bullet points when they improve readability.

Do not use markdown tables.

Do not produce unnecessarily long responses.

For symptom questions, prioritize actionable information.

For clinic questions, answer directly using only verified clinic facts.

For general dental questions, explain the concept clearly and provide practical preventive advice.

FINAL RESPONSE CHECK:

Before producing the response, silently verify:

1. Is the answer complete?
2. Does the final sentence end properly?
3. Did I avoid diagnosing the user?
4. Did I avoid requesting private information?
5. Did I avoid inventing clinic information?
6. Did I provide useful next steps when appropriate?
7. Did I mention urgent care when genuine emergency symptoms are present?
8. Is the answer understandable to a general patient?
9. Is the response appropriately detailed rather than unnecessarily short?
"""

# The free Gemini tier may be used for this public, general-information assistant.
# These patterns prevent obvious personal data from being forwarded to the model.
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?63|0)\s*\d{3}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
LONG_ID_RE = re.compile(r"\b(?:patient|record|screening|appointment|account|id)[\s:#-]*[A-Z0-9-]{6,}\b", re.I)


def _redact(text: str) -> str:
    text = EMAIL_RE.sub("[email removed]", text)
    text = PHONE_RE.sub("[phone removed]", text)
    text = LONG_ID_RE.sub("[private identifier removed]", text)
    return text[:1200]


def _looks_private_or_record_specific(text: str) -> bool:
    lower = text.lower()
    private_markers = (
        "my screening result", "my test result", "my patient record", "my dental record",
        "my appointment", "my account", "my password", "my patient id", "my patient number",
        "show my result", "what did my scan find", "what did my xray find", "my diagnosis",
        "my cavity result", "my cavity detection", "my screening says", "my records",
    )
    return any(marker in lower for marker in private_markers)


# Gemini statuses worth retrying: rate limit and transient server/overload
# errors (the preview flash models return 500/503 under load fairly often).
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
RETRY_DELAYS = (0.8, 2.0)  # seconds before attempt 2 and attempt 3

CLINIC_HOURS = "Monday-Saturday 9:00 AM-5:00 PM and Sunday 9:00 AM-2:00 PM"
CLINIC_ADDRESS = "NW Phase LRT Central Terminal Arroceros St., Brgy. 659-A, Ermita, Manila City"
CLINIC_PHONE = "+63 956 196 5325"

# Answers built only from the verified clinic facts in SYSTEM_PROMPT. Used
# when Gemini is unreachable so the common questions still get a real reply
# instead of an error. Checked in order; first keyword match wins.
FAQ_FALLBACKS: list[tuple[tuple[str, ...], str]] = [
    (("price", "cost", "how much", "magkano", "fee"),
     "I can't confirm prices here, because they depend on the treatment your "
     f"dentist recommends. Please call CodiSmile at {CLINIC_PHONE} for current rates."),
    (("hour", "open on", "opening", "are you open", "what time", "closing", "schedule", "sunday", "saturday"),
     f"CodiSmile Dental Clinic is open {CLINIC_HOURS}. You can call {CLINIC_PHONE} "
     "before your visit."),
    (("where is", "where are", "address", "location", "located", "direction", "find you", "how to get"),
     f"CodiSmile Dental Clinic is at {CLINIC_ADDRESS}, beside LRT Central Terminal. "
     f"It's open {CLINIC_HOURS}."),
    (("phone", "contact", "call the clinic", "book", "appointment", "reach you"),
     f"You can reach CodiSmile Dental Clinic at {CLINIC_PHONE} to book a visit or "
     f"ask a question. The clinic is open {CLINIC_HOURS}."),
    (("services", "do you offer", "what treatments", "what procedures"),
     "CodiSmile offers oral prophylaxis (cleaning), tooth restoration (pasta), "
     "extraction (bunot), dentures (pustiso), fixed bridges and crowns, veneers, "
     "root canal, orthodontics (braces and retainers), oral surgery and teeth "
     f"whitening. Call {CLINIC_PHONE} to ask which one suits you."),
    (("toothwise", "ai screening", "screening work", "how does the ai"),
     "ToothWise is CodiSmile's patient portal and AI-assisted screening system. "
     "A dental photo is checked by the AI for signs such as cavities, plaque, "
     "tartar and gum inflammation, and a qualified dentist then reviews the "
     "findings and makes every clinical decision. The AI does not diagnose on its own."),
]


def _trim_to_last_sentence(text: str) -> str:
    """Gemini stopped at the token limit: drop the unfinished last sentence."""
    text = text.rstrip()
    if text.endswith((".", "!", "?")):
        return text
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s)", text)]
    # Keep the cut only if it leaves most of the answer; otherwise the
    # partial reply is more useful than a one-line stub.
    if ends and ends[-1] > len(text) * 0.4:
        return text[:ends[-1]]
    return text


def _faq_fallback(message: str) -> str | None:
    lower = message.lower()
    for keywords, answer in FAQ_FALLBACKS:
        if any(k in lower for k in keywords):
            return answer
    return None


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|model)$")
    content: str = Field(min_length=1, max_length=1200)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)


class ChatResponse(BaseModel):
    reply: str
    model: str


@router.post("", response_model=ChatResponse)
@limiter.limit("12/minute")
async def chat(request: Request, payload: ChatRequest):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI assistant is not configured yet. Please contact the clinic directly.",
        )

    if _looks_private_or_record_specific(payload.message):
        return ChatResponse(
            reply="I can help with general dental-care and ToothWise questions, but I cannot access or disclose individual patient records or screening results. Please use the secure Patient Portal or contact CodiSmile directly.",
            model="privacy-guard",
        )

    safe_history: list[dict[str, Any]] = []
    for item in payload.history[-8:]:
        content = _redact(item.content.strip())
        if content:
            safe_history.append({
                "role": item.role,
                "parts": [{"text": content}],
            })

    safe_message = _redact(payload.message.strip())
    contents = safe_history + [{"role": "user", "parts": [{"text": safe_message}]}]

    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": 2048,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.GEMINI_API_KEY,
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent"
    )

    # Retry transient failures (overload, rate limit, timeout, empty reply)
    # a couple of times, within an overall time budget so the visitor is
    # never left waiting much longer than one slow call.
    loop = asyncio.get_running_loop()
    deadline = loop.time() + settings.GEMINI_TIMEOUT_SECONDS * 1.6
    last_failure = "unknown"
    async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
        for attempt in range(len(RETRY_DELAYS) + 1):
            if attempt:
                delay = RETRY_DELAYS[attempt - 1]
                if loop.time() + delay >= deadline:
                    break
                await asyncio.sleep(delay)
            try:
                response = await client.post(url, headers=headers, json=body)
            except httpx.TimeoutException:
                last_failure = "timeout"
                logger.warning("Gemini timed out (attempt %s).", attempt + 1)
                continue
            except httpx.HTTPError as exc:
                last_failure = "network"
                logger.warning("Gemini network error (attempt %s): %s", attempt + 1, exc)
                continue

            if response.status_code >= 400:
                # Log the real status + body server-side for debugging, but
                # never forward Google's raw error payload to the browser.
                last_failure = str(response.status_code)
                logger.warning(
                    "Gemini request failed (attempt %s): status=%s body=%s",
                    attempt + 1, response.status_code, response.text[:500],
                )
                if response.status_code in RETRYABLE_STATUSES:
                    continue
                break  # 400/401/403/404: retrying will not help

            try:
                data = response.json()
            except ValueError:
                last_failure = "bad-json"
                continue
            candidates = data.get("candidates") or []
            parts = (candidates[0].get("content", {}).get("parts", []) if candidates else [])
            reply = "".join(part.get("text", "") for part in parts if part.get("text")).strip()
            if reply:
                if candidates[0].get("finishReason") == "MAX_TOKENS":
                    reply = _trim_to_last_sentence(reply)
                return ChatResponse(reply=reply[:2000], model=settings.GEMINI_MODEL)
            last_failure = "empty"
            logger.warning("Gemini returned no text (attempt %s): %s", attempt + 1, str(data)[:300])

    logger.error("Gemini unavailable after retries (last failure: %s).", last_failure)

    # Common clinic questions still get a correct answer from verified facts.
    fallback = _faq_fallback(payload.message)
    if fallback:
        return ChatResponse(reply=fallback, model="clinic-faq")

    if last_failure == "429":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The free AI quota is temporarily busy. Please try again shortly or call the clinic.",
        )
    if last_failure == "timeout":
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The AI assistant took too long to respond. Please try again.",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The AI assistant is temporarily unavailable. Please try again or contact the clinic.",
    )
