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
from neighborly import NeighborlyConfig
from neighborly.core.ecs import GameObject, World, Active
from neighborly.core.time import SimDateTime
from neighborly.components.shared import Name
from neighborly.core.roles import Role, RoleList
from neighborly.core.life_event import RandomLifeEvent, AllEvents, EventHistory
from neighborly.core.relationship import RelationshipFacet, Relationship, RelationshipModifier, RelationshipManager
from neighborly.core.relationship import (
    get_relationship,
    get_relationships_with_statuses
)
from neighborly.components.character import Family
from neighborly.decorators import random_life_event

from speakeasy.negotiation.core import NegotiationState, print_negotiation_trace, ResponseCategory

############
# TODO: remove placeholders for new stuff
TRADE_EVENT_RESPECT_THRESHOLD = 5
GOOD_WORD_EVENT_RESPECT_THRESHOLD = 5
TELL_ABOUT_EVENT_RESPECT_THRESHOLD = 10
THEFT_EVENT_RESPECT_THRESHOLD = -4
HELP_EVENT_RESPECT_THRESHOLD = 12
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

class TriggerEventEffect:
    def __init__(self, triggered_event_class) -> None:
        self.triggered_event_class = triggered_event_class

# utility functions
def needs_item_from(a: Business, b: Inventory, r : random.Random):
    pro_a = a.gameobject.get_component(Produces)
    if True in [i in b.items for i in pro_a.requires]:
        items = [i for i in pro_a.requires if (i in b.items and b.items[i] > 0)]
        if items:
            return r.choice(items)
    return None

def has_knowledge(a: Knowledge, b: Business) -> bool:
    return True in [b.gameobject.uid in i for i in list(a.produces.values())]

def get_associated_business(obj : GameObject) -> Business:
    bizown = None
    employed = []
    if obj.has_component(BusinessOwner):
        bizown = obj.get_component(BusinessOwner)
    if obj.has_component(RelationshipManager):
        employed = [obj.world.get_gameobject(rel.get_component(Relationship).target) for rel in get_relationships_with_statuses(obj, EmployeeOf)]
    associated_biz = None

    if len(employed) > 0:
        associated_biz = obj.world.get_gameobject(employed[0].get_component(BusinessOwner).business).get_component(Business)

    if bizown:
        associated_biz = obj.world.get_gameobject(bizown.business).get_component(Business)

    return associated_biz

#learning that someone's biz produces an item
@random_life_event()
class LearnAboutEvent(RandomLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])
        self.business = None

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
        return 1

    def get_effects(self):
        return {
            Role("Initiator", self["Initiator"]) : [GainKnowledgeEffect(None)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #add the knowledge
        initiators_knowledge = initiator.get_component(Knowledge)
        others_biz = get_associated_business(other)
        others_items = list(others_biz.gameobject.get_component(Produces).produces.keys())
        initiators_knowledge.add_producer(others_biz.gameobject.uid, others_items[0])
        initiator.world.get_resource(AllEvents).append(self)

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
    ) -> Optional[RandomLifeEvent]:

        initiator = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get("Other"))

        if other is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other)

