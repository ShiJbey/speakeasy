import random
from typing import Any
from neighborly import ISystem
from neighborly.systems import System
from neighborly.core.time import SimDateTime
from neighborly.core.ecs import Active
from neighborly.components import GameCharacter, Business
from neighborly.core.life_event import AllEvents, RandomLifeEvent
from neighborly.core.relationship import RelationshipManager, get_relationship

from speakeasy.components import Inventory, Produces, Knowledge, Ethnicity, EthnicityValue
from speakeasy.events import GenerateKnowledgeEvent, get_associated_business, has_knowledge

from neighborly.decorators import system

class ProduceItemsSystem(System):

    sys_group = "early-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for _, (business, produces) in self.world.get_components(
            (Business, Produces)
        ):
            has_required_items = True

            # check for owner
            inventory = None
            if business.owner:
                inventory = self.world.get_gameobject(business.owner).get_component(Inventory)
            
            if not inventory:
                continue

            # Check if they have enough of the required items
            for item, quantity in produces.requires.items():
                if inventory.get_item(item) < quantity:
                    has_required_items = False
                    break

            if has_required_items is False:
                continue

            # Subtract required items from owners' inventory
            for item, quantity in produces.requires.items():
                inventory.remove_item(item, quantity)

            # Add produces items to owners' inventory
            for item, quantity in produces.produces.items():
                inventory.add_item(item, quantity)

class InitialInventorySystem(System):

    sys_group = "late-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for id, (_, inventory) in self.world.get_components(
            (GameCharacter, Inventory)
        ):
            character = self.world.get_gameobject(id)
            for i in range(character.world.get_resource(random.Random).randint(0,15)):
                inventory.add_item(character.world.get_resource(random.Random).choice(['booze','corn','money']), 1)

        self.world.remove_system(type(self))

class InitialEthnicitySystem(System):

    sys_group = "late-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for id, (_, ethnicity) in self.world.get_components(
            (GameCharacter, Ethnicity)
        ):
            if ethnicity.ethnicity == EthnicityValue.NotSpecified:
                i = self.world.get_resource(random.Random).randint(0, len(list(EthnicityValue))-1)
                ethnicity.ethnicity = list(EthnicityValue)[i]

        self.world.remove_system(type(self))

class ProbeRelationshipSystem(System):

    sys_group = "late-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for id, (_, _, _) in self.world.get_components(
            (GameCharacter, Active, RelationshipManager)
        ):
            for id2, (_, _, _) in self.world.get_components(
            (GameCharacter, Active, RelationshipManager)
            ):
                get_relationship(self.world.get_gameobject(id), self.world.get_gameobject(id2))

        self.world.remove_system(type(self))