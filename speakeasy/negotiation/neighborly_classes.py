import os
import sys
import types
import random
import time
import cProfile, pstats

import neighborly

from neighborly.components import GameCharacter
from neighborly.components import Active, Resident, BusinessOwner, Business, EmployeeOf
from neighborly.core.relationship import Relationship, RelationshipManager
from neighborly.exporter import export_to_json

from neighborly.core.roles import Role, RoleList
from neighborly.plugins.defaults.life_events import RetireLifeEvent, MarriageLifeEvent, DivorceLifeEvent, StartDatingLifeEvent, DatingBreakUp, GetPregnantLifeEvent, FindOwnPlaceLifeEvent
currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(currentdir)

sys.path.insert(0, parentdir + '/negotiation_core') 
sys.path.insert(0, os.path.abspath(currentdir + '/neighborly/samples'))
sys.path.insert(0, os.path.abspath(currentdir + '/speakeasy'))

from neighborly.utils.relationships import get_relationship, get_relationships_with_statuses
from neighborly.utils.statuses import has_status

import speakeasy.negotiation.core as negotiation
from negotiation import Action, NegotiationState
import talktown
import speakeasy
from speakeasy.events import GainItemEffect, LoseItemEffect, GainKnowledgeEffect, GainRelationshipEffect, LoseRelationshipEffect, needs_item_from, get_associated_business
from speakeasy.components import Respect, Knowledge, Favors, Produces
from speakeasy.events import TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent

supported_actions = [TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent]

class NeighborlyNegotiator():
    def __init__(self, name, game_object : neighborly.GameObject) -> None:
        self.name = name
        self.gameObject = game_object
        self.agent = negotiation.Agent()
        self.negotiation_state : NegotiationState = None
        #overload the negotiation functions
        self.agent.evaluate_action = types.MethodType(self.evaluate_action_ov, self)
        self.agent.generate_starting_possible_actions = types.MethodType(self.generate_starting_possible_actions_ov, self)
        self.agent.parent = self


    def generate_starting_possible_actions_ov(self, old_self) -> 'list[Action]':
        possible_actions = []
        partner : NeighborlyNegotiator = self.negotiation_state.get_partner(self.agent).parent

        #print(f'enumerating actions for {self.gameObject.get_component(GameCharacter).first_name}')

        for action in supported_actions:
            if action in [GiveEvent, TradeEvent]:
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", self.gameObject), Role("Other", partner.gameObject)])):
                    possible_actions.append(Action(event))
                    #print(f'they can ask for {action.__name__}: {self.agent.evaluate_action(Action(event))}')
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Other", self.gameObject)])):
                    possible_actions.append(Action(event))
                    #print(f'they can get asked for {action.__name__}: {self.agent.evaluate_action(Action(event))}')
            if action in [GoodWordEvent]:
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Subject", self.gameObject), Role("Other", None)])):
                    possible_actions.append(Action(event))
                    #print(f'they can get asked for {action.__name__}: {self.agent.evaluate_action(Action(event))}')
            if action in [TellAboutEvent]:
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Subject", self.gameObject), Role("Other", None)])):
                    possible_actions.append(Action(event))
                    #print(f'they can ask for {action.__name__}: {self.agent.evaluate_action(Action(event))}')
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Subject", None), Role("Other", self.gameObject)])):
                    possible_actions.append(Action(event))
                    #print(f'they can get asked for {action.__name__}: {self.agent.evaluate_action(Action(event))}')

            #...others here...

        possible_actions = [p for p in possible_actions if self.agent.evaluate_action(p) > 0 and p not in self.negotiation_state.currentOffers[0]]
        #print(f'{len(possible_actions)} are pos')
        return possible_actions

    #evaluate action (evaluator, verb, subject, object, verbbenefitfor_subject, verbbenefitfor_object):
    def evaluate_action_ov(self, old_self, action : negotiation.Action) -> int:
        neighborly_action_priority = action.val.get_priority()
        effects_dict = action.val.get_effects()

        biz = get_associated_business(self.gameObject)
        prod = None
        if biz:
            prod = biz.gameobject.get_component(Produces)
            
        utility = 0

        for role in effects_dict.keys():
            if role.gameobject != self.gameObject:
                continue

            effects = effects_dict[role]
            
            for effect in effects:
                if type(effect) in [GainItemEffect, LoseItemEffect]:
                    sign = 1 if type(effect) is GainItemEffect else -1

                    utility += 1 * sign
                    
                    if biz:
                        if effect.item in prod.requires:
                            utility += 1 * sign
                        #elif effect.item in prod.produces:
                            #utility -= 1 * sign

                    continue     

                elif type(effect) in [GainRelationshipEffect, LoseRelationshipEffect]:
                    sign = 1 if type(effect) is GainRelationshipEffect else -1
                    target = effect.relationship.get_component(Relationship).target
                    owner = effect.relationship.get_component(Relationship).owner

                    utility += 1 * sign
                    if effect.facet == Respect:
                        #someone gains respect for me
                        if target == self.gameObject._id:
                            other = self.gameObject.world.get_gameobject(owner)
                            other_biz = get_associated_business(other)
                            if other_biz and biz:
                                other_prod = other_biz.gameobject.get_component(Produces)
                                if True in [x in other_prod.produces for x in prod.requires]:
                                    utility += 1 * sign
                    
                    #gaining favors is considered bad, losing is considered REALLY good
                    elif effect.facet == Favors:
                        if target == self.gameObject._id:
                            #having someone no longer owe me is fine, 0 util (i probably got something out of it)
                            if effect is LoseRelationshipEffect:
                                utility -= 1 * sign 
                            #having someone owe me is good enough for util of 2
                            else:
                                utility += 1 * sign
                        if owner == self.gameObject._id:
                            utility -= 5 * sign # getting rid of a favor u owe is worth a lot & owing a favor is a pricy place to be

                elif type(effect) is GainKnowledgeEffect:
                    if biz and effect.item in prod.requires:
                        utility += 2 #knowledge is power or whatever

        return utility * neighborly_action_priority

def negotiate(agent1, agent2, thing_to_ask_for):
    result = negotiation.print_negotiation_trace(agent1, agent2, thing_to_ask_for)
    if result[0] == negotiation.ResponseCategory.ACCEPT:
        return result[1][0]
    else:
        return[]
    