# First pass at a trading event
@random_life_event()
class TradeEvent(RandomLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, initiators_item: str, others_item: str
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])
        self.initiators_item = initiators_item
        self.others_item = others_item

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
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
        get_relationship(initiator, other).get_component(Respect).increment(1)
        get_relationship(other, initiator).get_component(Respect).increment(1)

        if event_history := initiator.try_component(EventHistory):
            event_history.append(self)
        initiator.world.get_resource(AllEvents).append(self)

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

            candidate_biz = get_associated_business(candidate)
            if not candidate_biz:
                continue

            known_businesses = [world.get_gameobject(i) for i in candidate.get_component(Knowledge).known_producers()]

            known_business_associates = [world.get_gameobject(i.get_component(Business).owner) for i in known_businesses if i.get_component(Business).owner]

            known_business_employees = [[world.get_gameobject(e) for e in biz.get_component(Business).get_employees()] for biz in known_businesses if biz.get_component(Business).get_employees()]

            for emps in known_business_employees:
                known_business_associates.extend(emps)

            known_business_relationships = [get_relationship(candidate, o) for o in known_business_associates]
            #print("MY relationships wit them:", [r.get_component(Respect).get_value() for r in known_business_relationships])

            potential_offered_items = [i for i in inventory.items]

            #hold back anything required by my biz
            biz = get_associated_business(candidate)
            if biz:
                prod = biz.gameobject.get_component(Produces)
                potential_offered_items = [i for i in potential_offered_items if i not in prod.requires]

            if True in [r.get_component(Respect).get_value() > TRADE_EVENT_RESPECT_THRESHOLD for r in known_business_relationships] and len(potential_offered_items) > 0:
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
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).outgoing.keys()
            ]

        matches: List[GameObject] = []

        for character in candidates:
            if character == initiator:
                continue

            #Prereq: initiator need
            initiators_biz = get_associated_business(initiator)
            characters_inv = character.get_component(Inventory)

            needed_item = needs_item_from(initiators_biz, characters_inv, world.get_resource(random.Random))
            if needed_item is None:
                #print('init needs nothing from other?')
                continue

            #Prereq: mutual respect
            outgoing_relationship = get_relationship(initiator, character)
            incoming_relationship = get_relationship(character, initiator)

            outgoing_respect = outgoing_relationship.get_component(Respect)
            incoming_respect = incoming_relationship.get_component(Respect)

            if outgoing_respect.get_value() < respect_threshold or incoming_respect.get_value() < respect_threshold:
                #print('init and other dont mutually respect weach other?')
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
    ) -> Optional[RandomLifeEvent]:

        initiator_tup = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator_tup is None:
            #print("trade failed on initiator_tup")
            return None

        initiator, i_item = initiator_tup

        other_tup = cls._bind_other(world, initiator, bindings.get("Other"))

        if other_tup is None:
            #print("trade failed on other_tup")
            return None

        other, o_item = other_tup
        return cls(world.get_resource(SimDateTime), initiator, other, i_item, o_item)

    def __str__(self) -> str:
        return f"{super().__str__()}, i_item={str(self.initiators_item)}, o_item={str(self.others_item)}"

@random_life_event()
class GoodWordEvent(RandomLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, subject: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other),  Role("Subject", subject)])

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        return {
            Role("Initiator", initiator) : [LoseRelationshipEffect(get_relationship(initiator, subject), Favors)],#, LoseRelationshipEffect(get_relationship(other, initiator), Respect)
            Role("Subject", subject) : [GainRelationshipEffect(get_relationship(other, subject), Respect), GainRelationshipEffect(get_relationship(subject, initiator), Favors)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        favors_sub_owes_init_DISCOURAGING = get_relationship(subject, initiator).get_component(Favors).favors
        favors_init_owed_sub_ENCOURAGING = get_relationship(initiator, subject).get_component(Favors).favors
        #print(f"Prior, SUB now owes INIT: {favors_sub_owes_init_DISCOURAGING} + 1, and INIT ALREADY OWED SUB {favors_init_owed_sub_ENCOURAGING} (-1)?")

        #add some respect
        get_relationship(other, subject).get_component(Respect).increment(1)

        #remove some favor, or add if there wasn't a favor owed.
        if (favors_init_owed_sub_ENCOURAGING > 0):
            get_relationship(initiator, subject).get_component(Favors).favors -= 1
        else:
            get_relationship(subject, initiator).get_component(Favors).favors += 1

        favors_sub_owes_init_DISCOURAGING = get_relationship(subject, initiator).get_component(Favors).favors
        favors_init_owed_sub_ENCOURAGING = get_relationship(initiator, subject).get_component(Favors).favors
        #print(f"{initiator.name} puts in a good word with {other.name} about {subject.name}, bringing total favors owed by {subject.name} to {initiator.name} to: {favors_sub_owes_init_DISCOURAGING}")
        #print(f"After, SUB now owes INIT: {favors_sub_owes_init_DISCOURAGING} + 1, and INIT ALREADY OWED SUB {favors_init_owed_sub_ENCOURAGING} (-1)?")

        if event_history := initiator.try_component(EventHistory):
            event_history.append(self)
        initiator.world.get_resource(AllEvents).append(self)

    @staticmethod
    def _bind_initiator(
        world: World, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:
        apply_threshold = True

        if candidate:
            candidates = [candidate]
            apply_threshold = False
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active, RelationshipManager))
            ]

        #initiator must respect someone... who respects them
        matches = []
        for character in candidates:
            people_they_respect = [world.get_gameobject(r).get_component(Relationship).target for r in character.get_component(RelationshipManager).outgoing.values() 
                                        if (world.get_gameobject(r).get_component(Respect).get_value() >= GOOD_WORD_EVENT_RESPECT_THRESHOLD
                                        or not apply_threshold)
                                    ]
            if len(people_they_respect) < 1:
                continue

            people_mutually_respected = [world.get_gameobject(target) for target in people_they_respect 
                                            if (get_relationship(world.get_gameobject(target), character).get_component(Respect).get_value() >= GOOD_WORD_EVENT_RESPECT_THRESHOLD
                                            or not apply_threshold)
                                        ]
            if len(people_mutually_respected) < 1:
                continue

            matches.append(character)

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @staticmethod
    def _bind_subject(
        world: World, initiator: GameObject, candidate: Optional[GameObject] = None
    ) -> Optional[GameObject]:

        respect_threshold = GOOD_WORD_EVENT_RESPECT_THRESHOLD
        apply_threshold = True

        if candidate:
            candidates = [candidate]
            apply_threshold = False
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).outgoing.keys()
            ]

        matches: List[GameObject] = []

        for character in candidates:
            #prereq: initiator must respect subject
            respect = get_relationship(initiator, character).get_component(Respect)
            if respect.get_value() >= respect_threshold or not apply_threshold:
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
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(result[0])
                for result in world.get_components((GameCharacter, Active))
            ]
            candidates = [c for c in candidates if c != initiator and c != subject]

        matches: List[GameObject] = []

        for character in candidates:
            if character == subject:
                continue

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
    ) -> Optional[RandomLifeEvent]:

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

