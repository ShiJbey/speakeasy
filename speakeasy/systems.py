from typing import Any

from neighborly.components import Business, GameCharacter
from neighborly.core.ecs import Active
from neighborly.core.life_event import AllEvents
from neighborly.core.relationship import RelationshipManager, get_relationship
from neighborly.core.time import SimDateTime
from neighborly.systems import System

from speakeasy.components import Inventory, Knowledge, Produces
from speakeasy.events import (
    GenerateKnowledgeEvent,
    get_associated_business,
    has_knowledge,
)


class ProduceItemsSystem(System):
    sys_group = "early-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for _, (business, produces) in self.world.get_components((Business, Produces)):
            has_required_items = True

            # check for owner
            inventory = None
            if business.owner:
                inventory = self.world.get_gameobject(business.owner).get_component(
                    Inventory
                )

            if not inventory:
                continue

            # Check if they have enough of the required items
            for item, quantity in produces.requires.items():
                if inventory.get_quantity(item) < quantity:
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


class GenerateSelfKnowledgeSystem(System):
    sys_group = "early-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for id, (_, _, knowledge) in self.world.get_components(
            (GameCharacter, Active, Knowledge)
        ):
            character = self.world.get_gameobject(id)
            biz = get_associated_business(character)
            if biz and not has_knowledge(knowledge, biz):
                learning_event = GenerateKnowledgeEvent(
                    self.world.get_resource(SimDateTime), character
                )
                self.world.get_resource(AllEvents).append(learning_event)
                learning_event.execute()


class ProbeRelationshipSystem(System):
    sys_group = "late-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for id, (_, _, _) in self.world.get_components(
            (GameCharacter, Active, RelationshipManager)
        ):
            for id2, (_, _, _) in self.world.get_components(
                (GameCharacter, Active, RelationshipManager)
            ):
                get_relationship(
                    self.world.get_gameobject(id), self.world.get_gameobject(id2)
                )

        self.world.remove_system(type(self))
