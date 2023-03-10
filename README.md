# Speakeasy

*Speakeasy* is a character-driven emergent narrative simulation of a 1920's Prohibition-era American
town built with [Neighborly](https://github.com/ShiJbey/neighborly). The theme for this simulation
was inspired by games like *City of Gangsters* and *Empire of Sin*.

## Installing dependencies

This simulation requires [Neighborly](https://github.com/ShiJbey/neighborly) to run. You can install
it by running the following command.

```bash
pip install git+https://github.com/ShiJbey/neighborly.git
```

## Running the simulation

```bash
python main.py
```

The simulation runs for a few decades of in-simulation time. During which it wil generate a new
town, spawn residents, and play out the events of their lives. Characters join gangs, trade goods,
do favors, etc. At the end, the entire history of the simulation is exported to JSON