@random_life_event()
class TellAboutEvent(RandomLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, subject: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other),  Role("Subject", subject)])

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]
        subject = self["Subject"]

        subjects_item = list(get_associated_business(subject).gameobject.get_component(Produces).produces.keys())[0]

        return {
            Role("Initiator", initiator) : [GainRelationshipEffect(get_relationship(other, initiator), Respect), LoseRelationshipEffect(get_relationship(subject, initiator), Respect)],
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
        initiator.world.get_resource(AllEvents).append(learning_event)
        learning_event.execute()

        #other.get_component(Knowledge).produces[subjects_item].append(subjects_business)

        #add some respect
        get_relationship(initiator, subject).get_component(Respect).increment(1)

        if event_history := initiator.try_component(EventHistory):
            event_history.append(self)
        initiator.world.get_resource(AllEvents).append(self)

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
            candidates = [candidate]
        else:
            all_candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).outgoing.keys()
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
            candidates = [b.get_component(Business) for b in candidates if b.uid not in others_known_bizs]
            candidates = [world.get_gameobject(b.owner) for b in candidates if b.owner]

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: RoleList,
    ) -> Optional[RandomLifeEvent]:

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
@random_life_event()
class TheftEvent(RandomLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
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
        others_owner = initiator.world.get_gameobject(other.get_component(Business).owner)
        others_inventory = others_owner.get_component(Inventory)

        for stolen_item_idx in range(initiator.world.get_resource(random.Random).randint(1,5)):
            if len([item for item in others_inventory.items if others_inventory.items[item]>0]) < 1:
                continue

            others_item = initiator.world.get_resource(random.Random).choice([item for item in others_inventory.items if others_inventory.items[item]>0])
            others_inventory.remove_item(others_item, 1)
            initiators_inventory.add_item(others_item, 1)

            #lose some respect
            get_relationship(others_owner, initiator).get_component(Respect).increment(-3)

        if event_history := initiator.try_component(EventHistory):
            event_history.append(self)
        initiator.world.get_resource(AllEvents).append(self)

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

            known_businesses = [world.get_gameobject(i) for i in candidate.get_component(Knowledge).known_producers() if world.get_gameobject(i).has_component(Active) and world.get_gameobject(i).get_component(Business).owner]
            #print(f"I know {len(known_businesses)} biz's")

            known_business_associates = [(world.get_gameobject(i.get_component(Business).owner),i) for i in known_businesses if i.get_component(Business).owner]
            #print(f"It has {len(known_business_associates)} owners")
            known_business_employees = [[(world.get_gameobject(emp), biz_object) for emp in biz_object.get_component(Business).get_employees()] for biz_object in known_businesses if biz_object.get_component(Business).get_employees()]
            #print(f"It has {len(known_business_employees)} employees")

            for emps in known_business_employees:
                known_business_associates.extend(emps)

            known_business_relationships = [(get_relationship(candidate, pair[0]), pair[1]) for pair in known_business_associates]
            #print("My relatioships with them: ", [r.get_component(Respect).get_value() for r in known_business_relationships])

            #print("ALL my relationships: ", [candidate.world.get_gameobject(r_id).get_component(Respect).get_value() for r_id in candidate.get_component(RelationshipManager).outgoing.values()])

            if True in [pair[0].get_component(Respect).get_value() < THEFT_EVENT_RESPECT_THRESHOLD for pair in known_business_relationships]:
                victim = world.get_resource(random.Random).choice([pair[1] for pair in known_business_relationships if pair[0].get_component(Respect).get_value() < THEFT_EVENT_RESPECT_THRESHOLD])
                matches.append((candidate, victim))
                #print('chose a victim and candidate.')

        if matches:
            return world.get_resource(random.Random).choice(matches)

        return None

    @classmethod
    def instantiate(
        cls,
        world: World,
        bindings: RoleList,
    ) -> Optional[RandomLifeEvent]:

        initiator_tup = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator_tup is None:
            #print("theft failed on initiator")
            return None

        initiator, other = initiator_tup

        if other is None:
            #print("theft failed on other")
            return None

        return cls(world.get_resource(SimDateTime), initiator, other)

    def __str__(self) -> str:
        return f"{super().__str__()}"

#@random_life_event()
#class ExtortBusinessEvent(TheftEvent):
#    pass

@random_life_event()
class GiveEvent(RandomLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject, item: str
    ) -> None:
        self.item = item
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]

        return {
            Role("Initiator", initiator) : [LoseItemEffect(self.item)],
            Role("Other", other)  : [GainItemEffect(self.item)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #move item between inventories
        initiators_inventory = initiator.get_component(Inventory)
        others_inventory = other.get_component(Inventory)

        initiators_inventory.remove_item(self.item, 1)
        others_inventory.add_item(self.item, 1)

        initiator.world.get_resource(AllEvents).append(self)


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
            candidates = [item for item in list(initiator_inventory.items)] #needed to spawn to put item in role list but, creates waste?
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
    ) -> Optional[RandomLifeEvent]:

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
    
    def __str__(self) -> str:
        return f"{super().__str__()}, Item: {self.item}"

@random_life_event()
class HelpWithRivalGangEvent(RandomLifeEvent):

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
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

        #add some respect from other and their fam
        get_relationship(other, initiator).get_component(Respect).increment(2) 
        others_fam = [obj.get_component(Relationship).target for obj in get_relationships_with_statuses(other, Family)]
        for fam in others_fam:
            get_relationship(initiator.world.get_gameobject(fam), initiator).get_component(Respect).increment(1) 

        #add a favor from other
        get_relationship(other, initiator).get_component(Favors).favors += 1

        if event_history := initiator.try_component(EventHistory):
            event_history.append(self)
        initiator.world.get_resource(AllEvents).append(self)

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
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).outgoing.keys()
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
    ) -> Optional[RandomLifeEvent]:

        initiator = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get("Other"))

        if other is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other)

    def __str__(self) -> str:
        return f"{super().__str__()}"

