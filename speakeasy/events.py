import random
from typing import Any, Dict, Generator, List, Optional, Tuple
from neighborly.components.business import (
    Business,
    BusinessOwner,
    EmployeeOf
)
from neighborly.components.character import (
    GameCharacter,
)
from neighborly.core.ecs import GameObject, World
from neighborly.core.time import SimDateTime
from neighborly.components.shared import Active, Name
from neighborly.core.roles import Role, RoleList
from neighborly.core.life_event import ActionableLifeEvent, LifeEventBuffer
from neighborly.core.relationship import RelationshipFacet, Relationship, RelationshipModifier, RelationshipManager
from neighborly.utils.relationships import (
    get_relationship,
    has_relationship,
    get_relationships_with_statuses
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
NEGOTIATE_EVENT_RESPECT_THRESHOLD = -10
#############

from speakeasy.components import Inventory, Knowledge, Respect, Favors, Produces

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

# utility functions
def needs_item_from(a: Business, b: Inventory, r : random.Random):
    pro_a = a.gameobject.get_component(Produces)
    if True in [i in b.items for i in pro_a.requires]:
        items = [i for i in pro_a.requires if (i in b.items and b.items[i] > 0)]
        if items:
            return r.choice(items)
    return None

def has_knowledge(a: Knowledge, b: Business) -> bool:
    return True in [b.gameobject._id in i for i in list(a.produces.values())]

def get_associated_business(obj : GameObject) -> Business:
    bizown = None
    employed = []
    if obj.has_component(BusinessOwner):
        bizown = obj.get_component(BusinessOwner)
    if obj.has_component(RelationshipManager):
        employed = [obj.world.get_gameobject(rel.target()) for rel in get_relationships_with_statuses(obj, EmployeeOf)]
    associated_biz = None

    if len(employed) > 0:
        associated_biz = employed[0].get_component(Business)

    if bizown:
        associated_biz = obj.world.get_gameobject(bizown.business).get_component(Business)
    
    return associated_biz

#learning that someone's biz produces an item
class LearnAboutEvent(ActionableLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])
        self.business = None

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        return {}

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #add the knowledge
        initiators_knowledge = initiator.get_component(Knowledge)
        others_biz = get_associated_business(other)
        others_items = list(others_biz.gameobject.get_component(Produces).produces.keys())
        initiators_knowledge.add_producer(others_biz.gameobject._id, others_items[0])

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            return candidate
        else:
            return None #prevents this from being initiated randomly

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        if candidate:
            candidate_biz = get_associated_business(candidate)
            if not candidate_biz:
                return None

            initiator_knowledge = initiator.get_component(Knowledge)
            candidate_item = candidate_biz.produces[0]

            if candidate_biz not in initiator_knowledge.produces[candidate_item]:
                return candidate
            
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
        self, date: SimDateTime, initiator: GameObject, other: GameObject, initiators_item: str, others_item: str
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])
        self.initiators_item = initiators_item
        self.others_item = others_item

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]

        initiators_item = self.initiators_item
        others_item = self.others_item

        return {
            Role("Initiator", initiator) : [GainItemEffect(others_item), LoseItemEffect(initiators_item), GainRelationshipEffect(get_relationship(other, initiator), Respect)],
            Role("Other", other) : [GainItemEffect(initiators_item), LoseItemEffect(others_item), GainRelationshipEffect(get_relationship(initiator, other), Respect)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #swap items between inventories
        initiators_inventory = initiator.get_component(Inventory)
        others_inventory = other.get_component(Inventory)
        others_item = self.others_item
        initiators_item = self.initiators_item

        others_inventory.remove_item(others_item, 1)
        initiators_inventory.add_item(others_item, 1)
        initiators_inventory.remove_item(initiators_item, 1)
        others_inventory.add_item(initiators_item, 1)

        #add some mutual respect
        get_relationship(initiator, other).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to trade.', {Respect:1}))
        get_relationship(other, initiator).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to trade.', {Respect:1}))

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active, Inventory, Knowledge))
            ]

        matches = []

        #must know someone they respect
        for candidate in candidates:
            inventory = candidate.get_component(Inventory)
            if len(inventory.items) < 1:
                continue

            known_businesses = [world.get_gameobject(i) for i in candidate.get_component(Knowledge).known_producers()]

            known_business_associates = [world.get_gameobject(i.get_component(Business).owner) for i in known_businesses if i.get_component(Business).owner]

            known_business_employees = [world.get_gameobject(i.get_component(Business).get_employees()) for i in known_businesses if i.get_component(Business).get_employees()]

            for emps in known_business_employees:
                known_business_associates.extend(emps)

            known_business_relationships = [get_relationship(candidate, o) for o in known_business_associates]

            potential_offered_items = [i for i in inventory.items]

            #hold back anything required by my biz
            biz = get_associated_business(candidate)
            if biz:
                prod = biz.gameobject.get_component(Produces)
                potential_offered_items = [i for i in potential_offered_items if i not in prod.requires]

            if True in [r.get_component(Respect).get_value() > 0 for r in known_business_relationships] and len(potential_offered_items) > 0:
                matches.append((candidate, world.get_resource(random.Random).choice(potential_offered_items)))

        if matches:
            return world.get_resource(random.Random).choice(matches)

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
            if character == initiator:
                continue

            #Prereq: initiator need
            initiators_biz = get_associated_business(initiator)
            characters_inv = character.get_component(Inventory)
            
            if not initiators_biz:
                continue

            needed_item = needs_item_from(initiators_biz, characters_inv, world.get_resource(random.Random)) 
            if needed_item is None:
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

            matches.append((character, needed_item))

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: RoleList,
    ) -> Optional[ActionableLifeEvent]:

        initiator_tup = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator_tup is None:
            return None

        initiator, i_item = initiator_tup

        other_tup = cls._bind_other(world, initiator, bindings.get("Other"))

        if other_tup is None:
            return None

        other, o_item = other_tup
        return cls(world.get_resource(SimDateTime), initiator, other, i_item, o_item)
    
    def __str__(self) -> str:
        return f"{super().__str__()}, i_item={str(self.initiators_item)}, o_item={str(self.others_item)}"

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
            respect = get_relationship(initiator, character).get_component(Respect)
            if respect.get_value() >= respect_threshold:
                matches.append(character)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, subject: GameObject, candidate: Optional[GameObject] = None
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
            candidates = [c for c in candidates if c != initiator and c != subject]

        matches: List[GameObject] = []

        for character in candidates:
            #prereq: other must respect initiator
            respect = get_relationship(character, initiator).get_component(Respect).get_value()
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

        other = cls._bind_other(world, initiator, subject, bindings.get("Other"))

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

        subjects_item = list(get_associated_business(subject).gameobject.get_component(Produces).produces.keys())[0]

        return {
            Role("Initiator", initiator) : [GainRelationshipEffect(get_relationship(other, initiator), Respect)],
            Role("Other", other) : [GainKnowledgeEffect(subjects_item)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        subjects_business = get_associated_business(subject)
        #subjects_item = subjects_business.produces[0]

        #add some knowledge
        learning_event = LearnAboutEvent(initiator.world.get_resource(SimDateTime), other, subject)
        initiator.world.get_resource(LifeEventBuffer).append(learning_event)
        learning_event.execute()

        #other.get_component(Knowledge).produces[subjects_item].append(subjects_business)

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
                for result in world.get_components((GameCharacter, Active, Knowledge))
            ]

        matches = [c for c in candidates if len(c.get_component(Knowledge).produces.keys()) > 0]

        if matches:
            return world.get_resource(random.Random).choice(matches)

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
            all_candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).targets()
            ]
            #prereq: initiator must respect other
            candidates = []
            for character in all_candidates:
                respect = get_relationship(initiator, character).get_component(Respect)
                if respect.get_value() >= respect_threshold:
                    candidates.append(character)     

        matches: List[GameObject] = []

        for character in candidates:
             if character.has_component(Knowledge):
                
                #prepreq: initiator must know new business for other
                other_knowledge = character.get_component(Knowledge)
                
                known_businesses = initiator.get_component(Knowledge).known_producers()
                other_known_businesses = other_knowledge.known_producers()

                if False in [b in other_known_businesses for b in known_businesses]:
                    matches.append(character)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @staticmethod
    def _bind_subject(
        world: World, initiator: GameObject, other: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        initiators_known_bizs = initiator.get_component(Knowledge).known_producers()
        others_known_bizs = other.get_component(Knowledge).known_producers()

        if candidate:
            biz = get_associated_business(candidate)
            if biz:
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [world.get_gameobject(i) for i in initiators_known_bizs]
            candidates = [b.get_component(Business) for b in candidates if b._id not in others_known_bizs]
            candidates = [world.get_gameobject(b.owner) for b in candidates if b.owner]

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

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

#robbing a BUSINESS
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

        others_item = list(other.get_component(Inventory).items)[0]

        return {
            Role("Initiator", initiator) : [GainItemEffect(others_item), LoseRelationshipEffect(get_relationship(other, initiator), Respect)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #move item between inventories
        initiators_inventory = initiator.get_component(Inventory)
        #others_inventory = other.get_component(Inventory)
        others_biz = get_associated_business(other)
        others_item = list(others_biz.gameobject.get_component(Produces).produces)[0]

        #others_inventory.remove_item(others_item, 1)
        initiators_inventory.add_item(others_item, 1)

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

        matches = []
        
        #initiator must disrespect someonethey know
        for candidate in candidates:


            known_businesses = [world.get_gameobject(i) for i in candidate.get_component(Knowledge).known_producers()]

            known_business_associates = [world.get_gameobject(i.get_component(Business).owner) for i in known_businesses if i.get_component(Business).owner]

            known_business_employees = [world.get_gameobject(i.get_component(Business).get_employees()) for i in known_businesses if i.get_component(Business).get_employees()]

            for emps in known_business_employees:
                known_business_associates.extend(emps)

            known_business_relationships = [get_relationship(candidate, o) for o in known_business_associates]

            if True in [r.get_component(Respect).get_value() < 0 for r in known_business_relationships]:
                matches.append(candidate)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        respect_threshold = THEFT_EVENT_RESPECT_THRESHOLD

        if candidate:
            if has_relationship(initiator, candidate):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(Knowledge).known_producers()
            ]

        matches: List[GameObject] = []

        for character in candidates:
            #Prereq: other is associated with biz
            characters_biz = get_associated_business(character)
            if not characters_biz:
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
            #print("no init")
            return None

        other = cls._bind_other(world, initiator, bindings.get("Other"))

        if other is None:
            #print("no victim")
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
        item = self["Item"].get_component(Name).value

        #move item between inventories
        initiators_inventory = initiator.get_component(Inventory)
        others_inventory = other.get_component(Inventory)

        initiators_inventory.remove_item(item, 1)
        others_inventory.add_item(item, 1)


    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            if candidate.has_component(Inventory):
                return candidate
            return None
        else:
            return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        if candidate and candidate != initiator:
            if candidate.has_component(Inventory):
                return candidate
            return None
        else:
            return None
    
    def _bind_item(
        world: World, initiator: Optional[GameObject] = None, other: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        if initiator and other:
            initiator_inventory = initiator.get_component(Inventory)
            candidates = [world.spawn_gameobject([Name(item)], item) for item in list(initiator_inventory.items)] #needed to spawn to put item in role list but, creates waste?
            if len(candidates) < 1:
                return None
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
        self, date: SimDateTime, initiator: GameObject, other: GameObject
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
        else:
            candidates = [world.get_gameobject(c[0]) for c in world.get_components((GameCharacter, Active))]
        return world.get_resource(random.Random).choice(candidates)

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        
        respect_threshold = HELP_EVENT_RESPECT_THRESHOLD
        
        if candidate:
            if has_relationship(initiator, candidate):
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
            #prereq: initiator must respect other
            respect = get_relationship(initiator, character).get_component(Respect)
            if respect.get_value() >= respect_threshold:
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

class GenerateKnowledgeEvent(ActionableLifeEvent):
    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator)])

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        return {}
    
    def execute(self) -> None:
        initiator = self["Initiator"]

        #add knowledge
        learning_event = LearnAboutEvent(initiator.world.get_resource(SimDateTime), initiator, initiator)
        initiator.world.get_resource(LifeEventBuffer).append(learning_event)
        learning_event.execute()

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            if candidate.has_component(Knowledge):
                candidates = [candidate]
            else:
                return None
        else:
            candidates = [world.get_gameobject(c[0]) for c in world.get_components((GameCharacter, Active, Knowledge))]

        matches = []

        for candidate in candidates:
            candidates_biz = get_associated_business(candidate)
            if candidates_biz:
                if not has_knowledge(candidate.get_component(Knowledge), candidates_biz):
                    matches.append(candidate)

        if matches:
            world.get_resource(random.Random).choice(matches)
        
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

        return cls(world.get_resource(SimDateTime), initiator)

