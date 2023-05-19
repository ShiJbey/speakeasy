import random
from neighborly import GameObject
from neighborly.events import GiveBirthEvent, JoinSettlementEvent
from neighborly.core.ecs import Active
from neighborly.components import InTheWorkforce, LifeStage, Occupation, Unemployed
from neighborly.components.character import LifeStageType

from speakeasy.components import Inventory, Ethnicity, EthnicityValue

def on_adult_join_settlement(
    gameobject: GameObject, event: JoinSettlementEvent
) -> None:
    if (
        gameobject.has_component(Active)
        and gameobject.get_component(LifeStage).life_stage >= LifeStageType.YoungAdult
        and gameobject.has_component(Inventory)
    ):
        inventory = gameobject.get_component(Inventory)
        for i in range(event.character.world.get_resource(random.Random).randint(0,15)):
            inventory.add_item(event.character.world.get_resource(random.Random).choice(['booze','corn','money']), 1)

        new_adult_ethnicity = gameobject.get_component(Ethnicity)
        new_adult_ethnicity.ethnicity = list(EthnicityValue)[event.character.world.get_resource(random.Random).randint(0, len(list(EthnicityValue))-1)]

def on_birth(gameobject: GameObject, event: GiveBirthEvent) -> None:
    if (gameobject == event.birthing_parent or gameobject == event.other_parent):
        parent_inventory = gameobject.get_component(Inventory)
        baby_inventory = event.baby.get_component(Inventory)
        items_given = round(sum(parent_inventory.items.values()) / 2)
        if items_given >= 1:
          for i in range(event.birthing_parent.world.get_resource(random.Random).randint(1,items_given)):
              key_options = [k for k in parent_inventory.items.keys() if parent_inventory.get_item(k) > 0]
              chosen_item = event.birthing_parent.world.get_resource(random.Random).choice(key_options)
              parent_inventory.remove_item(chosen_item, 1)
              baby_inventory.add_item(chosen_item, 1)
        
        baby_ethnicity = event.baby.get_component(Ethnicity)
        baby_ethnicity.ethnicity = event.birthing_parent.world.get_resource(random.Random).choice([event.birthing_parent.get_component(Ethnicity).ethnicity, event.other_parent.get_component(Ethnicity).ethnicity])

def register_event_listeners():
    GameObject.on(GiveBirthEvent, on_birth)
    GameObject.on(JoinSettlementEvent, on_adult_join_settlement)

