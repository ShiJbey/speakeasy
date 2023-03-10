import argparse
from neighborly import Neighborly, NeighborlyConfig
from neighborly.exporter import export_to_json

sim = Neighborly(
    NeighborlyConfig.parse_obj(
        {
            "time_increment": "1mo",
            "years_to_simulate": 10,
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
                "neighborly.plugins.defaults.names",
                "neighborly.plugins.defaults.characters",
                "neighborly.plugins.defaults.businesses",
                "neighborly.plugins.defaults.residences",
                "neighborly.plugins.defaults.ai",
                "neighborly.plugins.defaults.location_bias_rules",
                "speakeasy.plugin"
            ]
        }
    )
)

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Runs the Speakeasy simulation")

    parser.add_argument("-o", "--output", help="path to write final simulation state")

    parser.add_argument(
        "--no-emit",
        default=False,
        action="store_true",
        help="Disable creating an output file with the simulation's final state",
    )

    return parser.parse_args()

def main() -> None:

    args = get_args()

    sim.run_for(sim.config.years_to_simulate)

    if not args.no_emit:
        output_path = (
            args.output if args.output else f"speakeasy_{sim.config.seed}.json"
        )

        with open(output_path, "w") as f:
            data = export_to_json(sim)
            f.write(data)

if __name__ == "__main__":
    main()
