import os
import pathlib
from typing import Any

from neighborly.loaders import load_data_file, load_occupation_types, load_prefab
from neighborly.plugins.defaults import names
from neighborly.simulation import Neighborly, PluginInfo

import speakeasy.components
import speakeasy.social_rules
import speakeasy.systems
from speakeasy import VERSION
from speakeasy.event_listeners import register_event_listeners
from speakeasy.factories import InventoryFactory

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"

plugin_info = PluginInfo(
    name="Speakeasy", plugin_id="external.speakeasy", version=VERSION
)


def setup(sim: Neighborly, **kwargs: Any) -> None:
    # Register components
    sim.register_component(speakeasy.components.Inventory, factory=InventoryFactory())
    sim.register_component(speakeasy.components.OwnedBy)
    sim.register_component(speakeasy.components.IsFaction)
    sim.register_component(speakeasy.components.Faction)
    sim.register_component(speakeasy.components.Ethnicity)
    sim.register_component(speakeasy.components.Favors)
    sim.register_component(speakeasy.components.Produces)
    sim.register_component(speakeasy.components.Knowledge)
    sim.register_component(speakeasy.components.Respect)

    # Add systems
    sim.add_system(speakeasy.systems.ProbeRelationshipSystem())
    sim.add_system(speakeasy.systems.ProduceItemsSystem())
    sim.add_system(speakeasy.systems.GenerateSelfKnowledgeSystem())

    # load prefabs and content
    load_prefab(_RESOURCES_DIR / "character.default.with-inventory.yaml")
    load_prefab(_RESOURCES_DIR / "business.default.with-produces.yaml")
    load_prefab(_RESOURCES_DIR / "town.default.with-ethnicity.yaml")
    load_data_file(_RESOURCES_DIR / "businesses.yaml")
    load_occupation_types(_RESOURCES_DIR / "occupation_types.yaml")

    # event listeners
    register_event_listeners()

    names.setup(sim, **kwargs)
