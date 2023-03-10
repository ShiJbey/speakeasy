from typing import Any
from neighborly.systems import System

from speakeasy.components import Inventory, Produces

class ProduceItemsSystem(System):

    sys_group = "early-update"

    def run(self, *args: Any, **kwargs: Any) -> None:
        for _, (inventory, produces) in self.world.get_components(
            (Inventory, Produces)
        ):
            has_required_items = True

            # Check if they have enough of the required items
            for item, quantity in produces.requires.items():
                if inventory.get_item(item) < quantity:
                    has_required_items = False
                    break

            if has_required_items is False:
                continue

            # Subtract required items from inventory
            for item, quantity in produces.requires.items():
                inventory.remove_item(item, quantity)

            # Add produces items to inventory
            for item, quantity in produces.produces.items():
                inventory.add_item(item, quantity)
