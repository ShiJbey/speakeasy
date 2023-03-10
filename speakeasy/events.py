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
from neighborly.content_management import (
    LifeEventLibrary
)
from neighborly.simulation import Neighborly, PluginInfo

############
# TODO: remove placeholders for new stuff
TRADE_EVENT_RESPECT_THRESHOLD = 1
GOOD_WORD_EVENT_RESPECT_THRESHOLD = 2
TELL_ABOUT_EVENT_RESPECT_THRESHOLD = 1
THEFT_EVENT_RESPECT_THRESHOLD = -5
HELP_EVENT_RESPECT_THRESHOLD = 5
#############

from speakeasy.components import Inventory, Knowledge, Respect, Favors

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

def has_knowledge(a: Knowledge, b: Business):
    return True in [b in i for i in list(a.produces.values())]

#learning that someone's biz produces an item
class LearnAboutEvent(ActionableLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        return {}

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #add the knowledge
        initiators_knowledge = initiator.get_component(Knowledge)
        others_biz = other.get_component(BusinessOwner).others_biz_own.business
        others_item = others_biz.produces()[0]
        initiators_knowledge.produces()[others_item].append(others_biz)

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            return None #prevents this from being initiated randomly

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        if candidate:
            candidate_bizown = candidate.get_component(BusinessOwner)
            if not candidate_bizown:
                return None

            initiator_knowledge = initiator.get_component(Knowledge)
            candidate_biz = candidate_bizown.business
            candidate_item = candidate_biz.produces()[0]

            if candidate_biz not in initiator_knowledge.produces()[candidate_item]:
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_component(BusinessOwner)
            ]

        matches: List[GameObject] = []

        #Prereq: don't already know
        for character in candidates:
            candidate_bizown = character.get_component(BusinessOwner)
            initiator_knowledge = initiator.get_component(Knowledge)
            candidate_biz = candidate_bizown.business
            candidate_item = candidate_biz.produces()[0]

            if candidate_biz not in initiator_knowledge.produces()[candidate_item]:
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

        initiators_item = initiator.get_component(BusinessOwner).business.produces()[0]
        others_item = other.get_component(BusinessOwner).business.produces()[0]

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
        initiators_biz = initiator.get_component(BusinessOwner).business
        others_biz = other.get_component(BusinessOwner).business
        initiators_item = initiators_biz.produces()[0]
        others_item = others_biz.produces()[0]

        others_inventory.remove(others_item)
        initiators_inventory.add(others_item)
        initiators_inventory.remove(initiators_item)
        others_inventory.add(initiators_item)

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

