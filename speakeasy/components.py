from typing import Dict
from typing import Any, Dict, Optional, Union, Set
from enum import Enum, auto

from neighborly import Component
from neighborly.core.relationship import RelationshipStatus, RelationshipFacet


class Inventory(Component):
    """
    Tracks the items that the GameObject possesses

    Attributes
    ----------
    items: Dict[str, int]
        Item names mapped to quantity counts
    """

    __slots__ = "items"

    def __init__(self, items: Optional[Dict[str, int]] = None) -> None:
        """
        Parameters

        Parameters
        ----------
        items : Optional[Dict[str, int]], optional
            The starting set of items in the inventory
        """
        super().__init__()
        self.items: Dict[str, int] = {**items} if items else {}

    def add_item(self, item: str, quantity: int) -> None:
        """Add a quantity of an item to the inventory"""
        if item not in self.items:
            self.items[item] = 0
        self.items[item] += quantity

    def remove_item(self, item: str, quantity: int) -> None:
        """Add a quantity of an item to the inventory"""
        if item not in self.items:
            raise KeyError(f"Cannot find item, {item}, in inventory")

        if self.items[item] < quantity:
            raise ValueError(
                    f"Quantity ({quantity}) too high. "
                    f"Inventory has {self.items[item]} {item}(s)"
                )

        self.items[item] -= quantity

    def get_item(self, item: str) -> int:
        """Returns the quantity of an item in the inventory"""
        return self.items.get(item, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": {**self.items}
        }

    def __str__(self) -> str:
        return self.items.__str__()

    def __repr__(self) -> str:
        return f"Inventory({self.items.__repr__()})"


class OwnedBy(RelationshipStatus):
    """A Relationship status that signifies a GameObject is owned by another"""

    pass


class IsFaction(Component):
    """Tags a GameObject as a faction"""

    def to_dict(self) -> Dict[str, Any]:
        return {}

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return self.__class__.__name__


class Faction(Component):
    """
    Tracks the faction that a GameObject belongs to

    Attributes
    ----------
    name: str
        The name of the faction
    faction_id: int
        The ID of the GameObject that represents this faction
    """

    __slots__ = "name", "faction_id"

    def __init__(self, name: str, faction_id: int) -> None:
        super().__init__()
        self.name = name
        self.faction_id = faction_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "faction_id": self.faction_id
        }

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Faction):
            raise TypeError(f"Expected Faction but was type {type(__o)}")
        return self.faction_id == __o.faction_id

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return self.__class__.__name__


class EthnicityValue(Enum):
    Asian = auto()
    Black = auto()
    Latino = auto()
    NativeAmerican = auto()
    White = auto()


class Ethnicity(Component):
    """
    Tracks the character's ethnicity for social interactions

    Attributes
    ----------
    ethnicity: EthnicityValue
        The value of the character's ethnicity
    """

    __slots__ = "ethnicity"

    def __init__(self, ethnicity: Union[str, EthnicityValue]) -> None:
        super().__init__()
        self.ethnicity: EthnicityValue = \
            ethnicity if isinstance(ethnicity, EthnicityValue) \
            else EthnicityValue[ethnicity]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ethnicity": self.ethnicity.name
        }

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Ethnicity):
            raise TypeError(f"Expected Ethnicity but was type {type(__o)}")
        return self.ethnicity == __o.ethnicity

    def __str__(self) -> str:
        return self.ethnicity.name

    def __repr__(self) -> str:
        return f"Ethnicity({self.ethnicity.name})"


class Favors(Component):
    """
    Attached to relationships and tracks the number of favors a GameObject owes another

    Attributes
    ----------
    favors: int
        The number of favors owed
    """

    __slots__ = "favors"

    def __init__(self, favors: int = 0) -> None:
        """
        Parameters
        ----------
        favors : int, optional
            The starting number of favors, by default 0
        """
        super().__init__()
        self.favors = favors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "favors": self.favors
        }

    def __str__(self) -> str:
        return self.favors.__str__()

    def __repr__(self) -> str:
        return f"Favors({self.favors})"


class Produces(Component):
    """
    Specifies what items a gameobject creates using another set of items

    Attributes
    ----------
    produces: Dict[str, int]
        Names of items produced mapped to quantities
    requires: Dict[str, int]
        Names of items required for production mapped to quantities
    """

    __slots__ = "produces", "requires"

    def __init__(self, produces: Dict[str, int], requires: Dict[str, int]) -> None:
        """
        Parameters
        ----------
        produces: Dict[str, int]
            Names of items produced mapped to quantities
        requires: Dict[str, int]
            Names of items required for production mapped to quantities
        """
        super().__init__()
        self.produces = produces
        self.requires = requires

    def to_dict(self) -> Dict[str, Any]:
        return {
            "produces": self.produces,
            "requires": self.requires
        }

    def __str__(self) -> str:
        return f"{self.requires} => {self.produces}"

    def __repr__(self) -> str:
        return f"Produces({self.requires} => {self.produces})"


class Knowledge(Component):
    """
    Tracks what a character knows

    produces: Dict[str, Set[int]]
        Map of item names to a set of IDs of businesses that produce that item
    buys: Dict[str, Set[int]]
        Map of item names to a set of IDs of businesses that buy that item
    """

    __slots__ = "produces", "buys"

    def __init__(self) -> None:
        super().__init__()
        self.produces: Dict[str, Set[int]] = {}
        self.buys: Dict[str, Set[int]] = {}

    def add_producer(self, producer: int, item: str) -> None:
        """
        Add knowledge of a business that produces an item

        Parameters
        ----------
        producer : int
            The GameObject ID of the the business that produces an item
        item : str
            The name of the item that's produced
        """
        if item not in self.produces:
            self.produces[item] = set()
        self.produces[item].add(producer)

    def remove_producer(self, producer: int, item: str) -> None:
        """
        Remove knowledge of a business that produces an item

        Parameters
        ----------
        producer : int
            The GameObject ID of the the business that produces an item
        item : str
            The name of the item that's produced
        """
        if item not in self.produces:
            return
        self.produces[item].remove(producer)

    def add_buyer(self, buyer: int, item: str) -> None:
        """
        Add knowledge of a business that buys an item

        Parameters
        ----------
        buyer : int
            The GameObject ID of the the business that produces an item
        item : str
            The name of the item that's produced
        """
        if item not in self.buys:
            self.buys[item] = set()
        self.buys[item].add(buyer)

    def remove_buyer(self, buyer: int, item: str) -> None:
        """
        Remove knowledge of a business that produces an item

        Parameters
        ----------
        buyer : int
            The GameObject ID of the the business that produces an item
        item : str
            The name of the item that's produced
        """
        if item not in self.buys:
            return
        self.buys[item].remove(buyer)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyers": {**self.buys},
            "produces": {**self.produces}
        }


class Respect(RelationshipFacet):
    """Tracks how much a GameObject respects another"""

    pass
