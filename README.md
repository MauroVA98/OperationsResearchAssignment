# OperationsResearchAssignment

This repository contains the code for the Operations Research (AE4441) Assignment on the Robust Scheduling of the Bay Assignment Problem using a Mixed-Integer Linear Programming Model by Mauro Villanueva Aguado (4557824) & Luke de Waal (4560000).

# Set-Up Guide
1. A python enviroment (3.7-3.9)
2. The following python modules:
- numpy
- matplotlib
- pulp
- datetime
- typing
3. A CPLEX Studio Installation

# Usage Guide
1. Replace the LPSolver path with your CPLEX installation in main.py
2. Run main.py
3. You can change the seed and/or the amount of flights
4. You can plot the simulation results using the plotter method:
- len_bar = bar chart of turn durations
- ac_bar = bar chart of aircraft types
- h_bar = turn and bay visualization
5. You can further tune the probabilities of the turn schedule and bay configutation in the programdata folder
- ac.json - Aircraft Names, Capacities and Categories
- adj.json - Adjacency Contraint
- costs.json - Costs of the Objective Function
- features.json - Turn & Aircraft Category Probabilities
- scheduling.json - Start and End Time of Simulation, Minimum Tow Duration
- terminals.json - Bay Configurations