class GoodWordEvent(ActionableLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, subject: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other),  Role("Subject", subject)])

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        return {
            Role("Initiator", initiator) : [LoseRelationshipEffect(get_relationship(initiator, subject), Favors)],
            Role("Subject", subject) : [GainRelationshipEffect(get_relationship(other, subject), Respect)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        #add some respect
        get_relationship(other, subject).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to good word.', {Respect:1}))

        #remove some favor
        get_relationship(initiator, subject).get_component(Relationship).add_modifier(RelationshipModifier('Used up favor by putting in a good word.', {Favors:-1}))

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_subject(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        respect_threshold = GOOD_WORD_EVENT_RESPECT_THRESHOLD

        if candidate:
            if has_relationship(initiator, candidate):

                outgoing_relationship = get_relationship(initiator, candidate)
                outgoing_respect = outgoing_relationship.get_component(Respect).get_value()

                if outgoing_respect < GOOD_WORD_EVENT_RESPECT_THRESHOLD:
                    return None

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
            #prereq: initiator must respect subject
            respect = get_relationship(initiator, character).get_component(Relationship).get_component(Respect)
            if respect.get_value() >= respect_threshold:
                matches.append(character)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        respect_threshold = GOOD_WORD_EVENT_RESPECT_THRESHOLD

        if candidate:
            if has_relationship(
                candidate, initiator
            ):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        matches: List[GameObject] = []

        for character in candidates:
            #prereq: other must respect initiator
            respect = get_relationship(character, initiator).get_component(Relationship).get_component(Respect)
            if respect >= respect_threshold:
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

        subject = cls._bind_subject(world, initiator, bindings.get("Subject"))

        if subject is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get("Other"))

        if other is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other, subject)

class TellAboutEvent(ActionableLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, subject: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other),  Role("Subject", subject)])

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        subjects_item = subject.get_component(BusinessOwner).business.produces()[0]

        return {
            Role("Initiator", initiator) : [GainRelationshipEffect(get_relationship(other, initiator), Respect)],
            Role("Other", other) : [GainKnowledgeEffect(subjects_item)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        subjects_business = subject.get_component(BusinessOwner).business
        subjects_item = subjects_business.produces()[0]

        #add some knowledge
        other.get_component(Knowledge).produces()[subjects_item].append(subjects_business)

        #add some respect
        get_relationship(initiator, subject).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to getting information.', {Respect:1}))

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        respect_threshold = TELL_ABOUT_EVENT_RESPECT_THRESHOLD

        if candidate:
            if has_relationship(
                initiator, candidate
            ):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]

        matches: List[GameObject] = []

        for character in candidates:
            #prereq: initiator must respect other
            respect = get_relationship(initiator, character).get_component(Respect)
            if respect.get_value() >= respect_threshold:
                matches.append(character)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @staticmethod
    def _bind_subject(
        world: World, initiator: GameObject, other: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        if candidate:
            initiators_knowledge = initiator.get_component(Knowledge)
            others_knowledge = other.get_component(Knowledge)
            subjects_bizown = candidate.get_component(BusinessOwner)
            if not subjects_bizown:
                return None

            subject_biz = subjects_bizown.business

            if has_knowledge(initiators_knowledge, subject_biz) and not has_knowledge(others_knowledge, subject_biz):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = []
            initiators_knowledge = initiator.get_component(Knowledge)
            for entry in list(initiators_knowledge.produces().values()):
                candidates.extend(entry)

        matches: List[GameObject] = []

        for character in candidates:
            #prereq: inititator must have knowledge, other must not
            initiators_knowledge = initiator.get_component(Knowledge)
            others_knowledge = other.get_component(Knowledge)
            subjects_bizown = candidate.get_component(BusinessOwner)
            if not subjects_bizown:
                return None

            subject_biz = subjects_bizown.business

            if has_knowledge(initiators_knowledge, subject_biz) and not has_knowledge(others_knowledge, subject_biz):
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

        subject = cls._bind_subject(world, initiator, other, bindings.get("Subject"))

        if subject is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other, subject)

class TheftEvent(ActionableLifeEvent):

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

        others_item = other.get_component(BusinessOwner).business.produces()[0]

        return {
            Role("Initiator", initiator) : [GainItemEffect(others_item), LoseRelationshipEffect(get_relationship(other, initiator), Respect)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #move item between inventories
        initiators_inventory = initiator.get_component(Inventory)
        others_inventory = other.get_component(Inventory)
        others_biz = other.get_component(BusinessOwner).business
        others_item = others_biz.produces()[0]

        others_inventory.remove(others_item)
        initiators_inventory.add(others_item)

        #lose some respect
        get_relationship(initiator, other).get_component(Relationship).add_modifier(RelationshipModifier('Lost respect due to theft.', {Respect:-3}))

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active, Knowledge))
            ]

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        respect_threshold = THEFT_EVENT_RESPECT_THRESHOLD

        if candidate:
            if has_relationship(initiator, candidate):
                initiators_knowledge = initiator.get_component(Knowledge)
                outgoing_relationship = get_relationship(initiator, character)
                outgoing_respect = outgoing_relationship.get_component(Respect)

                characters_biz_owner = character.get_component(BusinessOwner)
                if characters_biz_owner is None:
                    return None
                
                characters_biz = characters_biz_owner.business

                if has_knowledge(initiators_knowledge, characters_biz) and outgoing_respect.get_value() <= respect_threshold:
                    candidates = [candidate]
            
            return None
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).targets()
            ]

        matches: List[GameObject] = []

        for character in candidates:
            #Prereq: other owns biz
            characters_biz_owner = character.get_component(BusinessOwner)

            if characters_biz_owner is None:
                continue

            characters_biz = characters_biz_owner.business

            #Prereq: initiator knowledge of biz
            initiators_knowledge = initiator.get_component(Knowledge)
            if not has_knowledge(initiators_knowledge, characters_biz):
              continue

            #Prereq: negative respect
            outgoing_relationship = get_relationship(initiator, character)
            outgoing_respect = outgoing_relationship.get_component(Respect)

            if outgoing_respect.get_value() <= respect_threshold:
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

