"""
The Bay Assignment Problem
Authors: Mauro, Luke    2020
"""
# Importing modules
from collections import defaultdict
from pulp import LpProblem, LpMinimize, lpSum, LpInteger, LpVariable, LpStatus, value
from math import ceil
import datetime as dt

from flight_schedule import schedule, ac_dict


def pref(index, val):
    costs[index[0]][index[1]] = costs[index[0]][index[1]]*(1/val)


def get_dt(t: dt.time):
    return dt.datetime(1, 1, 1, t.hour, t.minute)


def alp_list(start: str, end: str):
    w = [chr(i) for i in range(ord(start), ord(end) + 1)]
    return w[::-1]


# variables
# start time, end time, buffer times
t_start = dt.time(hour=8, minute=0)
t_end = dt.time(hour=22, minute=0)

tarr_buf = dt.timedelta(minutes=15)
tdep_buf = dt.timedelta(minutes=15)

# terminals and amount of gates
terminals = ["A", "B"]  # A: domestic + continental terminal / B: international terminal
n_bays = [15, 10]

bays = {}
costs = defaultdict(dict)
t_penalty = 20

# Create a dictionary with bays
for idx, ter in enumerate(terminals):
    for b in range(1, n_bays[idx] + 1):
        if ter == "B":
            if b <= 2:
                bays[ter + str(b)] = {"dist": ceil(b / 2) * 4 - 2, "cat": alp_list("B", "H"), "type": "INT"}
            elif 2 < b <= 8:
                bays[ter + str(b)] = {"dist": ceil(b / 2) * 3 - 0.5, "cat": alp_list("B", "G"), "type": "INT"}
            else:
                bays[ter + str(b)] = {"dist": 20, "cat": alp_list("A", "G"), "type": "INT"}
        elif ter == "A":
            if b <= 2:
                bays[ter + str(b)] = {"dist": ceil(b / 2) * 3 - 1.5, "cat": alp_list("B", "H"), "type": "DOM"}
            elif 2 < b <= 10:
                bays[ter + str(b)] = {"dist": ceil(b / 2) * 2, "cat": alp_list("B", "E"), "type": "DOM"}
            else:
                bays[ter + str(b)] = {"dist": 20, "cat": alp_list("A", "G"), "type": "DOM"}

# create cost matrix
for i in schedule:
    for k in bays:
        if schedule[i]["type"] == bays[k]["type"]:
            costs[i][k] = ac_dict[schedule[i]["ac"]]["cap"] * bays[k]["dist"]
        else:
            costs[i][k] = t_penalty*ac_dict[schedule[i]["ac"]]["cap"] * bays[k]["dist"]

# specific flight/bay preferences
# 1 (no preference) - 10 (high preference)
pref((3, "B2"), 10)
pref((2, "B2"), 5)

# Creates the 'prob' variable to contain the problem data
prob = LpProblem("Bay_Assignment", LpMinimize)

# Creates a list of tuples containing all the possible combinations of flight and bays
keys = [(i, k) for i in schedule for k in bays]

# A dictionary called 'Vars' is created to contain the referenced variables
var = LpVariable.dicts("X", ([i for i in schedule], [k for k in bays]), 0, 1, LpInteger)

# The objective function is added to 'prob' first
prob += lpSum([var[i][k] * costs[i][k] for (i, k) in keys]), "obj_fun"

t_conf = []
for n in schedule:
    n_arr = get_dt(schedule[n]["ETA"]) - tarr_buf
    n_dep = get_dt(schedule[n]["ETD"]) + tdep_buf

    for x in range(n+1, schedule.__len__()+1):
        x_arr = get_dt(schedule[x]["arrival"]["ETA"]) - tarr_buf
        x_dep = get_dt(schedule[x]["departure"]["ETD"]) + tdep_buf

        if n_arr <= x_arr <= n_dep or n_arr <= x_dep <= n_dep:
            t_conf.append([n, x])

av_bays = {}
for f in schedule:
    l = []
    for b in bays:
        if ac_dict[schedule[f]["ac"]]["cat"] not in bays[b]["cat"]:
            prob += lpSum(var[b][f]) == 0, "Bay_Constraint:%s_%s" % (b, f)
        else:
            l.append(b)
    prob += lpSum(var[b][f] for b in l) == 1, "Assignment_Constraint:%s" % f
    av_bays[f] = l

for c in t_conf:
    for z in av_bays[c[0]]:
        if z in av_bays[c[1]]:
            prob += lpSum(var[z][c[0]] + var[z][c[1]]) <= 1, "TimeSlot_Constraint:%s_%s_%s" % (z, c[0], c[1])


# Solving LP Problem
# The problem data is written to an .lp file
prob.writeLP("BayAssignmentProblem.lp")

# The problem is solved using PuLP's choice of Solver
prob.solve()

# The status of the solution is printed to the screen
print("Status:", LpStatus[prob.status])

# Each of the variables is printed with it's resolved optimum value
for v in prob.variables():
    if v.varValue == 1:
        print(v.name, "=", v.varValue)

# The optimised objective function value is printed to the screen
print("Objective Function Value = ", value(prob.objective))