import random
from typing import Any, Dict, Generator, List, Optional, Tuple
from neighborly.components.business import (
    Business,
    BusinessOwner,
)
from neighborly.components.character import (
    GameCharacter,
)
from neighborly.core.ecs import GameObject, World
from neighborly.core.time import SimDateTime
from neighborly.components.shared import Active
from neighborly.core.roles import Role, RoleList
from neighborly.core.life_event import ActionableLifeEvent, LifeEventBuffer
from neighborly.core.relationship import RelationshipFacet, Relationship, RelationshipModifier, RelationshipManager
from neighborly.utils.relationships import (
    get_relationship,
    has_relationship,
)

############
# TODO: remove placeholders for new stuff
class Respect(RelationshipFacet):
    pass
class Favor(RelationshipFacet):
    pass
from neighborly.core.ecs import Component
class Inventory(Component):
    pass
class Knowledge(Component):
    pass
TRADE_EVENT_RESPECT_THRESHOLD = 1
#############

# Classes for the different effects map entries
class GainItemEffect:
    def __init__(self, item) -> None:
        self.item = item

class LoseItemEffect:
    def __init__(self, item) -> None:
        self.item = item

class GainRelationshipEffect:
    def __init__(self, relationship: Relationship, facet: RelationshipFacet) -> None:
        self.relationship = relationship
        self.facet = facet

class LoseRelationshipEffect:
    def __init__(self, relationship: Relationship, facet: RelationshipFacet) -> None:
        self.relationship = relationship
        self.facet = facet

class GainKnowledgeEffect:
    def __init__(self, item) -> None:
        self.item = item

# utility fucntion
def needs_item_from(a: Business, b: Business):
    return True in [i in b.produces() for i in a.requires()]

# placeholder for future event
class LearnAboutEvent(ActionableLifeEvent):
    pass

# First pass at a trading event
class TradeEvent(ActionableLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])

    def get_priority(self) -> float:
        return 1
    
    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]

        initiators_item = initiator.get_component(Business).produces()[0]
        others_item = other.get_component(Business).produces()[0]

        return {
            Role("Initiator", initiator) : [GainItemEffect(others_item), LoseItemEffect(initiators_item), GainRelationshipEffect(get_relationship(other, initiator), Respect)],
            Role("Other", other) : [GainItemEffect(initiators_item), LoseItemEffect(others_item), GainRelationshipEffect(get_relationship(initiator, other), Respect), GainKnowledgeEffect(initiators_item)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #swap items between inventories
        initiators_inventory = initiator.get_component(Inventory)
        others_inventory = other.get_component(Inventory)
        initiators_biz = initiator.get_component(Business)
        others_biz = other.get_component(Business)
        initiators_item = initiators_biz.produces()[0]
        others_item = others_biz.produces()[0]

        others_inventory.remove(others_item)
        initiators_inventory.add(others_item)
        initiators_inventory.remove(initiators_item)
        initiators_inventory.add(initiators_item)

        #add some mutual respect
        get_relationship(initiator, other).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to trade.', {Respect:1}))
        get_relationship(other, initiator).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to trade.', {Respect:1}))

        #trigger a learning event
        if initiators_biz not in other.get_component(Knowledge).produces()[initiators_item]:
          world = initiator.world
          learning_event = LearnAboutEvent(world.get_resource(SimDateTime), other, initiator)
          world.get_resource(LifeEventBuffer).append(learning_event)
          learning_event.execute()

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active, BusinessOwner, Knowledge))
            ]

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        respect_threshold = TRADE_EVENT_RESPECT_THRESHOLD

        if candidate:
            if has_relationship(initiator, candidate) and has_relationship(
                candidate, initiator
            ):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).targets()
            ]

        matches: List[GameObject] = []

        for character in candidates:
            #Prereq: initiator need
            characters_biz_owner = character.get_component(BusinessOwner)

            if characters_biz_owner is None:
                continue
            
            initiators_biz = initiator.get_component(BusinessOwner).business
            characters_biz = characters_biz_owner.business

            if not needs_item_from(initiators_biz, characters_biz):
              continue

            #Prereq: initiator knowledge
            initiators_knowledge = initiator.get_component(Knowledge)
            if not characters_biz in initiators_knowledge.produces[initiators_biz.requires()[0]]:
              continue

            #Prereq: mutual respect
            outgoing_relationship = get_relationship(initiator, character)
            
            if not has_relationship(character, initiator):
                continue
            incoming_relationship = get_relationship(character, initiator)

            outgoing_respect = outgoing_relationship.get_component(Respect)
            incoming_respect = incoming_relationship.get_component(Respect)

            if outgoing_respect.get_value() < respect_threshold or incoming_respect.get_value() < respect_threshold:
                continue

            matches.append(character)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: RoleList,
    ) -> Optional[ActionableLifeEvent]:

        initiator = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get("Other"))

        if other is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other)