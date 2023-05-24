import random
from typing import Any

from neighborly.components import Business, GameCharacter
from neighborly.core.ecs import Active
from neighborly.core.life_event import AllEvents
from neighborly.core.relationship import RelationshipManager, get_relationship
from neighborly.core.time import SimDateTime
from neighborly.systems import System

from speakeasy.components import Inventory, Knowledge, Produces


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
