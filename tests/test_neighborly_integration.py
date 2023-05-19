import os
import sys
import random as r
import time
import cProfile, pstats

import neighborly
from neighborly.components import GameCharacter
from neighborly.core.ecs import Active
from neighborly.core.roles import RoleList
from neighborly.core.relationship import get_relationship, get_relationships_with_statuses
from neighborly.exporter import export_to_json

#from neighborly.plugins.defaults.life_events import MarriageLifeEvent, DivorceLifeEvent, StartDatingLifeEvent, DatingBreakUp, GetPregnantLifeEvent

currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, os.path.abspath(parentdir))

from speakeasy.events import get_associated_business
from speakeasy.components import Respect, Knowledge, Favors, Produces
from speakeasy.events import TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent

from speakeasy.negotiation.core import Action, NegotiationState, print_negotiation_trace, get_initial_ask_options
from speakeasy.negotiation.neighborly_classes import NeighborlyNegotiator

supported_actions = [TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent]

def test_supported_event_feasibility(sim : neighborly.Neighborly):
    for action in supported_actions:
        if event:= action.instantiate(sim.world, RoleList()):
            print(f"It is possible to {action.__name__}.")
        else:
            print(f"Failed to find a way to {action.__name__}!! (Spontaneously)")

def run_random_negotiation(sim : neighborly.Neighborly, num : int = 1):
    random = sim.world.get_resource(r.Random)
    print(f'Initiating random negotiation in world {sim}')
    possible_negotiators = sim.world.get_components((Active, GameCharacter))

    print()
    print('Current active characters & associated businesses (required item -> produced item):')
    print('\n'.join([f'{n[1][1].full_name}, {get_associated_business(sim.world.get_gameobject(n[0])).gameobject.get_component(Produces) if get_associated_business(sim.world.get_gameobject(n[0])) else ""}' for n in possible_negotiators]))

    options = []
    tries = 0
    initiator = None
    partner = None
    pairs_run = []
    print()
    print()
    print(f'Running {num} negotiations:')
    while num > 0:
        while ((len(options) < 1 and tries < 1000) or (initiator, partner) in pairs_run):

            initiator_gid, (_, initiator) = random.choice(possible_negotiators)
            
            partner_gid, (_, partner) = random.choice([(gid, _) for (gid, _) in possible_negotiators if gid != initiator_gid])

            initiator = NeighborlyNegotiator( initiator.full_name, sim.world.get_gameobject(initiator_gid) )
            partner = NeighborlyNegotiator( partner.full_name, sim.world.get_gameobject(partner_gid) )
            options = get_initial_ask_options(initiator.agent, partner.agent)
            tries+=1

        if (len(options) < 1):
            print ("Failed to find viable negotiation candidates. :c")
            return
        
        print()
        outgoing_respect = get_relationship(initiator.gameObject, partner.gameObject).get_component(Respect).get_value()
        incoming_respect = get_relationship(partner.gameObject, initiator.gameObject).get_component(Respect).get_value()
        print(f'#{num}')
        print(f'\tInitiator / Agent 1: {initiator.name} ({outgoing_respect})')
        print(f'\tTarget / Agent 2: {partner.name} ({incoming_respect})')

        thing_to_ask_for = random.choice(options)
        print(f'Generated {len(options)} things to ask for and chose: {thing_to_ask_for}')

        #state.setup_initial_ask(thing_to_ask_for)
        print_negotiation_trace(initiator.agent, partner.agent, thing_to_ask_for)
        pairs_run.append((initiator, partner))
        num-=1

def run_sim_with_negotiation(duration, seed = 1337, enable_negotiation = True):
    sim = neighborly.Neighborly(
    neighborly.NeighborlyConfig.parse_obj(
        {
            "seed": seed,
            "enable_negotiation": enable_negotiation,
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
                #"neighborly.plugins.defaults.all",
                "neighborly.plugins.defaults.characters",
                #"neighborly.plugins.defaults.businesses",
                "neighborly.plugins.defaults.residences",
                "neighborly.plugins.defaults.life_events",
                "neighborly.plugins.defaults.social_rules",
                "neighborly.plugins.defaults.location_bias_rules",
                "neighborly.plugins.defaults.resident_spawning",
                #"neighborly.plugins.defaults.settlement",
                "neighborly.plugins.defaults.create_town",
                "speakeasy.plugin"
            ],
        }
    )
    )

    print('Running some initial Speakeasy simulation...')

    st = time.time()
    sim.run_for(duration)
    elapsed_time = time.time() - st

    print('...done.')

    print(f"\tWorld Date: {sim.date.to_iso_str()}")
    print("\tExecution time: ", elapsed_time, "seconds")
    return sim

if __name__ == '__main__':
    sim = run_sim_with_negotiation(sys.argv[1] if len(sys.argv) > 1 else 15)
    test_supported_event_feasibility(sim)
    run_random_negotiation(sim)
    