class ExtortBusinessEvent(TheftEvent):
    pass

class GiveEvent(ActionableLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, item: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other), Role("Item", item)])

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]
        item = self["Item"]

        return {
            Role("Initiator", initiator) : [LoseItemEffect(item)],
            Role("Other", other)  : [GainItemEffect(item)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]
        item = self["Item"]

        #move item between inventories
        initiators_inventory = initiator.get_component(Inventory)
        others_inventory = other.get_component(Inventory)

        others_inventory.remove(item)
        initiators_inventory.add(item)


    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
            return world.get_resource(random.Random).choice(candidates)
        else:
            return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        if candidate and candidate != initiator:
            candidates = [candidate]
            return world.get_resource(random.Random).choice(candidates)
        else:
            return None
    
    def _bind_item(
        world: World, initiator: Optional[GameObject] = None, other: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        if initiator and other:
            initiator_inventory = initiator.get_component(Inventory)
            candidates = initiator_inventory.items()
            return world.get_resource(random.Random).choice(candidates)
        else:
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
        
        item = cls._bind_item(world, initiator, other)

        if item is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other, item)
    
class HelpWithRivalGangEvent(ActionableLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, item: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]

        return {
            Role("Initiator", initiator) : [GainRelationshipEffect(get_relationship(other, initiator), Favors), GainRelationshipEffect(get_relationship(other, initiator), Respect)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #add some respect
        get_relationship(other, initiator).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to help witha  rival gang.', {Respect:1}))

        #add a favor
        get_relationship(other, initiator).get_component(Relationship).add_modifier(RelationshipModifier('Owe a Favors due to getting help with a rival gang.', {Favors:1}))


    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
            return world.get_resource(random.Random).choice(candidates)
        else:
            candidates = [world.get_gameobject(c[0]) for c in world.get_components((GameCharacter, Active))]
            return world.get_resource(random.Random).choice(candidates)

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        respect_threshold = HELP_EVENT_RESPECT_THRESHOLD
        
        if candidate and has_relationship(initiator, candidate):
            candidates = [candidate]

            outgoing_relationship = get_relationship(initiator, candidate)
            outgoing_respect = outgoing_relationship.get_component(Respect).get_value()

            if outgoing_respect < HELP_EVENT_RESPECT_THRESHOLD:
                return None
            
            return world.get_resource(random.Random).choice(candidates)
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).targets()
            ]

        matches: List[GameObject] = []

        for character in candidates:
            #prereq: initiator must respect other
            respect = get_relationship(initiator, character).get_component(Respect)
            if respect.get_value() >= respect_threshold:
                matches.append(character)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None


    
    def _bind_item(
        world: World, initiator: Optional[GameObject] = None, other: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        if initiator and other:
            initiator_inventory = initiator.get_component(Inventory)
            candidates = initiator_inventory.items()
            return world.get_resource(random.Random).choice(candidates)
        else:
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
        
        item = cls._bind_item(world, initiator, other)

        if item is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other, item)

plugin_info = PluginInfo(
    name="speakeasy events plugin",
    plugin_id="speakeasy.life-events",
    version="0.1.0",
)

def setup(sim: Neighborly, **kwargs: Any):
    life_event_library = sim.world.get_resource(LifeEventLibrary)

    life_event_library.add(TradeEvent)
    life_event_library.add(GoodWordEvent)
    life_event_library.add(TheftEvent)
    life_event_library.add(HelpWithRivalGangEvent)
    life_event_library.add(GiveEvent)
    life_event_library.add(ExtortBusinessEvent)
    life_event_library.add(TellAboutEvent)
    life_event_library.add(LearnAboutEvent)