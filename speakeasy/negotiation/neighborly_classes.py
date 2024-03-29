import types
from typing import List
import random

from neighborly import GameObject
from neighborly.core.relationship import Relationship

from neighborly.core.roles import Role, RoleList
from neighborly.core.relationship import get_relationship

from speakeasy.negotiation.core import Action, Agent, ResponseCategory
from speakeasy.events import GainItemEffect, LoseItemEffect, GainKnowledgeEffect, GainRelationshipEffect, LoseRelationshipEffect, get_associated_business
from speakeasy.components import Respect, Favors, Produces, Inventory
from speakeasy.events import TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent

supported_actions = [TradeEvent, GoodWordEvent, GiveEvent, TellAboutEvent]

def check_item_possibility(self_object, other_object, offers_so_far, potential_action):
    self_inventory = self_object.get_component(Inventory)
    other_inventory = other_object.get_component(Inventory)

    self_net_item_dict = {}
    other_net_item_dict = {}

    #calculate the net gain or loss of items resulting from the current offer + potential action

    list_of_actions = []
    list_of_actions.extend(offers_so_far[0])
    list_of_actions.append(potential_action)

    for action in list_of_actions:
        effects_dict = action.val.get_effects()

        for role in effects_dict.keys():
            if role.gameobject == self_object:
                chosen_dict = self_net_item_dict
            elif role.gameobject == other_object:
                chosen_dict = other_net_item_dict

            effects = effects_dict[role]
            for effect in effects:
                if type(effect) in [LoseItemEffect]: #don't consider gain as that can crete really dumb trades
                    item_delta = 1 if effect is GainItemEffect else -1
                    if effect.item not in chosen_dict:
                        chosen_dict[effect.item] = item_delta
                    else:
                        chosen_dict[effect.item] = item_delta + chosen_dict[effect.item]

    #make sure its possible to lose that many items

    #print(self_net_item_dict)
    #print(other_net_item_dict)

    for item in self_net_item_dict:
        amount = self_net_item_dict[item]
        #print(item, amount, self_inventory.get_quantity(item), not (amount < 0 and self_inventory.get_quantity(item) < -amount))
        if amount < 0 and self_inventory.get_quantity(item) < -amount:
            return False

    for item in other_net_item_dict:
        amount = other_net_item_dict[item]
        #print(item, amount, other_inventory.get_quantity(item), not (amount < 0 and other_inventory.get_quantity(item) < -amount))
        if amount < 0 and other_inventory.get_quantity(item) < -amount:
            return False

    return True
