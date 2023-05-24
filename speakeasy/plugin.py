import os
import pathlib
from typing import Any

from neighborly.simulation import PluginInfo, Neighborly
from neighborly.loaders import load_prefab, load_data_file, load_occupation_types
from neighborly.plugins.defaults import names

from speakeasy import VERSION
import speakeasy.components
import speakeasy.systems
import speakeasy.social_rules
from speakeasy.event_listeners import register_event_listeners

_RESOURCES_DIR = pathlib.Path(os.path.abspath(__file__)).parent / "data"

plugin_info = PluginInfo(
    name="Speakeasy",
    plugin_id="external.speakeasy",
    version=VERSION
)


def setup(sim: Neighborly, **kwargs: Any) -> None:

    # Register components
    sim.register_component(speakeasy.components.Inventory)
    sim.register_component(speakeasy.components.OwnedBy)
    sim.register_component(speakeasy.components.IsFaction)
    sim.register_component(speakeasy.components.Faction)
    sim.register_component(speakeasy.components.Ethnicity)
    sim.register_component(speakeasy.components.Favors)
    sim.register_component(speakeasy.components.Produces)
    sim.register_component(speakeasy.components.Knowledge)
    sim.register_component(speakeasy.components.Respect)

    # Add systems
    sim.add_system(speakeasy.systems.InitialInventorySystem())
    sim.add_system(speakeasy.systems.InitialEthnicitySystem())
    sim.add_system(speakeasy.systems.ProbeRelationshipSystem())
    sim.add_system(speakeasy.systems.ProduceItemsSystem())

    #load prefabs and content
    load_prefab(_RESOURCES_DIR / "character.default.with-inventory.yaml")
    load_prefab(_RESOURCES_DIR / "business.default.with-produces.yaml")
    load_prefab(_RESOURCES_DIR / "town.default.with-ethnicity.yaml")
    load_data_file(_RESOURCES_DIR / "businesses.yaml")
    load_occupation_types(_RESOURCES_DIR / "occupation_types.yaml")

    #event listeners
    register_event_listeners()
    
    names.setup(sim, **kwargs)