from neighborly import Neighborly, NeighborlyConfig

sim = Neighborly(
    NeighborlyConfig.parse_obj(
        {
            "plugins": [
                "speakeasy.plugin"
            ]
        }
    )
)

def main():
    print(sim)


if __name__ == "__main__":
    main()