class NeighborlyNegotiator(Agent):
    def __init__(self, name: str, game_object : GameObject, seeded_random) -> None:
        super().__init__(seeded_random)
        self.name = name
        self.gameObject = game_object
        #overload the negotiation functions
        #self.agent.evaluate_action = types.MethodType(self.evaluate_action_ov, self)
        #self.agent.generate_starting_possible_actions = types.MethodType(self.generate_starting_possible_actions_ov, self)
        #self.agent.parent = self

    def generate_starting_possible_actions(self) -> 'list[Action]':
        possible_actions: List[Action] = []
        partner : NeighborlyNegotiator = self.negotiation_state.get_partner(self)

        #print(f'enumerating actions for {self.gameObject.get_component(GameCharacter).first_name}')

        for action in supported_actions:
            if action in [GiveEvent, TradeEvent]:
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", self.gameObject), Role("Other", partner.gameObject)])):
                    if check_item_possibility(self.gameObject, partner.gameObject, self.negotiation_state.currentOffers, Action(event)):
                        possible_actions.append(Action(event))
                        #print(f'they can ask for {action.__name__}: {self.evaluate_action(Action(event))}')
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Other", self.gameObject)])):
                    if check_item_possibility(self.gameObject, partner.gameObject, self.negotiation_state.currentOffers, Action(event)):
                        possible_actions.append(Action(event))
                        #print(f'they can ask for {action.__name__}: {self.evaluate_action(Action(event))}')

            if action in [GoodWordEvent]:
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Subject", self.gameObject), Role("Other", None)])):
                    possible_actions.append(Action(event))
                    #print(f'they can ask for {action.__name__}: {self.evaluate_action(Action(event))}')
            if action in [TellAboutEvent]:
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Subject", self.gameObject), Role("Other", None)])):
                    possible_actions.append(Action(event))
                    #print(f'they can ask for {action.__name__}: {self.evaluate_action(Action(event))}')
                if event := action.instantiate(self.gameObject.world, RoleList([Role("Initiator", partner.gameObject), Role("Subject", None), Role("Other", self.gameObject)])):
                    possible_actions.append(Action(event))
                    #print(f'they can ask for {action.__name__}: {self.evaluate_action(Action(event))}')

            #...others here...

        possible_actions = [p for p in possible_actions if self.evaluate_action(p) > 0 and p not in self.negotiation_state.currentOffers[0]]
        #print(f'{len(possible_actions)} are pos')
        return possible_actions

    #evaluate action (evaluator, verb, subject, object, verbbenefitfor_subject, verbbenefitfor_object):
    def evaluate_action(self, action : Action) -> int:
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
                    used_rational_util = False
                    if biz:
                        if effect.item in prod.requires:
                            utility += 4 * sign
                            used_rational_util = True
                        #elif effect.item in prod.produces:
                            #utility -= 1 * sign

                    if not used_rational_util:
                        utility += self.gameObject.world.get_resource(random.Random).randint(0, 3) * sign

                    continue

                elif type(effect) in [GainRelationshipEffect, LoseRelationshipEffect]:
                    sign = 1 if type(effect) is GainRelationshipEffect else -1
                    target = effect.relationship.get_component(Relationship).target
                    owner = effect.relationship.get_component(Relationship).owner
                    target_obj = self.gameObject.world.get_gameobject(target)
                    owner_obj = self.gameObject.world.get_gameobject(owner)

                    utility += 1 * sign
                    if effect.facet == Respect:
                        #someone gains respect for me
                        if target == self.gameObject.uid:
                            other_biz = get_associated_business(owner_obj)
                            if other_biz and biz:
                                other_prod = other_biz.gameobject.get_component(Produces)
                                if True in [x in other_prod.produces for x in prod.requires]:
                                    utility += 1 * sign

                    #gaining favors is considered bad, losing is considered REALLY good (only if you actually owe them a Favor, in which case its bad the more Favors they owe you)
                    elif effect.facet == Favors:
                        i_own_the_debt = owner == self.gameObject.uid

                        if i_own_the_debt:
                            favors_they_owe_me = effect.relationship.get_component(Favors).favors
                            favors_i_owe_them = get_relationship(target_obj, owner_obj).get_component(Favors).favors

                            #me no longer owing a favor is usually good
                            if type(effect) is LoseRelationshipEffect:
                                utility += 5*(favors_i_owe_them > 0) - favors_they_owe_me * 2
                            
                            #me owing a favor is increasingly bad
                            if type(effect) is GainRelationshipEffect:
                                utility -= favors_i_owe_them * 2

                        else:
                            favors_i_owe_them = effect.relationship.get_component(Favors).favors
                            favors_they_owe_me = get_relationship(target_obj, owner_obj).get_component(Favors).favors

                            #them no longer owing me a favor is fine
                            if type(effect) is LoseRelationshipEffect:
                                pass

                            #them owing me a favor is nice, unless they already do
                            if type(effect) is GainRelationshipEffect:
                                utility += 1 - favors_they_owe_me

                        #print(f"GoodWord: {utility}, I-own:{i_own_the_debt}, favors-i-owe:{favors_i_owe_them}, favors-they-owe:{favors_they_owe_me}")

                elif type(effect) is GainKnowledgeEffect:
                    if biz and effect.item in prod.requires:
                        utility += 2 #knowledge is power or whatever
            
        return utility * neighborly_action_priority
