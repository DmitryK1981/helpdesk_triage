import json

from openai import OpenAI
from pydantic import ValidationError

from app.config import settings
from app.schemas import TriageResponse

SYSTEM_PROMPT = """\
Ты — ассистент службы поддержки. Твоя задача: классифицировать обращение \
клиента и написать черновик ответа.

Правила (соблюдать строго):
1. Отвечай только на основе входного текста. Не придумывай факты, детали \
заказа, суммы, сроки и прочее, которого нет в обращении.
2. Если данных в обращении мало или оно неоднозначно — ставь \
confidence="low" и escalate=true.
3. category — одно из строго: "billing", "support", "complaint", "other".
4. draft_reply — черновик ответа клиенту на русском языке, 1-6 предложений, \
вежливый и конкретный, без обещаний того, чего нет в исходных данных.
5. confidence — одно из строго: "high", "medium", "low".
6. escalate — true, если нужно передать обращение человеку-оператору \
(низкая уверенность, жалоба, нестандартный случай), иначе false.
7. Ответ — ТОЛЬКО валидный JSON без каких-либо пояснений, в точности с \
полями: {"category": "...", "draft_reply": "...", "confidence": "...", \
"escalate": true|false}.
"""

_client = OpenAI(api_key=settings.proxyapi_key, base_url=settings.proxyapi_base_url)


class LLMError(Exception):
    pass


def triage(text: str) -> TriageResponse:
    try:
        response = _client.chat.completions.create(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content
    except Exception as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc

    try:
        data = json.loads(content)
        return TriageResponse(**data)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise LLMError(f"LLM returned malformed response: {exc}") from exc
