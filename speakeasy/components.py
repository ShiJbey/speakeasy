from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from neighborly.core.ecs import Component, ISerializable
from neighborly.core.relationship import RelationshipFacet, RelationshipStatus
from ordered_set import OrderedSet


class Inventory(Component, ISerializable):
    """Tracks the items that the GameObject possesses."""

    __slots__ = "items"

    items: Dict[str, int]
    """Item names mapped to quantity counts."""

    def __init__(self, items: Optional[Dict[str, int]] = None) -> None:
        """
        Parameters
        ----------
        items
            The starting set of items in the inventory
        """
        super().__init__()
        self.items: Dict[str, int] = {**items} if items is not None else {}

    def add_item(self, item: str, quantity: int) -> None:
        """Add an item to the inventory.

        Parameters
        ----------
        item
            The name of an item to add.
        quantity
            The amount to add to the inventory.
        """
        if item not in self.items:
            self.items[item] = 0
        self.items[item] += quantity

    def remove_item(self, item: str, quantity: int) -> None:
        """Add an item to the inventory.

        Parameters
        ----------
        item
            The name of an item to remove.
        quantity
            The quantity of the item to remove.
        """
        if item not in self.items:
            raise KeyError(f"Cannot find item, {item}, in inventory")

        if self.items[item] < quantity:
            raise ValueError(
                f"Quantity ({quantity}) too high. "
                f"Inventory has {self.items[item]} {item}(s)"
            )

        self.items[item] -= quantity
        if self.items[item] == 0:
            del self.items[item]

    def get_quantity(self, item: str) -> int:
        """Returns the quantity of an item in the inventory.

        Parameters
        ----------
        item
            The name of an item
        """
        return self.items.get(item, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {"items": {**self.items}}

    def __str__(self) -> str:
        return self.items.__str__()

    def __repr__(self) -> str:
        return f"Inventory({self.items.__repr__()})"


class OwnedBy(RelationshipStatus, ISerializable):
    """A Relationship status that signifies a GameObject is owned by another."""

    def to_dict(self) -> Dict[str, Any]:
        return {}


class IsFaction(Component, ISerializable):
    """Tags a GameObject as a faction."""

    def to_dict(self) -> Dict[str, Any]:
        return {}

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return self.__class__.__name__


class Faction(Component, ISerializable):
    """Tracks the faction that a GameObject belongs to."""

    faction_id: int
    """The GameObject ID of the faction."""

    __slots__ = "faction_id"

    def __init__(self, faction_id: int) -> None:
        """
        Parameters
        ----------
        faction_id
            The GameObject ID of the faction.
        """
        super().__init__()
        self.faction_id = faction_id

    def to_dict(self) -> Dict[str, Any]:
        return {"faction_id": self.faction_id}

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Faction):
            raise TypeError(f"Expected Faction but was type {type(__o)}")
        return self.faction_id == __o.faction_id

    def __str__(self) -> str:
        return f"Faction({self.faction_id})"

    def __repr__(self) -> str:
        return f"Faction({self.faction_id})"


class EthnicityValue(Enum):
    """Enumeration of Ethnicity types."""

    Asian = "Asian"
    Black = "Black"
    Latino = "Latino"
    NativeAmerican = "NativeAmerican"
    White = "White"
    NotSpecified = "Not Specified"

    def __lt__(self, __o: EthnicityValue) -> bool:
        return self.name < __o.name

    def __gt__(self, __o: EthnicityValue) -> bool:
        return self.name > __o.name


class Ethnicity(Component):
    """Tracks a character's ethnicity."""

    __slots__ = "ethnicity"

    ethnicity: EthnicityValue
    """The value of the character's ethnicity."""

    def __init__(self, ethnicity: Union[str, EthnicityValue]) -> None:
        """
        Parameters
        ----------
        ethnicity
            An Ethnicity enum value or ethnicity name string.
        """
        super().__init__()
        self.ethnicity = (
            ethnicity
            if isinstance(ethnicity, EthnicityValue)
            else EthnicityValue[ethnicity]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"ethnicity": self.ethnicity.name}

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Ethnicity):
            raise TypeError(f"Expected Ethnicity but was type {type(__o)}")
        return self.ethnicity == __o.ethnicity

    def __str__(self) -> str:
        return self.ethnicity.name

    def __repr__(self) -> str:
        return f"Ethnicity({self.ethnicity.name})"


class Favors(Component):
    """Tracks the number of favors a GameObject owes another."""

    __slots__ = "favors"

    favors: int
    """The number of favors owed."""

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
        return {"favors": self.favors}

    def __str__(self) -> str:
        return self.favors.__str__()

    def __repr__(self) -> str:
        return f"Favors({self.favors})"


class Produces(Component):
    """Specifies what items a gameobject creates using another set of items."""

    __slots__ = "produces", "requires"

    produces: Dict[str, int]
    """Names of items produced mapped to quantities."""

    requires: Dict[str, int]
    """Names of items required for production mapped to quantities."""

    def __init__(self, produces: Dict[str, int], requires: Dict[str, int]) -> None:
        """
        Parameters
        ----------
        produces
            Names of items produced mapped to quantities
        requires
            Names of items required for production mapped to quantities
        """
        super().__init__()
        self.produces = produces
        self.requires = requires

    def to_dict(self) -> Dict[str, Any]:
        return {"produces": self.produces, "requires": self.requires}

    def __str__(self) -> str:
        return f"{self.requires} => {self.produces}"

    def __repr__(self) -> str:
        return f"Produces({self.requires} => {self.produces})"


class Knowledge(Component):
    """Tracks knowledge of what businesses produce and buy certain items."""

    __slots__ = ("produces", "buys")

    produces: Dict[str, OrderedSet[int]]
    """Map of item names to a set of IDs of businesses that produce that item."""

    buys: Dict[str, OrderedSet[int]]
    """Map of item names to a set of IDs of businesses that buy that item."""

    def __init__(self) -> None:
        super().__init__()
        self.produces = {}
        self.buys = {}

    def add_producer(self, producer: int, item: str) -> None:
        """Add knowledge of a business that produces an item.

        Parameters
        ----------
        producer
            The GameObject ID of the the business that produces an item
        item
            The name of the item that's produced
        """
        if item not in self.produces:
            self.produces[item] = OrderedSet([])
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
            self.buys[item] = OrderedSet([])
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

    def known_producers(self) -> List[int]:
        known_businesses: List[int] = []
        for producers in self.produces.values():
            known_businesses.extend(list(producers))
        return known_businesses

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyers": {**dict([(a, list(b)) for (a, b) in self.buys.items()])},
            "produces": {**dict([(a, list(b)) for (a, b) in self.produces.items()])},
        }


class Respect(RelationshipFacet):
    """Tracks how much a GameObject respects another."""

    pass
