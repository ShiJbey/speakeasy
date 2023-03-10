"""
speakeasy/consequences.py

The concept of consequences is something created just for this project. There is not
a way for character AI to determine the benefit or loss associated with performing
various actions/actionable events. All the side effects are hidden inside the execute()
functions.

The goal of consequences is to list enough of the side effects from the execute function
to allow an AI agent to calculate the utility of an action/actionable event. For them to
do that we need a way for characters to know what consequences affect them.
"""

from dataclasses import dataclass, field
from neighborly import GameObject
from typing import Dict, List, Tuple


@dataclass
class ConsequencesInstance:
    gains_item: List[Tuple[GameObject, str, int]] = field(default_factory=list)
    loses_item: List[Tuple[GameObject, str, int]] = field(default_factory=list)


@dataclass
class ConsequencesDef:
    gains_item: List[Tuple[str, str, int]] = field(default_factory=list)
    loses_item: List[Tuple[str, str, int]] = field(default_factory=list)

    def instantiate(self, bindings: Dict[str, GameObject]) -> ConsequencesInstance:
        gains_item_tuples: List[Tuple[GameObject, str, int]] = []
        for entry in self.gains_item:
            role_name, item, quantity = entry
            gains_item_tuples.append(
                (bindings[role_name], item, quantity)
            )

        loses_item_tuples: List[Tuple[GameObject, str, int]] = []
        for entry in self.gains_item:
            role_name, item, quantity = entry
            loses_item_tuples.append(
                (bindings[role_name], item, quantity)
            )

        return ConsequencesInstance(
            gains_item=gains_item_tuples, loses_item=loses_item_tuples
        )


if __name__ == "__main__":

    C0 = {
        "gains_item": [
            ("Initiator", "wheat", 2),
        ],
        "loses_item": [
            ("Other", "wheat", 2)
        ],
        "gain_relationship_status": [
            ("Initiator", "Other", "BusinessPartner"),
            ("Other", "Initiator", "BusinessPartner"),
        ],
        "relationship_change": [
            ("Initiator", "Other", "Respect", 5),
            ("Other", "Initiator", "Respect", 5)
        ]
    }

    # Consequences are listed as tuples
    CTL = [
        # Operation, Positional Args
        ("gains_item", "Initiator", "wheat", 2),
        ("loses_item", "Other", "wheat", 2),
        ("gain_relationship_status", "Initiator", "Other", "BusinessPartner"),
        ("gain_relationship_status", "Other", "Initiator", "BusinessPartner"),
        ("relationship_change", "Initiator", "Other", "Respect", 5),
        ("relationship_change", "Other", "Initiator", "Respect", 5)
    ]

    # Consequences are first sorted by the target of the change
    CBR = {
        "Initiator": {
            "gains_item": [
                ("wheat", 2)
            ],
            "gain_relationship_status": [
                ("Other", "BusinessPartner")
            ],
            "relationship_change": [
                ("Other", "Respect", 5)
            ]
        },
        "Other": {
            "loses_item": [
                ("wheat", 2)
            ],
            "gain_relationship_status": [
                ("Initiator", "BusinessPartner")
            ],
            "relationship_change": [
                ("Initiator", "Respect", 5)
            ]
        }
    }
