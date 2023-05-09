from enum import Enum
import random

class ResponseCategory(Enum):
  ACCEPT = 0,
  REJECT = 1,
  COUNTER = 2

class Action:
  def __init__(self, _val):
    self.val = _val

  def __eq__(self, __o: object) -> bool:
    if isinstance(__o, self.__class__):
      return self.val == __o.val
    else:
      return False

  def __ne__(self, __o: object) -> bool:
    return not self.__eq__(__o)

  def __hash__(self) -> int:
    return self.val.__hash__()

NegotiationOffer = list

def offers_to_string(offers : list):
  return " OR ".join([("[" + ",".join([str(action.val) for action in offer]) + "]") for offer in offers])

class Agent:
  def __init__(self):
    self.utilities = {}
    for i in range(26):
      action = Action(chr(ord('A') + i))
      self.utilities[action.val] = random.randint(-5,5)

    # Must have something w positive utility
    idx = random.randint(0,25)
    val = random.randint(1,5)
    self.utilities[list(self.utilities.keys())[idx]] = val
    self.ActionToAskFor = Action(chr(ord('A') + idx))
    self.parent = None

  # naive evaluation = random dictionary lookup
  def evaluate_action(self, action: Action):
    return self.utilities[action.val]

  def evaluate_offer(self, offer: NegotiationOffer):
    return sum([self.evaluate_action(action) for action in offer])

  # worker for generate_counter_offers
  def generate_counter_offers_recursive(self,
  offerUtilityNeeded: int,
  counterOfferSoFar: NegotiationOffer, 
  counterOffers: list,
  rejectedOffers: list,
  possibleActions: list):
    if (len(possibleActions) < 1):
      return counterOffers
    
    possibleNextAction = possibleActions.pop()
    utilityOfNextAction = self.evaluate_action(possibleNextAction)

    counterOfferSoFar.append(possibleNextAction)

    # cutoff recursion with the rejection list. #TODO: doesn't make sense to do really. and wont work as root offer isn't included
    #if (counterOfferSoFar in rejectedOffers):
    #  return counterOffers
    
    # naive: Don't continue building if not needed for own utility TODO: parameterize as Greed ? 
    if (self.evaluate_offer(counterOfferSoFar) >= offerUtilityNeeded):
      # TODO: doesnt work bc initial offer isn't included, see: print('appending current offer: ', offers_to_string([counterOfferSoFar]), ', rejected offers: ', offers_to_string(rejectedOffers))
      if (counterOfferSoFar not in rejectedOffers):
        counterOffers.append(counterOfferSoFar)
      return self.generate_counter_offers_recursive(offerUtilityNeeded, [], counterOffers, rejectedOffers, possibleActions)

    # else recurse and continue building the current offer.
    return self.generate_counter_offers_recursive(offerUtilityNeeded, counterOfferSoFar, counterOffers, rejectedOffers, possibleActions)
    
  def generate_starting_possible_actions(self):
    return [ action for action in list(map(Action, list(self.utilities.keys()))) if self.evaluate_action(action) > 0]
  
  #Naive Countering: Find sequence of actions (Offers) that sum to match (or exceed) needed utility.
  def generate_counter_offers(self, offerUtilityNeeded: int, startingOffer: NegotiationOffer, rejectedOffers : list):
    # startingPossibleActions = [ Action(val) for val in list(self.utilities.keys()) ]
    startingPossibleActions = self.generate_starting_possible_actions()
    startingPossibleActions = [a for a in startingPossibleActions if a not in startingOffer]
    startingPossibleActions = sorted(startingPossibleActions, key = lambda action: self.evaluate_action(action), reverse=False)
    
    # debug: print all starting possible actions
    # print(*[action.val +':'+ str(self.evaluate_action(action)) for action in startingPossibleActions])

    counterOffers = self.generate_counter_offers_recursive(offerUtilityNeeded, [], [], rejectedOffers, startingPossibleActions)

    counterOffers = [startingOffer + offer for offer in counterOffers]
		
    return counterOffers
  
  # return tuple (responseCategory, counterOffers)
  def respond_to_offer(self, offers: list, rejectedOffers: list, number_of_options: int = 2):
    counterOffers = []
		
    # Naive Order: First come first sercve.
    for offer in offers:
      currentOfferUtility = self.evaluate_offer(offer); # Evaluate what they're asking for. 
			
      if (currentOfferUtility >= 0): #TODO: parameterize willingness to perform neutral acts. aka Selfishness<->Benevolence? 
        counterOffers = [ offer ]
        return (ResponseCategory.ACCEPT, counterOffers)

      counterOffers = self.generate_counter_offers(-currentOfferUtility, offer, rejectedOffers) #.Except(rejectedOffersSoFar)
      counterOffers = [o for o in counterOffers if o not in rejectedOffers]
      counterOffers = counterOffers[:number_of_options]

      if (len(counterOffers) > 0):
        return (ResponseCategory.COUNTER, counterOffers)
			
			#try to compensate with Gratitude?
			
			#try to compensate with Money?
			
			#try to compensate with Reciprocal Action?
		
    return (ResponseCategory.REJECT, counterOffers)

  #this agent will take a turn, modify and return the negotiation state.
  def take_turn(self, negotiation_state):
    pass

