import sys
import random as r
import time
from typing import Union

import neighborly
from neighborly.components import GameCharacter
from neighborly.core.ecs import Active, GameObject
from neighborly.core.roles import RoleList
from neighborly.core.relationship import get_relationship
from neighborly.core.life_event import AllEvents
from neighborly.exporter import export_to_json

sys.path.append('../')
from speakeasy.events import get_associated_business
from speakeasy.components import Respect, Produces
from speakeasy.events import TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent

from speakeasy.negotiation.core import (
    print_negotiation_trace,
    get_initial_ask_options,
)
from speakeasy.negotiation.neighborly_classes import NeighborlyNegotiator

supported_actions = [TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent]


def test_supported_event_feasibility(sim: neighborly.Neighborly):
    for action in supported_actions:
        if event := action.instantiate(sim.world, RoleList()):
            print(f"It is possible to {action.__name__}.")
        else:
            print(f"Failed to find a way to {action.__name__}!! (Spontaneously)")


def run_random_negotiation(sim: neighborly.Neighborly, num: int = 1):
    random = sim.world.get_resource(r.Random)
    print(f"Initiating random negotiation in world {sim}")
    possible_negotiators = sim.world.get_components((Active, GameCharacter))

    print()
    print(
        "Current active characters & associated businesses (required item -> produced item):"
    )
    print(
        "\n".join(
            [
                f'{n[1][1].full_name}, {get_associated_business(sim.world.get_gameobject(n[0])).gameobject.get_component(Produces) if get_associated_business(sim.world.get_gameobject(n[0])) else ""}'
                for n in possible_negotiators
            ]
        )
    )

    options = []
    tries = 0
    initiator = None
    partner = None
    pairs_run = []
    print()
    print()
    print(f"Running {num} negotiations:")
    while num > 0:
        while (len(options) < 1 and tries < 1000) or (initiator, partner) in pairs_run:
            initiator_gid, (_, initiator) = random.choice(possible_negotiators)

            partner_gid, (_, partner) = random.choice(
                [(gid, _) for (gid, _) in possible_negotiators if gid != initiator_gid]
            )

            initiator = NeighborlyNegotiator(
                initiator.full_name, sim.world.get_gameobject(initiator_gid)
            )
            partner = NeighborlyNegotiator(
                partner.full_name, sim.world.get_gameobject(partner_gid)
            )
            options = get_initial_ask_options(initiator, partner)
            tries += 1

        if len(options) < 1:
            print("Failed to find viable negotiation candidates. :c")
            return

        print()
        outgoing_respect = (
            get_relationship(initiator.gameObject, partner.gameObject)
            .get_component(Respect)
            .get_value()
        )
        incoming_respect = (
            get_relationship(partner.gameObject, initiator.gameObject)
            .get_component(Respect)
            .get_value()
        )
        print(f"#{num}")
        print(f"\tInitiator / Agent 1: {initiator.name} ({outgoing_respect})")
        print(f"\tTarget / Agent 2: {partner.name} ({incoming_respect})")

        thing_to_ask_for = random.choice(options)
        print(
            f"Generated {len(options)} things to ask for and chose: {thing_to_ask_for}"
        )

        # state.setup_initial_ask(thing_to_ask_for)
        print_negotiation_trace(initiator, partner, thing_to_ask_for)
        pairs_run.append((initiator, partner))
        num -= 1


def run_sim_with_negotiation(
    duration: int, seed: Union[str, int] = 1337, enable_negotiation: bool = True
):
    sim = neighborly.Neighborly(
        neighborly.NeighborlyConfig.parse_obj(
            {
                "seed": seed,
                "time_increment": "1mo",
                "relationship_schema": {
                    "components": {
                        "Friendship": {
                            "min_value": -100,
                            "max_value": 100,
                        },
                        "Romance": {
                            "min_value": -100,
                            "max_value": 100,
                        },
                        "InteractionScore": {
                            "min_value": -5,
                            "max_value": 5,
                        },
                        "Respect": {
                            "min_value": -100,
                            "max_value": 100,
                        },
                        "Favors": {"favors": 0},
                    }
                },
                "plugins": [
                    "neighborly.plugins.defaults.characters",
                    "neighborly.plugins.defaults.residences",
                    #"neighborly.plugins.defaults.life_events",
                    "neighborly.plugins.defaults.social_rules",
                    "neighborly.plugins.defaults.location_bias_rules",
                    "neighborly.plugins.defaults.resident_spawning",
                    "neighborly.plugins.defaults.create_town",
                    "neighborly.plugins.defaults.systems",
                    "neighborly.plugins.defaults.names",
                    "speakeasy.plugin",
                ],
                "settings": {
                    "enable_negotiation": enable_negotiation,
                },
            }
        )
    )

    print("Running some initial Speakeasy simulation...")

    st = time.time()
    sim.run_for(duration)
    elapsed_time = time.time() - st

    print("...done.")

    print(f"\tWorld Date: {sim.date.to_iso_str()}")
    print("\tExecution time: ", elapsed_time, "seconds")
    return sim

def test_seed_consistency(duration = 1, seed = 1337):
    num_to_sync = 2
    steps_to_test = 50
    sims = []
    for i in range(num_to_sync):
        AllEvents.clear_event_listeners()
        GameObject.clear_event_listeners()
        sim = neighborly.Neighborly(
        neighborly.NeighborlyConfig.parse_obj(
            {
                "seed": seed,
                "enable_negotiation": True,
                "time_increment": "1mo",
                "relationship_schema": {
                    "components": {
                        "Friendship": {
                            "min_value": -100,
                            "max_value": 100,
                        },
                        "Romance": {
                            "min_value": -100,
                            "max_value": 100,
                        },
                        "InteractionScore": {
                            "min_value": -5,
                            "max_value": 5,
                        },
                        "Respect": {
                            "min_value": -100,
                            "max_value": 100,
                        },
                        "Favors": {
                            "favors": 0
                        }
                    }
                },
                "plugins": [
                    "neighborly.plugins.defaults.create_town",
                    "neighborly.plugins.defaults.characters",
                    "neighborly.plugins.defaults.residences",
                    #"neighborly.plugins.defaults.life_events",
                    "neighborly.plugins.defaults.social_rules",
                    "neighborly.plugins.defaults.location_bias_rules",
                    "neighborly.plugins.defaults.resident_spawning",
                    #"neighborly.plugins.defaults.systems",
                    "neighborly.plugins.defaults.names",
                    "speakeasy.plugin"
                ],
            }
        )
        )
        print(f"++++++Starting Sim {i+1}+++++++")
        sim.run_for(duration)
        sims.append(sim)

        with open(f"speakeasy_synced_{sim.config.seed}_{i}.json", "w") as f:
            f.write(export_to_json(sim))

    for i in range(num_to_sync):
        all_events = sims[i].world.get_resource(AllEvents)
        for event in all_events:
            for j in range(num_to_sync):
                if i == j:
                    continue
                other_all_events = sims[j].world.get_resource(AllEvents)
                if event not in other_all_events:
                    print(f"Desync at event #{event.get_id()}: {event}")
                    return False
                
    return True

if __name__ == '__main__':
    if (test_seed_consistency()):
        sim = run_sim_with_negotiation(int(sys.argv[1]) if len(sys.argv) > 1 else 15)
        test_supported_event_feasibility(sim)
        run_random_negotiation(sim)
    else:
        print("Failed the seed conistency check.")
