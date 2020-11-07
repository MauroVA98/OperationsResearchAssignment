"""
The Bay Assignment Problem
Authors: Mauro, Luke   2020
"""
# Importing modules
from collections import defaultdict, ChainMap
from operator import not_
from pulp import LpProblem, LpMinimize, lpSum, LpInteger, LpVariable, LpStatus, value
from datetime import datetime, timedelta

from flight_schedule import Scheduler, cat_list


def flight_check(flights: list):
    for idx, flight in enumerate(flights):
        flights[idx] = str("".join(x for x in flight if x not in ["P", "A", "D"]))
    return not flights or flights.count(flights[0]) == len(flights)


class LPSolver(object):
    def __init__(self, nflights: int, date: datetime = datetime(2010, 6, 15), tbuf: dict = None,
                 plotting: bool = False):

        self.__schedule = Scheduler(nflights, date=date, plotting=plotting)
        if tbuf is None:
            tbuf = {"arr": timedelta(minutes=15), "dep": timedelta(minutes=15)}
        self.__tbuf = tbuf

        self.__ac = self.__schedule.return_ac()

        self.__bays = self.__schedule.return_bays()
        self.__terminals = self.__schedule.return_termianls()
        self.__ter_penalty = 100  # penalty multiplier for inappropriate terminal

        self.__turns = self.__schedule.return_turns()
        self.__lturns = self.__schedule.return_lturns()
        # create chain map of all turns
        self.__map_turns = ChainMap(self.__turns, self.__lturns["FULL"], self.__lturns["SPLIT"])

        self.__costs_turns = defaultdict(lambda: defaultdict(dict))
        self.__costs_tows = {}

        # USE .get() to avoid unnecessary adjacency constraints
        self.__adj = {"INT": {"L": {"L": {"H": cat_list(["G", "H"]), "G": cat_list(["G", "H"])},
                                    "S": {"H": cat_list(["F", "G"]), "G": ["G"]}},
                              "S": {"S": {"G": ["G"]}}},
                      "DOM": {"L": {"L": {"G": cat_list(["F", "G"]), "F": ["G"]},
                                    "S": {"G": ["E"]}},
                              "S": {"S": {"E": ["E"]}}}}

        self.__keys_bays = [(ter, k) for ter in self.__bays for k in self.__bays[ter]]
        self.__keys = [(i, ter, k) for i in self.__map_turns for ter in self.__bays for k in self.__bays[ter]]

        # get costs matrices for turns and tows for objective function
        self.get_costs_turns()
        self.get_costs_tows()

        # Creates the 'prob' variable to contain the problem data
        self.__prob = LpProblem("Bay_Assignment", LpMinimize)
        self.__var_tows = LpVariable.dicts("w", ([i for i in self.__lturns["FULL"]]), 0, 1, LpInteger)
        self.__var_turns = LpVariable.dicts("x", ([i for i in self.__map_turns], [ter for ter in self.__bays],
                                                  [k for ter in self.__bays for k in self.__bays[ter]]), 0, 1, LpInteger)
        self.make_objf()
        self.make_const()

        self.solve()

    def ac_data(self, flight: str):
        return self.__ac[
            list(self.__ac.keys())[[self.__ac[x]["AC"] for x in self.__ac].index(self.__map_turns[flight]["AC"])]]

    def get_costs_turns(self):
        for i in self.__map_turns:
            a = 3 if ("P" in i) or ("A" in i) or ("D" in i) else 1
            for ter, k in self.__keys_bays:
                if self.__map_turns[i]["ter"] == ter:
                    self.__costs_turns[i][ter][k] = self.ac_data(flight=i)["cap"] * self.__bays[ter][k]["dist"] / a
                else:
                    self.__costs_turns[i][ter][k] = self.__ter_penalty * self.ac_data(flight=i)["cap"] * \
                                                    self.__bays[ter][k]["dist"] / a
            if "pref" in self.__map_turns[i]:
                ter_pref = self.__map_turns[i]["pref"]["ter"]
                bay_pref = self.__map_turns[i]["pref"]["bay"]
                pref = self.__map_turns[i]["pref"]["val"]
                self.__costs_turns[i][ter_pref][bay_pref] = self.__costs_turns[i][ter_pref][bay_pref] / pref

    def get_costs_tows(self):
        tow_cat = {"A": 4000, "B": 4000, "C": 400, "D": 5000, "E": 5000, "F": 5000, "G": 9000, "H": 9000}
        for i in self.__lturns["FULL"]:
            self.__costs_tows[i] = tow_cat[self.ac_data(flight=i)["cat"]]

    def make_objf(self):
        self.__prob += lpSum(
            [self.__var_turns[i][ter][k] * self.__costs_turns[i][ter][k] for (i, ter, k) in self.__keys] +
            [self.__var_tows[t] * self.__costs_tows[t] for t in self.__lturns["FULL"]]), "obj_fun"

    def make_const(self):
        self.bay_const()
        self.asg_const()
        self.tow_const()
        self.time_const()
        self.adj_const()

    def bay_const(self):
        for (i, ter, k) in self.__keys:
            if self.ac_data(flight=i)["cat"] not in self.__bays[ter][k]["cat"]:
                self.__prob += lpSum(self.__var_turns[i][ter][k]) == 0, \
                               "AircraftConstraint_Terminal:%s_Bay:%s_Flight:%s" % (ter, k, i)
            elif i[-1] == "P" and k <= self.__terminals[ter]["L"]["num"] + self.__terminals[ter]["S"]["num"]:
                self.__prob += lpSum(self.__var_turns[i][ter][k]) == 0, \
                               "ParkingConstraint_Terminal:%s_Bay:%s_Flight:%s" % (ter, k, i)

    def asg_const(self):
        for i in self.__turns:
            self.__prob += lpSum([self.__var_turns[i][ter][k] for ter in self.__bays for k in self.__bays[ter]]) == 1, \
                           "AssignmentConstraint_Flight:%s" % i
        for l in self.__lturns["FULL"]:
            self.__prob += lpSum(self.__var_tows[l] + [self.__var_turns[l][ter][k] for ter in self.__bays for k in
                                                       self.__bays[ter]]) == 1, "AssignmentConstraint_FullFlight:%s" % l
        for s in self.__lturns["SPLIT"]:
            self.__prob += lpSum(self.__var_tows[str("".join(x for x in s if x not in ["P", "A", "D"]))] -
                                 [self.__var_turns[s][ter][k] for ter in self.__bays for k in self.__bays[ter]]) == 0, \
                           "AssignmentConstraint_SplitFlight:%s" % s

    def time_const(self):
        for idx, i1 in enumerate(list(self.__map_turns.keys())):
            arr1, dep1 = self.get_tbuf(flight=i1)
            for i2 in list(self.__map_turns.keys())[idx + 1:]:
                arr2, dep2 = self.get_tbuf(flight=i2)
                if not flight_check(flights=[i1, i2]) and ((arr1 <= arr2 <= dep1 or arr1 <= dep2 <= dep1) or
                                                           (arr2 <= arr1 and dep2 >= dep1)):
                    for ter, k in self.__keys_bays:
                        if self.ac_data(flight=i1)["cat"] in self.__bays[ter][k]['cat'] and \
                                self.ac_data(flight=i2)["cat"] in self.__bays[ter][k]["cat"]:
                            self.__prob += lpSum(self.__var_turns[i1][ter][k] + self.__var_turns[i2][ter][k]) <= 1, \
                                           "TimeConstraint_Terminal:%s_Bay:%s&%s_Flights:%s&%s" % (ter, k, k + 2, i1, i2)

    def get_tbuf(self, flight):
        arr = self.__map_turns[flight]["ETA"]
        dep = self.__map_turns[flight]["ETD"]
        if "A" in flight:
            arr -= self.__tbuf["arr"]
        elif "D" in flight:
            dep += self.__tbuf["dep"]
        elif "P" not in flight:
            arr -= self.__tbuf["arr"]
            dep += self.__tbuf["dep"]
        return arr, dep

    def tow_const(self):
        for l in self.__lturns["FULL"]:
            if self.__lturns["FULL"][l].get("tow"):
                self.__prob += lpSum(self.__var_tows[l]) == 1, "TowConstraintFlight:%s" % l

    def adj_const(self):
        for idx, i1 in enumerate(list(self.__map_turns.keys())):
            for ter, k in self.__keys_bays:
                for i2 in list(self.__map_turns.keys())[idx + 1:]:
                    if flight_check(flights=[i1, i2]) and self.ac_data(flight=i1)["cat"] in \
                            self.__bays[ter].get(k, {}).get('cat', []) and self.ac_data(flight=i2)["cat"] in \
                            self.__bays[ter].get(k + 2, {}).get('cat', []) and self.ac_data(flight=i2)["cat"] in \
                            self.__adj[ter].get(self.__bays[ter][k]["size"], {}).get(self.__bays[ter].get(k + 2, {})
                            .get("size"), {}).get(self.ac_data(flight=i1)["cat"], []):
                        self.__prob += lpSum(self.__var_turns[i1][ter][k] + self.__var_turns[i2][ter][k + 2]) == 0, \
                                       "AdjacencyConstraint_Ter:%s_Bay:%s_Flights:%s&%s" % (ter, k, i1, i2)

    def writeLP(self):
        # The problem data is written to an .lp file
        self.__prob.writeLP("BayAssignmentProblem.lp")

    def solve(self):
        self.writeLP()
        # The problem is solved using PuLP's choice of Solver
        self.__prob.solve()

        # The status of the solution is printed to the screen
        print("Status:", LpStatus[self.__prob.status])

        # Each of the variables is printed with it's resolved optimum value
        for v in self.__prob.variables():
            if v.varValue == 1:
                print(v.name, "=", v.varValue)

        # The optimised objective function value is printed to the screen
        print("Objective Function Value = ", value(self.__prob.objective))


if __name__ == "__main__":
    solver = LPSolver(nflights=50, plotting=False)
