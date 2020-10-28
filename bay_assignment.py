"""
The Bay Assignment Problem
Authors: Mauro, Luke   2020
"""
# Importing modules
from collections import defaultdict, ChainMap
from pulp import LpProblem, LpMinimize, lpSum, LpInteger, LpVariable, LpStatus, value
from math import ceil
from datetime import datetime, timedelta

from flight_schedule import Scheduler


def cat_list(start: str, end: str):
    w = [chr(i) for i in range(ord(start), ord(end) + 1)]
    return w[::-1]

def get_flightn(flights):
    lst = []
    for f in flights:
        if isinstance(f, int):
            n = f
        else:
            n = int(f[0])
        lst.append(n)
    return lst


class LPSolver(object):
    def __init__(self, date: datetime = datetime(1, 1, 1), arr_buf: timedelta = timedelta(minutes=15),
                 dep_buf: timedelta = timedelta(minutes=15)):

        self.__schedule = Scheduler(date)
        self.__turns = self.__schedule.return_turns()
        self.__lturns = self.__schedule.return_lturns()
        self.__ac = self.__schedule.return_ac()

        self.__arr_buf = arr_buf
        self.__dep_buf = dep_buf

        # bay variables
        self.__terminals = ["A", "B"]  # A: domestic + continental terminal / B: international terminal
        self.__nbays = {"A": 15, "B": 10}
        self.__ter_penalty = 100  # penalty multiplier for inappropriate terminal
        self.__bdis = 30

        self.__int_lbays = 4
        self.__int_sbays = 4
        self.__dom_lbays = 4
        self.__dom_sbays = 6

        self.__bays = defaultdict(dict)
        self.__costs_turns = defaultdict(lambda: defaultdict(dict))
        self.__const_adf = defaultdict(lambda: defaultdict(dict))
        self.__tconf = []
        self.__costs_tows = {}

        # create chain map of all turns
        self.__map_turns = ChainMap(self.__turns, self.__lturns["FULL"], self.__lturns["SPLIT"])

        # create bay data dictionary
        self.get_bays(terminals=self.__terminals, nbays=self.__nbays)

        self.__keys_bays = [(ter, k) for ter in self.__bays for k in self.__bays[ter]]
        self.__keys = [(i, ter, k) for i in self.__map_turns for ter in self.__bays for k in self.__bays[ter]]

        # get costs matrices for turns and tows for objective function
        self.get_costs_turns()
        self.get_costs_tows()

        self.get_tconf()

        # Creates the 'prob' variable to contain the problem data
        self.__prob = LpProblem("Bay_Assignment", LpMinimize)
        self.__var_tows = LpVariable.dicts("w", ([i for i in self.__lturns["FULL"]]), 0, 1, LpInteger)
        self.__var_turns = LpVariable.dicts("x", ([i for i in self.__map_turns], [ter for ter in self.__bays],
                                                [k for ter in self.__bays for k in self.__bays[ter]]), 0, 1, LpInteger)
        self.make_objf()
        self.make_cons()

        self.writeLP()
        self.solve()

    def get_bays(self, terminals: list, nbays: dict):
        for ter in terminals:
            for k in range(1, nbays[ter]+1):
                if ter == "B":
                    if k <= self.__int_lbays:
                        self.__bays[ter][k] = {"type": "INT", "cat": cat_list("B", "H"), "dist": ceil(k / 2) * 4 - 2,
                                               "size": "L"}
                    elif k <= self.__int_lbays + self.__int_sbays:
                        self.__bays[ter][k] = {"type": "INT", "cat": cat_list("B", "G"), "dist": ceil(k / 2) * 3 - 0.5,
                                               "size": "S"}
                    else:
                        self.__bays[ter][k] = {"type": "INT", "cat": cat_list("A", "G"), "dist": self.__bdis}
                elif ter == "A":
                    if k <= self.__dom_lbays:
                        self.__bays[ter][k] = {"type": "DOM", "cat": cat_list("B", "G"), "dist": ceil(k / 2) * 3 - 1.5,
                                               "size": "L"}
                    elif k <= self.__dom_lbays + self.__dom_sbays:
                        self.__bays[ter][k] = {"type": "DOM", "cat": cat_list("B", "E"), "dist": ceil(k / 2) * 2,
                                               "size": "S"}
                    else:
                        self.__bays[ter][k] = {"type": "DOM", "cat": cat_list("A", "G"), "dist": self.__bdis}

    def get_costs_turns(self):
        for i in self.__map_turns:
            a = 1 if isinstance(i, int) else 3
            for ter, k in self.__keys_bays:
                if self.__map_turns[i]["type"] == self.__bays[ter][k]["type"]:
                    self.__costs_turns[i][ter][k] = self.__ac[self.__map_turns[i]["AC"]]["cap"] * \
                                             self.__bays[ter][k]["dist"] / a
                else:
                    self.__costs_turns[i][ter][k] = self.__ter_penalty * self.__ac[self.__map_turns[i]["AC"]]["cap"] * \
                                        self.__bays[ter][k]["dist"]/a

            if "PREF" in self.__map_turns[i]:
                ter_pref = self.__map_turns[i]["PREF"]["ter"]
                bay_pref = self.__map_turns[i]["PREF"]["bay"]
                val_pref = self.__map_turns[i]["PREF"]["val"]
                self.__costs_turns[i][ter_pref][bay_pref] = self.__costs_turns[i][ter_pref][bay_pref] / val_pref

    def get_costs_tows(self):
        tow_cat = {"A": 3000, "B": 3000, "C": 4500, "D": 4500, "E": 4500, "F": 4500, "G": 9000, "H": 9000}
        for i in self.__lturns["FULL"]:
            self.__costs_tows[i] = tow_cat[self.__ac[self.__lturns["FULL"][i]["AC"]]["cat"]]

    def get_tconf(self):
        for idx, i1 in enumerate(list(self.__map_turns.keys())):
            arr1, dep1 = self.get_buft(flight=i1)
            for i2 in list(self.__map_turns.keys())[idx + 1:]:
                arr2, dep2 = self.get_buft(flight=i2)
                [n1, n2] = get_flightn(flights=[i1, i2])
                if (arr1 <= arr2 <= dep1 or arr1 <= dep2 <= dep1 or (arr2 <= arr1 and dep2 >= dep1)) and n1 != n2:
                    self.__tconf.append([i1, i2])

    def get_buft(self, flight):
        arr = self.__map_turns[flight]["ETA"]
        dep = self.__map_turns[flight]["ETD"]
        if isinstance(flight, int):
            arr -= self.__arr_buf
            dep += self.__dep_buf
        else:
            if flight[-1] == "A":
                arr -= self.__arr_buf
            elif flight[-1] == "D":
                dep += self.__dep_buf
        return arr, dep

    def make_objf(self):
        self.__prob += lpSum([self.__var_turns[i][ter][k] * self.__costs_turns[i][ter][k] for (i, ter, k) in self.__keys] +
                             [self.__var_tows[t] * self.__costs_tows[t] for t in self.__lturns["FULL"]]), "obj_fun"

    def make_cons(self):
        self.const_bay()
        self.const_asg()
        self.const_t()
        self.const_tow()
        self.make_const_adj()

    def const_bay(self):
        for (i, ter, k) in self.__keys:
            if self.__ac[self.__map_turns[i]["AC"]]["cat"] not in self.__bays[ter][k]["cat"]:
                self.__prob += lpSum(self.__var_turns[i][ter][k]) == 0, "AircraftConstraint_Ter:%s_Bay:%s_Flight:%s" % (ter, k, i)
            elif (isinstance(i, str) and i[-1] == "P") and ((ter == "A" and k <= self.__dom_lbays + self.__dom_sbays) or
                                                            (ter == "B" and k <= self.__int_lbays + self.__int_sbays)):
                self.__prob += lpSum(self.__var_turns[i][ter][k]) == 0, "ParkingConstraint_Ter:%s_Bay:%s_Flight:%s" % (ter, k, i)

    def const_asg(self):
        for i in self.__turns:
            self.__prob += lpSum(
                [self.__var_turns[i][ter][k] for ter in self.__bays for k in self.__bays[ter]]) == 1, \
                                        "AssignmentConstraint_Flight:%s" % i
        for t in self.__lturns["FULL"]:
            self.__prob += lpSum(self.__var_tows[t] + [self.__var_turns[t][ter][k] for ter in self.__bays
                                        for k in self.__bays[ter]]) == 1, "AssignmentConstraintFull_Flight:%s" % t
        for i in self.__lturns["SPLIT"]:
            self.__prob += lpSum(-self.__var_tows[int("".join(x for x in i if x not in "PAD"))] +
                                 [self.__var_turns[i][ter][k] for ter in self.__bays for k in self.__bays[ter]]) == 0, \
                                        "AssignmentConstraintSplit_Flight:%s" % i

    def const_t(self):
        for x in self.__tconf:
            for ter, k in self.__keys_bays:
                self.__prob += lpSum(self.__var_turns[x[0]][ter][k] + self.__var_turns[x[1]][ter][k]) <= 1, \
                               "TimeConstraint_Ter:%s_Bay:%s_Flights:%s&%s" % (ter, k, x[0], x[1])

    def const_tow(self):
        for i in self.__lturns["FULL"]:
            if self.__lturns["FULL"][i].get("tow"):
                self.__prob += lpSum(self.__var_tows[i]) == 1, "TowConstraintFlight:%s" % i

    def make_const_adj(self):
        self.__const_adf["INT"]["L"]["L"] = dict.fromkeys(["H", "G"], cat_list("B", "F"))
        self.__const_adf["INT"]["L"]["L"].update(dict.fromkeys(["F", "E", "D", "C", "B"], cat_list("B", "H")))
        self.__const_adf["INT"]["L"]["S"] = {"H": cat_list("B", "F"), "G": cat_list("B", "F"), "F": cat_list("B", "F")}
        self.__const_adf["INT"]["S"]["S"] = {"H": cat_list("B", "F"), "G": cat_list("B", "F"), "F": cat_list("B", "F")}
        self.__const_adf["DOM"]["L"]["L"] = {"H": cat_list("B", "F"), "G": cat_list("B", "F"), "F": cat_list("B", "F")}
        self.__const_adf["DOM"]["L"]["S"] = {"H": cat_list("B", "F"), "G": cat_list("B", "F"), "F": cat_list("B", "F")}
        self.__const_adf["DOM"]["S"]["S"] = {"H": cat_list("B", "F"), "G": cat_list("B", "F"), "F": cat_list("B", "F")}

        for idx, i1 in enumerate(list(self.__map_turns.keys())):
            for ter, k in self.__keys_bays:
                for i2 in list(self.__map_turns.keys())[idx + 1:]:
                    [n1, n2] = get_flightn(flights=[i1,i2])
                    if n1 != n2 and ((ter == "A" and k <= self.__dom_lbays + self.__dom_sbays - 2) or
                                    (ter == "B" and k <= self.__int_lbays + self.__int_sbays - 2)) and \
                            self.__ac[self.__map_turns[i1]["AC"]]["cat"] in self.__bays[ter][k]["cat"] and \
                            self.__ac[self.__map_turns[i2]["AC"]]["cat"] in self.__bays[ter][k + 2]["cat"] and \
                            self.__ac[self.__map_turns[i2]["AC"]]["cat"] not in \
                            self.__const_adf[self.__bays[ter][k]["type"]][self.__bays[ter][k]["size"]][
                            self.__bays[ter][k + 2]["size"]][self.__ac[self.__map_turns[i1]["AC"]]["cat"]]:
                                self.__prob += lpSum(self.__var_turns[i1][ter][k] + self.__var_turns[i2][ter][k+2]) == 0,\
                                               "AdjacencyConstraint_Ter:%s_Bay:%s_Flights:%s&%s" % (ter, k, i1, i2)

    def writeLP(self):
        # The problem data is written to an .lp file
        self.__prob.writeLP("BayAssignmentProblem.lp")

    def solve(self):
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
    solver = LPSolver()
