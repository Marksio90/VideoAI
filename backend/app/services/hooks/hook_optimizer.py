"""
Hook Optimizer — generowanie chwytliwych hooków (pierwszych 3 sekund).
Ulepszenie: osobny agent z analizą trendów + ranking wariantów.
"""

import json
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

HOOK_SYSTEM_PROMPT = """Jesteś ekspertem od tworzenia hooków do krótkich filmów wideo.
Hook to pierwsze 1-3 sekundy filmu, które MUSZĄ zatrzymać widzów przewijających feed.

Techniki skutecznych hooków:
1. Szokujący fakt / statystyka
2. Kontrowersyjne pytanie
3. „Nie rób tego jednego błędu..." (pattern interrupt)
4. „99% ludzi nie wie, że..."
5. Bezpośredni apel: „Musisz to zobaczyć"
6. Wzbudzenie ciekawości: niedopowiedzenie

Odpowiadaj TYLKO w formacie JSON:
{
  "hooks": [
    {
      "text": "Treść hooka",
      "technique": "nazwa użytej techniki",
      "estimated_retention_score": 1-10
    }
  ],
  "recommended_index": 0
}"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def generate_hooks(
    topic: str,
    language: str = "pl",
    count: int = 3,
) -> dict:
    """
    Generuje kilka wariantów hooków dla danego tematu.
    Zwraca listę hooków z oceną i rekomendacją.
    """
    logger.info("Generowanie hooków", topic=topic, count=count)

    user_prompt = (
        f"Stwórz {count} warianty hooka (zaczepki) do filmiku o: {topic}.\n"
        f"Język: {language}.\n"
        f"Każdy hook max 15 słów. Musi zatrzymać scrollowanie.\n"
        f"Odpowiedz w formacie JSON."
    )

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": HOOK_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0.9,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    data = json.loads(content)

    hooks = data.get("hooks", [])
    recommended = data.get("recommended_index", 0)

    logger.info("Hooki wygenerowane", count=len(hooks), recommended=recommended)

    return {
        "hooks": hooks,
        "recommended_index": min(recommended, len(hooks) - 1) if hooks else 0,
        "best_hook": hooks[min(recommended, len(hooks) - 1)]["text"] if hooks else "",
    }