@random_life_event()
class GenerateKnowledgeEvent(RandomLifeEvent):
    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator)])

    def get_priority(self) -> float:
        return 1

    def get_effects(self):
        return {}

    def get_probability(self) -> float:
        return 1

    def execute(self) -> None:
        initiator = self["Initiator"]

        #add knowledge
        learning_event = LearnAboutEvent(initiator.world.get_resource(SimDateTime), initiator, initiator)
        initiator.world.get_resource(AllEvents).append(learning_event)
        learning_event.execute()
        initiator.world.get_resource(AllEvents).append(self)

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
    ) -> Optional[RandomLifeEvent]:

        initiator = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator)

@random_life_event()
class NegotiateEvent(RandomLifeEvent):
    from speakeasy.negotiation.core import get_initial_ask_options, negotiate
    from speakeasy.negotiation.neighborly_classes import NeighborlyNegotiator

    initiator = "Initiator"

    def __init__(
        self, date: SimDateTime, initiator: GameObject, other: GameObject
    ) -> None:
        super().__init__(date, [Role("Initiator", initiator), Role("Other", other)])
        self.trace = ""
        self.agreement = []

    def get_priority(self) -> float:
        return 1

    def get_probability(self) -> float:
        return 1

    def get_effects(self):
        initiator = self["Initiator"]
        other = self["Other"]

        return {
            Role("Initiator", initiator) : [GainRelationshipEffect(get_relationship(initiator, other), Respect), GainRelationshipEffect(get_relationship(other, initiator), Respect)],
            Role("Other", other) : [GainRelationshipEffect(get_relationship(initiator, other), Respect), GainRelationshipEffect(get_relationship(other, initiator), Respect)]
        }

    def execute(self) -> None:
        initiator = self["Initiator"]
        other = self["Other"]

        #run negotiation
        negotiator = NegotiateEvent.NeighborlyNegotiator( initiator.get_component(GameCharacter).full_name, initiator , initiator.world.get_resource(random.Random))
        partner = NegotiateEvent.NeighborlyNegotiator( other.get_component(GameCharacter).full_name, other, initiator.world.get_resource(random.Random) )
        options = NegotiateEvent.get_initial_ask_options(negotiator, partner)
        if len(options) < 1:
            return
        thing_to_ask_for = initiator.world.get_resource(random.Random).choice(options)

        print(f'Running negotiation between {negotiator.name} and {partner.name}:')
        print(f'{negotiator.name}:{negotiator.gameObject.get_component(Inventory).items}\n{partner.name}:{partner.gameObject.get_component(Inventory).items}')
        self.agreement, self.trace = NegotiateEvent.negotiate(negotiator, partner, thing_to_ask_for)

        #trigger each event from the agreed upon package
        for item in self.agreement:
            triggered_event = item.val
            initiator.world.get_resource(AllEvents).append(triggered_event)
            triggered_event.execute()

            #add some mutual respect
            get_relationship(initiator, other).get_component(Respect).increment(1)
            get_relationship(other, initiator).get_component(Respect).increment(1)

        if len(self.agreement) == 0:
            #lose some mutual respect
            get_relationship(initiator, other).get_component(Respect).increment(-1)
            get_relationship(other, initiator).get_component(Respect).increment(-1)

        if event_history := initiator.try_component(EventHistory):
            event_history.append(self)
        initiator.world.get_resource(AllEvents).append(self)

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
            candidates = [candidate]
        else:
            candidates = [
                world.get_gameobject(c)
                for c in initiator.get_component(RelationshipManager).outgoing.keys()
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

            #prereq: something to ask for
            negotiator = NegotiateEvent.NeighborlyNegotiator( initiator.get_component(GameCharacter).full_name, initiator, initiator.world.get_resource(random.Random))
            partner = NegotiateEvent.NeighborlyNegotiator( character.get_component(GameCharacter).full_name, character, initiator.world.get_resource(random.Random))
            options = NegotiateEvent.get_initial_ask_options(negotiator, partner)
            if len(options) < 1:
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
    ) -> Optional[RandomLifeEvent]:
        #make negotiation toggled in config
        if not world.get_resource(NeighborlyConfig).settings.get('enable_negotiation', True):
            print("Skipped Negotiation as it's disabled.")
            return None

        initiator = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator is None:
            return None

        other = cls._bind_other(world, initiator, bindings.get("Other"))

        if other is None:
            return None

        return cls(world.get_resource(SimDateTime), initiator, other)

    def __str__(self) -> str:
        return f"{super().__str__()} + {self.trace}"
