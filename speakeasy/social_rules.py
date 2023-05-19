from typing import Dict, Type

from neighborly import GameObject
from neighborly.components import Virtues
from neighborly.core.relationship import RelationshipFacet, Romance, Friendship
from neighborly.utils.query import are_related
from neighborly.decorators import social_rule

from speakeasy.components import Ethnicity, Faction, Respect

@social_rule("Characters with the same ethnicity gain a boost in respect")
def respect_same_ethnicity(
    subject: GameObject,
    target: GameObject
) -> Dict[Type[RelationshipFacet], int]:
    """Characters with the same ethnicity gain a boost in respect"""

    if subject.has_component(Ethnicity) and target.has_component(Ethnicity):
        if subject.get_component(Ethnicity) == target.get_component(Ethnicity):
            return {Respect: 5}

    return {}

@social_rule("Characters with different ethnicities lose respect")
def disrespect_different_ethnicity(
    subject: GameObject,
    target: GameObject
) -> Dict[Type[RelationshipFacet], int]:
    """Characters with different ethnicities lose respect"""

    if subject.has_component(Ethnicity) and target.has_component(Ethnicity):
        if subject.get_component(Ethnicity) != target.get_component(Ethnicity):
            return {Respect: -5}

    return {}

@social_rule("Characters with the same faction gain a boost in respect")
def respect_same_faction(
    subject: GameObject,
    target: GameObject
) -> Dict[Type[RelationshipFacet], int]:
    """Characters with the same faction gain a boost in respect"""

    if subject.has_component(Faction) and target.has_component(Faction):
        if subject.get_component(Faction) == target.get_component(Faction):
            return {Respect: 5}

    return {}

@social_rule("Characters that are closely related gain a boost in respect")
def respect_for_family(
    subject: GameObject,
    target: GameObject
) -> Dict[Type[RelationshipFacet], int]:
    """Characters that are closely related gain a boost in respect"""

    if are_related(subject, target):
        return {Respect: 10}

    return {}

@social_rule("Characters with shared high/low virtues gain romance points")
def romance_boost_from_shared_virtues(
    subject: GameObject,
    target: GameObject
) -> Dict[Type[RelationshipFacet], int]:
    """Characters with shared high/low virtues gain romance points"""

    if not subject.has_component(Virtues) or not target.has_component(Virtues):
        return {}

    subject_virtues = subject.get_component(Virtues)
    target_virtues = target.get_component(Virtues)

    shared_likes = set(subject_virtues.get_high_values()).intersection(set(target_virtues.get_high_values()))
    shared_dislikes = set(subject_virtues.get_low_values()).intersection(set(target_virtues.get_low_values()))

    return {
        Romance: len(shared_likes) + len(shared_dislikes)
    }

@social_rule("Characters with shared high/low virtues gain romance points")
def romance_loss_from_virtue_conflicts(
    subject: GameObject,
    target: GameObject
) -> Dict[Type[RelationshipFacet], int]:
    """Characters with shared high/low virtues gain romance points"""

    if not subject.has_component(Virtues) or not target.has_component(Virtues):
        return {}

    subject_virtues = subject.get_component(Virtues)
    target_virtues = target.get_component(Virtues)

    subject_conflicts = set(subject_virtues.get_high_values()).intersection(set(target_virtues.get_low_values()))
    target_conflicts = set(target_virtues.get_high_values()).intersection(set(subject_virtues.get_low_values()))

    return {
        Romance: -1 * (len(subject_conflicts) + len(target_conflicts))
    }

@social_rule("Characters with more similar virtues will be better friends")
def friendship_virtue_compatibility(
    subject: GameObject,
    target: GameObject
) -> Dict[Type[RelationshipFacet], int]:
    """Characters with more similar virtues will be better friends"""

    if not subject.has_component(Virtues) or not target.has_component(Virtues):
        return {}

    character_virtues = subject.get_component(Virtues)
    acquaintance_virtues = target.get_component(Virtues)

    compatibility = float(character_virtues.compatibility(acquaintance_virtues)) / 100.0

    return {Friendship: round(6 * compatibility)}
