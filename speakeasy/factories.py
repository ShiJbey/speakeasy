import random
from typing import Any

from neighborly import IComponentFactory
from neighborly.core.ecs.ecs import World

from speakeasy.components import Ethnicity, EthnicityValue, Inventory


class InventoryFactory(IComponentFactory):
    def create(self, world: World, **kwargs: Any) -> Inventory:
        return Inventory()


class EthnicityFactory(IComponentFactory):
    def create(self, world: World, **kwargs: Any) -> Ethnicity:
        rng = world.get_resource(random.Random)
        return Ethnicity(rng.choice(sorted(list(EthnicityValue))))
