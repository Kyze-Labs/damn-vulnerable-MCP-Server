"""Challenge registry — loads all challenges from all difficulty levels."""

from .beginner.challenges import register_beginner_challenges
from .intermediate.challenges import register_intermediate_challenges
from .advanced.challenges import register_advanced_challenges
from .expert.challenges import register_expert_challenges


def load_all_challenges():
    register_beginner_challenges()
    register_intermediate_challenges()
    register_advanced_challenges()
    register_expert_challenges()
