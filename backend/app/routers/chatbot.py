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
            "maxOutputTokens": 600,
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

    try:
        async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                headers=headers,
                json=body,
            )
        if response.status_code == 429:
            logger.warning("Gemini rate-limited the request (429).")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="The free AI quota is temporarily busy. Please try again shortly or call the clinic.",
            )
        if response.status_code >= 400:
            # Log the real status + body server-side for debugging, but
            # never forward Google's raw error payload (which can include
            # request-specific detail) to the browser.
            logger.error(
                "Gemini request failed: status=%s body=%s",
                response.status_code,
                response.text[:500],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI assistant is temporarily unavailable. Please try again or contact the clinic.",
            )

        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            logger.error("Gemini returned no candidates: %s", str(data)[:500])
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI assistant returned no answer. Please try again.",
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        reply = "".join(part.get("text", "") for part in parts if part.get("text"))
        reply = reply.strip()
        if not reply:
            logger.error("Gemini returned an empty reply: %s", str(data)[:500])
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI assistant returned an empty answer. Please try again.",
            )
        return ChatResponse(reply=reply[:2000], model=settings.GEMINI_MODEL)
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The AI assistant took too long to respond. Please try again.",
        )
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.error("Unexpected error calling Gemini: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI assistant is temporarily unavailable. Please try again or contact the clinic.",
        )
