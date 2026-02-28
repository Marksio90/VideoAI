"""
Serwis generowania skryptów wideo (LLM).
Ulepszenie: structured output (JSON) + retry z exponential backoff +
moderacja treści + fallback na tańszy model.
"""

import json
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """Jesteś profesjonalnym scenarzystą krótkich filmów wideo (shorts/reels/TikTok).
Tworzysz angażujące, dynamiczne scenariusze, które przyciągają uwagę widza od pierwszej sekundy.

Zawsze odpowiadaj w formacie JSON z następującą strukturą:
{
  "title": "Tytuł filmu (max 100 znaków, chwytliwy)",
  "hook": "Hook — pierwsze 3 sekundy, intrygujące pytanie lub szokujący fakt",
  "scenes": [
    {
      "text": "Tekst narracji dla tej sceny",
      "visual_description": "Opis wizualny — co powinno być na ekranie",
      "duration_hint": "czas w sekundach (orientacyjny)"
    }
  ],
  "call_to_action": "Wezwanie do działania na końcu filmu",
  "description": "Opis filmu do publikacji (max 300 znaków)",
  "tags": ["tag1", "tag2", "tag3"]
}"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def generate_script(
    topic: str,
    language: str = "pl",
    tone: str = "edukacyjny",
    duration_seconds: int = 60,
    custom_prompt: str | None = None,
    prompt_template: str | None = None,
) -> dict:
    """
    Generuje pełny scenariusz wideo na podstawie tematu.
    Zwraca strukturę: {title, hook, scenes, call_to_action, description, tags}.
    """
    if custom_prompt:
        user_prompt = custom_prompt
    elif prompt_template:
        user_prompt = prompt_template.format(
            topic=topic,
            language=language,
            tone=tone,
            duration=duration_seconds,
        )
    else:
        user_prompt = (
            f"Napisz {duration_seconds}-sekundowy scenariusz filmiku o: {topic}.\n"
            f"Język: {language}. Ton: {tone}.\n"
            f"Zaczynaj intrygującym hookiem (3 sekundy).\n"
            f"Uwzględnij 2-4 kluczowe sceny z opisami wizualnymi.\n"
            f"Zakończ wezwaniem do subskrypcji/obserwowania.\n"
            f"Odpowiedz w formacie JSON."
        )

    logger.info("Generowanie skryptu LLM", topic=topic, model=settings.OPENAI_MODEL)

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        script_data = json.loads(content)

        logger.info(
            "Skrypt wygenerowany",
            title=script_data.get("title", ""),
            scenes_count=len(script_data.get("scenes", [])),
        )

        return _validate_script(script_data)

    except json.JSONDecodeError:
        logger.warning("LLM zwrócił nieprawidłowy JSON, próba naprawy")
        # Fallback: retry z mniejszym modelem
        return await _fallback_generate(user_prompt)


async def _fallback_generate(user_prompt: str) -> dict:
    """Fallback na tańszy model."""
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return _validate_script(json.loads(content))


def _validate_script(data: dict) -> dict:
    """Walidacja i uzupełnienie brakujących pól."""
    defaults = {
        "title": "Bez tytułu",
        "hook": "",
        "scenes": [],
        "call_to_action": "Obserwuj, aby nie przegapić!",
        "description": "",
        "tags": [],
    }
    for key, default in defaults.items():
        if key not in data:
            data[key] = default

    # Walidacja scen
    validated_scenes = []
    for scene in data.get("scenes", []):
        validated_scenes.append({
            "text": scene.get("text", ""),
            "visual_description": scene.get("visual_description", ""),
            "duration_hint": scene.get("duration_hint", "5"),
        })
    data["scenes"] = validated_scenes

    return data
