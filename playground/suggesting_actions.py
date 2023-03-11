"""
One of the problems with this project is determining how to author actions.
"""
import pathlib
import random
from typing import Optional, List
from attr import has

from neighborly import GameObject, Neighborly, NeighborlyConfig, SimDateTime, World
from neighborly.decorators import life_event
from neighborly.core.life_event import ActionableLifeEvent
from neighborly.core.roles import Role, RoleList
from neighborly.components import Virtues, Virtue, Active, GameCharacter, Name
from neighborly.components.character import Child, Adolescent
from neighborly.loaders import load_names
from neighborly.core.tracery import Tracery
from numpy import character

from speakeasy.components import Faction, IsFaction

sim = Neighborly(
    NeighborlyConfig.parse_obj(
        {
            "time_increment": "1mo",
            "years_to_simulate": 20,
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
                "neighborly.plugins.defaults.names",
                "neighborly.plugins.defaults.characters",
                "neighborly.plugins.defaults.businesses",
                "neighborly.plugins.defaults.residences",
                "neighborly.plugins.defaults.ai",
                "neighborly.plugins.defaults.location_bias_rules",
                "neighborly.plugins.defaults.create_town",
                "speakeasy.plugin",
            ],
        }
    )
)


@life_event(sim)
class StartGang(ActionableLifeEvent):
    """A character starts a new gang

    At any point in the simulation the character may choose to start a new gang. Gangs
    are factions, and factions can track relationships between other factions and
    characters. Ideally, we would get characters that are ambitious to be the ones that
    start a gang.
    """

    initiator = "Initiator"

    def __init__(self, timestamp: SimDateTime, character: GameObject) -> None:
        super().__init__(timestamp, [Role("Initiator", character)])

    @property
    def character(self) -> GameObject:
        return self["Initiator"]

    @classmethod
    def instantiate(
        cls, world: World, bindings: RoleList
    ) -> Optional[ActionableLifeEvent]:
        candidate = bindings.get("Initiator")

        if candidate:
            return cls(world.get_resource(SimDateTime), candidate)

        candidates: List[GameObject] = []
        weights: List[float] = []

        for guid, _ in world.get_components((GameCharacter, Virtues, Active)):
            character = world.get_gameobject(guid)

            if character.has_component(Faction):
                continue

            if character.has_component(Child) or character.has_component(Adolescent):
                continue

            prob = cls.probability_of_starting_gang(character)

            if prob > 0.4:
                candidates.append(character)
                weights.append(prob)

        if candidates:
            chosen = world.get_resource(random.Random).choices(
                candidates, weights=weights, k=1
            )[0]
            return cls(world.get_resource(SimDateTime), chosen)

        return None

    def execute(self) -> None:
        world = self.character.world
        name_generator = world.get_resource(Tracery)

        gang_name: str = name_generator.generate("#gang_name#")

        gang = world.spawn_gameobject([Name(gang_name), IsFaction()], name=gang_name)

        self.character.add_component(Faction(gang_name, gang.uid))

    @staticmethod
    def probability_of_starting_gang(character: GameObject) -> float:
        virtues = character.get_component(Virtues)
        virtue_sum = max(
            0, virtues[Virtue.AMBITION] + virtues[Virtue.POWER] + virtues[Virtue.WEALTH]
        )
        return min(1.0, (float(virtue_sum) / 100.0))

    def get_priority(self) -> float:
        return self.probability_of_starting_gang(self.character)


@life_event(sim)
class JoinGang(ActionableLifeEvent):
    initiator = "Initiator"

    def __init__(
        self, timestamp: SimDateTime, character: GameObject, gang: GameObject
    ) -> None:
        super().__init__(
            timestamp, [Role("Initiator", character), Role("Gang", gang)]
        )

    @property
    def character(self) -> GameObject:
        return self["Initiator"]

    @property
    def gang(self) -> GameObject:
        return self["Gang"]

    @staticmethod
    def _bind_initiator(world: World, candidate: Optional[GameObject] = None):
        if candidate:
            return candidate

        candidates: List[GameObject] = []
        weights: List[float] = []

        for guid, _ in world.get_components((GameCharacter, Virtues, Active)):
            character = world.get_gameobject(guid)

            if character.has_component(Faction):
                continue

            if character.has_component(Child) or character.has_component(Adolescent):
                continue

            prob = JoinGang.probability_of_joining_gang(character)

            if prob > 0.4:
                candidates.append(character)
                weights.append(prob)

        if candidates:
            return world.get_resource(random.Random).choices(
                candidates, weights=weights, k=1
            )[0]

        return None

    @staticmethod
    def _bind_gang(world: World, candidate: Optional[GameObject] = None):
        if candidate and candidate.has_component(IsFaction):
            return candidate

        candidates: List[GameObject] = []

        for guid, _ in world.get_components((IsFaction,)):
            gang = world.get_gameobject(guid)
            candidates.append(gang)

        if candidates:
            return world.get_resource(random.Random).choice(candidates)

        return None

    @classmethod
    def instantiate(
        cls, world: World, bindings: RoleList
    ) -> Optional[ActionableLifeEvent]:
        initiator = cls._bind_initiator(world, bindings.get("Initiator"))

        if initiator is None:
            return

        gang = cls._bind_gang(world, bindings.get("Gang"))

        if gang is None:
            return

        return cls(world.get_resource(SimDateTime), initiator, gang)

    def execute(self) -> None:
        world = self.character.world
        name_generator = world.get_resource(Tracery)

        gang_name: str = name_generator.generate("#gang_name#")

        while not gang_name:
            gang_name = name_generator.generate("#gang_name#")

        gang = world.spawn_gameobject([Name(gang_name), IsFaction()])

        self.character.add_component(Faction(gang_name, gang.uid))

    @staticmethod
    def probability_of_joining_gang(character: GameObject) -> float:
        virtues = character.get_component(Virtues)
        virtue_sum = max(
            0,
            virtues[Virtue.AMBITION]
            + virtues[Virtue.POWER]
            + virtues[Virtue.WEALTH]
            + virtues[Virtue.LOYALTY]
            + virtues[Virtue.FAMILY],
        )
        return min(1.0, (float(virtue_sum) / 100.0))

    def get_priority(self) -> float:
        return self.probability_of_joining_gang(self.character)


def main() -> None:
    load_names(
        sim.world, "gang_name", pathlib.Path(__file__).parent / "gang_names.txt"
    )
    sim.run_for(sim.config.years_to_simulate)


if __name__ == "__main__":
    main()
