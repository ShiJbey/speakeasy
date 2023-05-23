# Speakeasy

*Speakeasy* is a character-driven emergent narrative simulation of a 1920's Prohibition-era American
town built with [Neighborly](https://github.com/ShiJbey/neighborly). The theme for this simulation
was inspired by games like *City of Gangsters* and *Empire of Sin*.

## Setup local for local development

```bash
# Step 1: Clone repo and change into the project directory
git clone https://github.com/ShiJbey/speakeasy
cd speakeasy

# Step 2: Create a Python virtual environment to manage dependencies
python -m venv venv

# Step 3 (MacOS & Linux): Activate the virtual environment
source ./venv/bin/activate

# Step 3 (Windows Powershell): Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Step 4: Install speakeasy as an editable install and install dependencies
python -m pip install -e ".[development]"

# Step 5: Test installation
python

>>> import speakeasy
```

## Running the simulation

```bash
python main.py
```

The simulation runs for a few decades of in-simulation time. During which it wil generate a new
town, spawn residents, and play out the events of their lives. Characters join gangs, trade goods,
do favors, etc. At the end, the entire history of the simulation is exported to JSON
