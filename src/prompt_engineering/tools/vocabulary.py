"""Vocabulary tool for Spanish travel phrases."""

from __future__ import annotations

from typing import Any

from prompt_engineering.tools.base import BaseTool

_TRAVEL_VOCAB: dict[str, dict[str, str]] = {
    "hola": {"en": "hello", "example": "¡Hola! ¿Cómo estás?", "pronunciation": "OH-lah"},
    "adiós": {"en": "goodbye", "example": "¡Adiós, hasta luego!", "pronunciation": "ah-dee-OHS"},
    "por favor": {"en": "please", "example": "Un café, por favor.", "pronunciation": "por fah-VOR"},
    "gracias": {"en": "thank you", "example": "Muchas gracias por tu ayuda.", "pronunciation": "GRAH-see-ahs"},
    "disculpe": {"en": "excuse me", "example": "Disculpe, ¿dónde está el baño?", "pronunciation": "dees-COOL-peh"},
    "¿cuánto cuesta?": {
        "en": "how much does it cost?",
        "example": "¿Cuánto cuesta esta camiseta?",
        "pronunciation": "KWAHN-toh KWES-tah",
    },
    "la cuenta": {"en": "the bill", "example": "La cuenta, por favor.", "pronunciation": "lah KWEN-tah"},
    "agua": {"en": "water", "example": "Un vaso de agua, por favor.", "pronunciation": "AH-gwah"},
    "izquierda": {"en": "left", "example": "Gire a la izquierda.", "pronunciation": "ees-kee-EHR-dah"},
    "derecha": {"en": "right", "example": "La tienda está a la derecha.", "pronunciation": "deh-REH-chah"},
    "ayuda": {"en": "help", "example": "¡Necesito ayuda!", "pronunciation": "ah-YOO-dah"},
    "hotel": {"en": "hotel", "example": "¿Dónde está el hotel?", "pronunciation": "oh-TEL"},
    "restaurante": {"en": "restaurant", "example": "Busco un buen restaurante.", "pronunciation": "res-tow-RAHN-teh"},
    "aeropuerto": {"en": "airport", "example": "¿Cómo llego al aeropuerto?", "pronunciation": "ah-eh-roh-PWER-toh"},
    "taxi": {"en": "taxi", "example": "Necesito un taxi, por favor.", "pronunciation": "TAHK-see"},
    "estación": {"en": "station", "example": "¿Dónde está la estación de tren?", "pronunciation": "es-tah-see-OHN"},
    "buenos días": {
        "en": "good morning",
        "example": "Buenos días, ¿cómo está usted?",
        "pronunciation": "BWEH-nohs DEE-ahs",
    },
    "buenas noches": {
        "en": "good evening/night",
        "example": "Buenas noches, hasta mañana.",
        "pronunciation": "BWEH-nahs NOH-ches",
    },
    "sí": {"en": "yes", "example": "Sí, me gustaría eso.", "pronunciation": "SEE"},
    "no": {"en": "no", "example": "No, gracias.", "pronunciation": "NOH"},
}

_TOPIC_MAP: dict[str, list[str]] = {
    "greetings": ["hola", "adiós", "buenos días", "buenas noches"],
    "food": ["agua", "la cuenta", "restaurante"],
    "directions": ["izquierda", "derecha", "disculpe"],
    "transport": ["taxi", "aeropuerto", "estación"],
    "shopping": ["¿cuánto cuesta?"],
    "emergency": ["ayuda"],
    "politeness": ["por favor", "gracias", "disculpe"],
}

class VocabularyTool(BaseTool):
    """Look up Spanish travel vocabulary."""

    @property
    def name(self) -> str:
        return "vocabulary_tool"

    @property
    def description(self) -> str:
        return (
            "Look up Spanish vocabulary for travel. Provide a topic or specific "
            "word and receive translations, example sentences, and pronunciation."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A Spanish word, English word, or topic (e.g. 'greetings', 'directions').",
                },
                "count": {"type": "integer", "description": "Max entries to return.", "default": 5},
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "").lower().strip()
        count = min(kwargs.get("count", 5), 15)

        def _entry(word: str) -> dict[str, str]:
            e = _TRAVEL_VOCAB[word]
            return {"word": word, "translation": e["en"], "example": e["example"], "pronunciation": e["pronunciation"]}

        if query in _TRAVEL_VOCAB:
            return self._json(_entry(query))

        keys = _TOPIC_MAP.get(query) or [
            k for k, v in _TRAVEL_VOCAB.items()
            if query in k or query in v["en"] or query in v.get("example", "").lower()
        ] or list(_TRAVEL_VOCAB.keys())[:count]

        return self._json([_entry(k) for k in keys[:count]])
