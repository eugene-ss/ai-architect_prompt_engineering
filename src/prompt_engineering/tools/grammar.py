"""Grammar explanation tool for Spanish learners."""

from __future__ import annotations

from typing import Any

from prompt_engineering.tools.base import BaseTool

_GRAMMAR_LESSONS: dict[str, dict[str, Any]] = {
    "gendered nouns": {
        "rule": (
            "Spanish nouns are either masculine or feminine. Most nouns ending "
            "in -o are masculine (el libro), most ending in -a are feminine "
            "(la mesa). Articles must agree in gender."
        ),
        "examples": [
            "el gato (the cat, masculine)",
            "la casa (the house, feminine)",
            "el agua (exception: feminine despite el)",
        ],
        "common_mistakes": [
            "Using 'la' with masculine nouns",
            "Forgetting that some -a nouns are masculine (el día, el mapa)",
        ],
    },
    "ser vs estar": {
        "rule": (
            "Both mean 'to be'. Use 'ser' for identity, origin, permanent "
            "traits. Use 'estar' for location, temporary states, feelings."
        ),
        "examples": [
            "Soy americano. (identity)",
            "Estoy cansado. (temporary state)",
            "El hotel está aquí. (location)",
        ],
        "common_mistakes": ["Using ser for location", "Using estar for nationality"],
    },
    "present tense regular verbs": {
        "rule": (
            "Regular verbs follow three patterns based on infinitive ending: "
            "-ar, -er, -ir. Drop the ending and add the appropriate suffix."
        ),
        "examples": [
            "hablar → yo hablo, tú hablas, él habla",
            "comer → yo como, tú comes, él come",
            "vivir → yo vivo, tú vives, él vive",
        ],
        "common_mistakes": [
            "Mixing -ar and -er endings",
            "Forgetting the accent on tú forms in some tenses",
        ],
    },
    "definite and indefinite articles": {
        "rule": (
            "Definite articles (el, la, los, las) = 'the'. Indefinite articles "
            "(un, una, unos, unas) = 'a/an/some'. Must agree in gender and number."
        ),
        "examples": ["el libro / los libros", "una mesa / unas mesas"],
        "common_mistakes": [
            "Omitting the article when required in Spanish but not in English"
        ],
    },
    "basic question formation": {
        "rule": (
            "Questions use inverted question marks (¿...?). Form by inversion "
            "or question words: ¿qué? ¿dónde? ¿cuándo? ¿cómo? ¿cuánto?"
        ),
        "examples": ["¿Dónde está el baño?", "¿Cuánto cuesta?", "¿Hablas inglés?"],
        "common_mistakes": [
            "Forgetting the inverted question mark ¿",
            "Wrong word order after question words",
        ],
    },
    "negation": {
        "rule": (
            "Place 'no' directly before the verb. Double negatives are "
            "grammatically correct in Spanish."
        ),
        "examples": ["No hablo español.", "No tengo nada."],
        "common_mistakes": [
            "Placing 'no' after the verb",
            "Avoiding double negatives (they are correct in Spanish)",
        ],
    },
}

class GrammarTool(BaseTool):
    """Explain Spanish grammar rules with examples."""

    @property
    def name(self) -> str:
        return "grammar_tool"

    @property
    def description(self) -> str:
        return (
            "Explain Spanish grammar rules. Provide a topic (e.g. 'ser vs estar', "
            "'present tense regular verbs') and receive rule explanations, examples, "
            "and common mistakes."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Grammar topic. Available: " + ", ".join(_GRAMMAR_LESSONS.keys()),
                },
            },
            "required": ["topic"],
        }

    async def execute(self, **kwargs: Any) -> str:
        topic = kwargs.get("topic", "").lower().strip()

        if topic in _GRAMMAR_LESSONS:
            return self._json({"topic": topic, **_GRAMMAR_LESSONS[topic]})

        matches = [k for k in _GRAMMAR_LESSONS if topic in k or k in topic]
        if matches:
            return self._json([{"topic": k, **_GRAMMAR_LESSONS[k]} for k in matches])

        return self._json({"error": f"Topic '{topic}' not found.", "available_topics": list(_GRAMMAR_LESSONS.keys())})
