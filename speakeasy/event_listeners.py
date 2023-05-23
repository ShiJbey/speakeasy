import random

from neighborly import GameObject
from neighborly.components import LifeStage
from neighborly.components.character import LifeStageType
from neighborly.core.ecs import Active
from neighborly.events import GiveBirthEvent, JoinSettlementEvent

from speakeasy.components import Ethnicity, EthnicityValue, Inventory


def on_adult_join_settlement(
    gameobject: GameObject, event: JoinSettlementEvent
) -> None:
    if (
        gameobject.has_component(Active)
        and gameobject.get_component(LifeStage).life_stage >= LifeStageType.YoungAdult
        and gameobject.has_component(Inventory)
    ):
        rng = gameobject.world.get_resource(random.Random)

        inventory = gameobject.get_component(Inventory)

        for _ in range(rng.randint(0, 15)):
            inventory.add_item(rng.choice(["booze", "corn", "money"]), 1)

        gameobject.get_component(Ethnicity).ethnicity = rng.choice(
            sorted(list(EthnicityValue))
        )


def on_birth(gameobject: GameObject, event: GiveBirthEvent) -> None:
    if gameobject == event.birthing_parent or gameobject == event.other_parent:
        rng = gameobject.world.get_resource(random.Random)

        parent_inventory = gameobject.get_component(Inventory)
        baby_inventory = event.baby.get_component(Inventory)

        items_given = round(sum(parent_inventory.items.values()) / 2)
        if items_given >= 1:
            for _ in range(rng.randint(1, items_given)):
                key_options = [
                    k
                    for k in parent_inventory.items.keys()
                    if parent_inventory.get_quantity(k) > 0
                ]
                chosen_item = rng.choice(key_options)
                parent_inventory.remove_item(chosen_item, 1)
                baby_inventory.add_item(chosen_item, 1)

        baby_ethnicity = event.baby.get_component(Ethnicity)
        baby_ethnicity.ethnicity = rng.choice(
            [
                event.birthing_parent.get_component(Ethnicity).ethnicity,
                event.other_parent.get_component(Ethnicity).ethnicity,
            ]
        )


def register_event_listeners():
    GameObject.on(GiveBirthEvent, on_birth)
    GameObject.on(JoinSettlementEvent, on_adult_join_settlement)