class NegotiateEvent(ActionableLifeEvent):

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

        return {
            Role("Initiator", initiator) : [],
            Role("Other", other) : []
        }

    def execute(self) -> None:
        from speakeasy.negotiation.neighborly_classes import NegotiationState, NeighborlyNegotiator, negotiate
        
        initiator = self["Initiator"]
        other = self["Other"]

        #run negotiation
        negotiator = NeighborlyNegotiator( initiator.get_component(GameCharacter).full_name, initiator )
        partner = NeighborlyNegotiator( other.get_component(GameCharacter).full_name, other )
        state = NegotiationState(negotiator.agent, partner.agent, None)

        negotiator.negotiation_state = state
        partner.negotiation_state = state

        options = negotiator.agent.generate_starting_possible_actions()
        thing_to_ask_for = random.choice(options)
        state.setup_initial_ask(thing_to_ask_for)
        print(f'Running negotiation between {negotiator.name} and {partner.name}:')
        agreement = negotiate(negotiator.agent, partner.agent, thing_to_ask_for)

        #trigger each event from the agreed upon package
        for item in agreement:
            triggered_event = item.val
            initiator.world.get_resource(LifeEventBuffer).append(triggered_event)
            triggered_event.execute()

            #add some mutual respect
            get_relationship(initiator, other).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to successful negotiation.', {Respect:1}))
            get_relationship(other, initiator).get_component(Relationship).add_modifier(RelationshipModifier('Gained respect due to successful negotiation.', {Respect:1}))

        if len(agreement) == 0:
            #lose some mutual respect
            get_relationship(initiator, other).get_component(Relationship).add_modifier(RelationshipModifier('Lost respect due to failed negotiation.', {Respect:-1}))
            get_relationship(other, initiator).get_component(Relationship).add_modifier(RelationshipModifier('Lost respect due to failed negotiation.', {Respect:-1}))

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        if candidate:
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active, Inventory, Knowledge))
            ]

        matches = []

        #no prereqs
        for candidate in candidates:
            matches.append(candidate)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @staticmethod
    def _bind_other(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        respect_threshold = NEGOTIATE_EVENT_RESPECT_THRESHOLD

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
            if character == initiator:
                continue

            #Prereq: mutual respect
            outgoing_relationship = get_relationship(initiator, character)
            outgoing_respect = outgoing_relationship.get_component(Respect)

            if outgoing_respect.get_value() < respect_threshold:
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
    
    def __str__(self) -> str:
        return f"{super().__str__()}"

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
    life_event_library.add(GenerateKnowledgeEvent)
    life_event_library.add(NegotiateEvent)