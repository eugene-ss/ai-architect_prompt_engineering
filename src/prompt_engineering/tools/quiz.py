"""Quiz generation tool for Spanish practice exercises."""

from __future__ import annotations

import random
from typing import Any

from prompt_engineering.tools.base import BaseTool

_QUIZ_BANK: dict[str, list[dict[str, Any]]] = {
    "fill_in_the_blank": [
        {"question": "¡___! ¿Cómo estás?", "answer": "Hola", "hint": "A common greeting"},
        {"question": "Un café, ___ ___.", "answer": "por favor", "hint": "How to say 'please'"},
        {"question": "¿___ está el baño?", "answer": "Dónde", "hint": "Asking 'where'"},
        {"question": "La tienda está a la ___.", "answer": "derecha", "hint": "Opposite of left"},
        {"question": "Yo ___ español. (hablar)", "answer": "hablo", "hint": "Present tense -ar for 'yo'"},
        {"question": "___ días, señor.", "answer": "Buenos", "hint": "Good morning"},
        {"question": "¿Cuánto ___?", "answer": "cuesta", "hint": "How much does it cost?"},
        {"question": "Necesito un ___, por favor.", "answer": "taxi", "hint": "A vehicle for hire"},
    ],
    "translation": [
        {"source": "Where is the airport?", "answer": "¿Dónde está el aeropuerto?"},
        {"source": "Thank you very much.", "answer": "Muchas gracias."},
        {"source": "I don't speak Spanish.", "answer": "No hablo español."},
        {"source": "The bill, please.", "answer": "La cuenta, por favor."},
        {"source": "I need help!", "answer": "¡Necesito ayuda!"},
        {"source": "How much does this cost?", "answer": "¿Cuánto cuesta esto?"},
        {"source": "Good evening.", "answer": "Buenas noches."},
        {"source": "Turn left.", "answer": "Gire a la izquierda."},
    ],
    "multiple_choice": [
        {
            "question": "What does '¿Cuánto cuesta?' mean?",
            "options": ["Where is it?", "How much does it cost?", "What time is it?", "How are you?"],
            "answer": "How much does it cost?",
        },
        {
            "question": "Which is the correct translation of 'goodbye'?",
            "options": ["Hola", "Gracias", "Adiós", "Por favor"],
            "answer": "Adiós",
        },
        {
            "question": "How do you say 'I am tired' in Spanish?",
            "options": ["Soy cansado", "Estoy cansado", "Tengo cansado", "Hago cansado"],
            "answer": "Estoy cansado",
        },
        {
            "question": "'El gato' is masculine. Which article goes with 'casa'?",
            "options": ["el", "la", "los", "un"],
            "answer": "la",
        },
    ],
}

class QuizTool(BaseTool):

    @property
    def name(self) -> str:
        return "quiz_tool"

    @property
    def description(self) -> str:
        return (
            "Generate a Spanish practice quiz. Choose a format (fill_in_the_blank, "
            "translation, multiple_choice) and the number of questions."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["fill_in_the_blank", "translation", "multiple_choice"],
                    "description": "Quiz format.",
                },
                "count": {"type": "integer", "description": "Number of questions (max 8).", "default": 3},
            },
            "required": ["format"],
        }

    async def execute(self, **kwargs: Any) -> str:
        fmt = kwargs.get("format", "fill_in_the_blank")
        count = min(kwargs.get("count", 3), 8)
        bank = _QUIZ_BANK.get(fmt)
        if not bank:
            return self._json({"error": f"Unknown format '{fmt}'", "available": list(_QUIZ_BANK.keys())})
        return self._json({"format": fmt, "questions": random.sample(bank, min(count, len(bank)))})
