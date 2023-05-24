"""
One of the problems with this project is determining how to author actions.
"""
import pathlib
import random
from typing import ClassVar, Dict, List, Optional

from neighborly import GameObject, Neighborly, NeighborlyConfig, SimDateTime, World
from neighborly.components import GameCharacter, LifeStage, Name, Virtue, Virtues
from neighborly.components.character import LifeStageType
from neighborly.core.ecs import Active
from neighborly.core.life_event import RandomLifeEvent
from neighborly.core.roles import Role, RoleList
from neighborly.core.tracery import Tracery
from neighborly.decorators import random_life_event
from neighborly.loaders import load_names
from neighborly.core.ai.brain import ConsiderationList

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
                "neighborly.plugins.defaults.all",
                "neighborly.plugins.talktown.spawn_tables",
                "neighborly.plugins.talktown",
                "speakeasy.plugin"
            ],
        }
    )
)


@random_life_event()
class StartGangEvent(RandomLifeEvent):
    """A character starts a new gang.

    Notes
    -----
    At any point in the simulation the character may choose to start a new gang. Gangs
    are factions, and factions can track relationships between other factions and
    characters. Ideally, we would get characters that are ambitious to be the ones that
    start a gang.
    """

    considerations: Dict[str, ConsiderationList] = {
        "Initiator": ConsiderationList([
            lambda gameobject: (
                (gameobject.get_component(Virtues)[Virtue.AMBITION] + 50.0) / 100.0
            ),
            lambda gameobject: (
                (gameobject.get_component(Virtues)[Virtue.POWER] + 50.0) / 100.0
            ),
            lambda gameobject: (
                (gameobject.get_component(Virtues)[Virtue.WEALTH] + 50.0) / 100.0
            )
        ])
    }

    def __init__(self, timestamp: SimDateTime, character: GameObject) -> None:
        super().__init__(timestamp, [Role("Initiator", character)])

    @property
    def character(self) -> GameObject:
        return self["Initiator"]

    @classmethod
    def instantiate(cls, world: World, bindings: RoleList) -> Optional[RandomLifeEvent]:
        candidate = bindings.get("Initiator")

        if candidate:
            return cls(world.get_resource(SimDateTime), candidate)

        candidates: List[GameObject] = []
        weights: List[float] = []

        for guid, _ in world.get_components((GameCharacter, Virtues, Active)):
            character = world.get_gameobject(guid)

            if character.has_component(Faction):
                continue

            if (
                character.get_component(LifeStage).life_stage
                <= LifeStageType.Adolescent
            ):
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

        self.character.add_component(Faction(gang.uid))

    @classmethod
    def probability_of_starting_gang(cls, character: GameObject) -> float:
        return cls.considerations["Initiator"].calculate_score(character)

    def get_probability(self) -> float:
        return StartGangEvent.probability_of_starting_gang(self.character)


@random_life_event()
class JoinGangEvent(RandomLifeEvent):

    JOIN_GANG_UTILITY_THRESH: ClassVar[float] = 0.4

    considerations: ClassVar[Dict[str, ConsiderationList]] = {
        "Initiator": ConsiderationList(
            [
                lambda gameobject: (
                    (gameobject.get_component(Virtues)[Virtue.AMBITION] + 50.0) / 100.0
                ),
                lambda gameobject: (
                    (gameobject.get_component(Virtues)[Virtue.POWER] + 50.0) / 100.0
                ),
                lambda gameobject: (
                    (gameobject.get_component(Virtues)[Virtue.WEALTH] + 50.0) / 100.0
                ),
                lambda gameobject: (
                    (gameobject.get_component(Virtues)[Virtue.LOYALTY] + 50.0) / 100.0
                ),
                lambda gameobject: (
                    (gameobject.get_component(Virtues)[Virtue.FAMILY] + 50.0) / 100.0
                ),
                lambda gameobject: 0 if gameobject.has_component(Faction) else None,
                lambda gameobject: (
                    0 if gameobject.get_component(LifeStage).life_stage
                    <= LifeStageType.Adolescent
                    else
                    None
                )
            ]
        )
    }

    def __init__(
        self, timestamp: SimDateTime, character: GameObject, gang: GameObject
    ) -> None:
        super().__init__(timestamp, [Role("Initiator", character), Role("Gang", gang)])

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

            prob = JoinGangEvent.probability_of_joining_gang(character)

            if prob > JoinGangEvent.JOIN_GANG_UTILITY_THRESH:
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
    def instantiate(cls, world: World, bindings: RoleList) -> Optional[RandomLifeEvent]:
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

        self.character.add_component(Faction(gang.uid))

    @classmethod
    def probability_of_joining_gang(cls, character: GameObject) -> float:
        return cls.considerations["Initiator"].calculate_score(character)

    def get_probability(self) -> float:
        return self.probability_of_joining_gang(self.character)


def main() -> None:
    load_names("gang_name", pathlib.Path(__file__).parent / "gang_names.txt")
    sim.run_for(sim.config.years_to_simulate)


if __name__ == "__main__":
    main()