class NegotiationState:
  def __init__(self, a1, a2, ask):
    self.agent1 = a1
    self.agent2 = a2
    self.initialAsk = None
    self.initialOffer = [ None ]
    self.currentOffers = [ [] ]
    self.rejectedOffers = []
    self.lastResult = ResponseCategory.COUNTER
    self.lastCountered = []
    self.currentAgentIndex = 1
    
    #containers for exchanged actions
    self.to_agent1 = []
    self.to_agent2 = []

  def setup_initial_ask(self, action : Action):
    self.initialAsk = action
    self.initialOffer = [ self.initialAsk ]
    self.currentOffers = [ self.initialOffer ]
  
  def get_agent_index(self, agent : Agent):
    return 1 if self.agent1 == agent else 2
  
  def get_partner(self, agent : Agent):
    if agent == self.agent1:
      return self.agent2
    elif agent == self.agent2:
      return self.agent1
    return None

def print_negotiation_trace(agent1, agent2, initialAsk):
    #agent1 = Agent()
    #agent2 = Agent()
		
		#Negotiation Protocol
    #initialAsk = agent1.ActionToAskFor
    initialOffer = [ initialAsk ]
    currentOffers = [ initialOffer ]
    rejectedOffers = []
		
    print("Negotiation Begins")
    print("==================")
    print(f"Agent 1 opens by asking Agent 2 for {offers_to_string(currentOffers)}. ", end =" ")
    currentAgentIndex = 2
    lastResult = ResponseCategory.COUNTER
		
    actionsDiscussed = []
		
    while lastResult == ResponseCategory.COUNTER:
      for offer in currentOffers:
        print(f"[{agent1.evaluate_offer(offer)}:{agent2.evaluate_offer(offer)}] ", end =" ")
        actionsDiscussed += offer
      
      print()
			
      currentAgent = agent1 if currentAgentIndex == 1 else agent2
      counterOffers = []
      (lastResult, counterOffers) = currentAgent.respond_to_offer(currentOffers, rejectedOffers);
			
      rejectedOffers += currentOffers
			
      if lastResult == ResponseCategory.COUNTER:
        print(f"Agent {currentAgentIndex} counters with {offers_to_string(counterOffers)}. ", end = ' ')
        currentOffers = counterOffers
      elif lastResult == ResponseCategory.ACCEPT: 
        print(f"Agent {currentAgentIndex} accepts {offers_to_string(counterOffers)}. ", end = ' ')
        currentOffers = counterOffers

        for offer in currentOffers:
          print(f"[{agent1.evaluate_offer(offer)}:{agent2.evaluate_offer(offer)}] ")

      elif lastResult == ResponseCategory.REJECT: 
        print(f"Agent {currentAgentIndex} rejects. ")
				
      currentAgentIndex = 2 if currentAgentIndex == 1 else 1
		
    print("==================")
		
    for a in actionsDiscussed:
      print(f"[{a.val} => {agent1.evaluate_action(a)}:{agent2.evaluate_action(a)}]")

    return (lastResult, currentOffers)

if __name__ == "__main__":
  agent1 = Agent()
  agent2 = Agent()  
  print_negotiation_trace(agent1, agent2, agent1.ActionToAskFor)
  
		
		
