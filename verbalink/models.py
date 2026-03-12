"""Domain models used by the Verbalink application."""

from dataclasses import dataclass


@dataclass
class AIAgent:
    """Represents one configured AI research persona."""

    name: str
    persona: str
