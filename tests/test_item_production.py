from neighborly import SimDateTime, World

from speakeasy.components import Inventory, Produces
from speakeasy.systems import ProduceItemsSystem


def test_produces() -> None:
    world = World()

    world.add_resource(SimDateTime())

    # Have to change the system group for the test to run successfully
    ProduceItemsSystem.sys_group = "root"
    world.add_system(ProduceItemsSystem())

    smith_shop = world.spawn_gameobject([
        Produces({"sword": 1, "armor": 1}, {"iron ore": 2}),
        Inventory()
    ])

    inventory = smith_shop.get_component(Inventory)

    world.step()

    assert inventory.get_quantity("sword") == 0
    assert inventory.get_quantity("armor") == 0

    # Add resources to inventory
    inventory.add_item("iron ore", 10)

    world.step()

    assert inventory.get_quantity("sword") == 1
    assert inventory.get_quantity("armor") == 1

    world.step()

    assert inventory.get_quantity("sword") == 2
    assert inventory.get_quantity("armor") == 2
