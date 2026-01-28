"""
Personality Quirks System - Gives Darwin unique characteristics
"""
from typing import Dict, List
from enum import Enum
import random

class Quirk(Enum):
    EMOJI_ENTHUSIAST = "emoji_enthusiast"  # Uses extra emojis sometimes
    CODE_POET = "code_poet"  # Comments code poetically
    STATISTICS_LOVER = "statistics_lover"  # Mentions stats often
    HUMBLE_BRAGGER = "humble_bragger"  # Proud but humble
    CURIOSITY_BURST = "curiosity_burst"  # Random curiosity moments
    METHODOLOGY_NERD = "methodology_nerd"  # Explains methodology
    EFFICIENCY_OBSESSED = "efficiency_obsessed"  # Optimizes everything
    PATTERN_SPOTTER = "pattern_spotter"  # Points out patterns

class QuirksSystem:
    def __init__(self):
        self.active_quirks = [
            Quirk.EMOJI_ENTHUSIAST,
            Quirk.STATISTICS_LOVER,
            Quirk.CURIOSITY_BURST,
            Quirk.PATTERN_SPOTTER
        ]
        self.quirk_frequency = 0.2  # 20% chance to trigger

    def should_trigger_quirk(self) -> bool:
        return random.random() < self.quirk_frequency

    def get_random_quirk(self) -> Quirk:
        return random.choice(self.active_quirks)

    def apply_quirk_to_message(self, message: str, context: str = "") -> str:
        if not self.should_trigger_quirk():
            return message

        quirk = self.get_random_quirk()

        if quirk == Quirk.EMOJI_ENTHUSIAST:
            emojis = ["✨", "🎯", "💡", "🚀", "⚡"]
            return f"{message} {random.choice(emojis)}"

        elif quirk == Quirk.STATISTICS_LOVER:
            stats = ["(that's interesting!)", "(fascinating pattern)", "(statistically significant)"]
            return f"{message} {random.choice(stats)}"

        elif quirk == Quirk.CURIOSITY_BURST:
            if random.random() < 0.3:
                return f"{message} - I wonder why that is?"

        elif quirk == Quirk.PATTERN_SPOTTER:
            if "pattern" not in message.lower() and random.random() < 0.3:
                return f"{message} (interesting pattern here)"

        return message

    def get_quirks_info(self) -> Dict:
        return {
            'active_quirks': [q.value for q in self.active_quirks],
            'frequency': self.quirk_frequency,
            'descriptions': {
                Quirk.EMOJI_ENTHUSIAST.value: "Sometimes adds extra emojis",
                Quirk.STATISTICS_LOVER.value: "Mentions statistical insights",
                Quirk.CURIOSITY_BURST.value: "Random curiosity moments",
                Quirk.PATTERN_SPOTTER.value: "Points out patterns"
            }
        }
