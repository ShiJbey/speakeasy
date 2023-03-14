import os
import pathlib
from typing import Any

from neighborly.simulation import PluginInfo, Neighborly
from neighborly.loaders import load_prefab, load_data_file, load_occupation_types

from speakeasy import VERSION
import speakeasy.components
import speakeasy.systems
import speakeasy.social_rules

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
    sim.add_system(speakeasy.systems.ProduceItemsSystem())

    # Add social rules
    sim.add_social_rule(speakeasy.social_rules.respect_same_ethnicity)
    sim.add_social_rule(speakeasy.social_rules.disrespect_different_ethnicity)
    sim.add_social_rule(speakeasy.social_rules.respect_same_faction)
    sim.add_social_rule(speakeasy.social_rules.respect_for_family)
    sim.add_social_rule(speakeasy.social_rules.romance_boost_from_shared_virtues)
    sim.add_social_rule(speakeasy.social_rules.romance_loss_from_virtue_conflicts)
    sim.add_social_rule(speakeasy.social_rules.friendship_virtue_compatibility)

    #add events
    speakeasy.events.setup(sim)

    #load prefabs and content
    load_prefab(_RESOURCES_DIR / "character.default.with-inventory.yaml")
    load_prefab(_RESOURCES_DIR / "business.default.with-produces.yaml")
    load_data_file(sim, _RESOURCES_DIR / "businesses.yaml")
    load_occupation_types(sim.world, _RESOURCES_DIR / "occupation_types.yaml")