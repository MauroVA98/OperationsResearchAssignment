"""
The Bay Assignment Problem
Authors: Mauro, Luke   2020
"""
# Importing modules
from collections import defaultdict, ChainMap
from pulp import LpProblem, LpMinimize, lpSum, LpInteger, LpVariable, LpStatus, value
from math import ceil
from datetime import datetime, timedelta, time

from flight_schedule import Scheduler


def cat_list(start: str, end: str):
    w = [chr(i) for i in range(ord(start), ord(end) + 1)]
    return w[::-1]


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
        self.__nbays = [15, 10]
        self.__ter_penalty = 100  # penalty multiplier for inappropriate terminal

        self.__int_lbays = 2
        self.__int_sbays = 6
        self.__dom_lbays = 2
        self.__dom_sbays = 8

        # create bay data dictionary
        self.__bays = self.get_bays(terminals=self.__terminals, nbays=self.__nbays)

        # create chain map of all turns
        self.__map_turns = ChainMap(self.__turns, self.__lturns["FULL"], self.__lturns["SPLIT"])

        # get costs matrices for turns and tows for objective function
        self.__costs_turns = self.get_costs_turns()
        self.__costs_tows = self.get_costs_tows()

        self.__tconf = self.get_tconf()

        # Creates the 'prob' variable to contain the problem data
        self.__prob = LpProblem("Bay_Assignment", LpMinimize)

        # Creates a list of tuples containing all the possible combinations of flight and bays
        self.__keys = [(i, k) for i in self.__map_turns for k in self.__bays]

        self.__var_turns, self.__var_tows = self.make_vars()

        self.make_objf()
        self.make_cons()

        self.writeLP()
        self.solve()

    def get_bays(self, terminals: list, nbays: list):
        bays = {}
        # Create a dictionary with bay data
        for idx, ter in enumerate(terminals):
            for k in range(1, nbays[idx] + 1):
                if ter == "B":
                    bays[ter + str(k)] = {"type": "INT"}
                    if k <= self.__int_lbays:
                        bays[ter + str(k)].update({"dist": ceil(k / 2) * 4 - 2, "cat": cat_list("B", "H")})
                    elif k <= self.__int_lbays + self.__int_sbays:
                        bays[ter + str(k)].update({"dist": ceil(k / 2) * 3 - 0.5, "cat": cat_list("B", "G")})
                    else:
                        bays[ter + str(k)].update(
                            {"dist": 10 + ceil((self.__int_lbays + self.__int_sbays) / 2) * 3 - 0.5,
                             "cat": cat_list("A", "G")})
                elif ter == "A":
                    bays[ter + str(k)] = {"type": "DOM"}
                    if k <= self.__dom_lbays:
                        bays[ter + str(k)].update({"dist": ceil(k / 2) * 3 - 1.5, "cat": cat_list("B", "H")})
                    elif k <= self.__dom_lbays + self.__dom_sbays:
                        bays[ter + str(k)].update({"dist": ceil(k / 2) * 2, "cat": cat_list("B", "E")})
                    else:
                        bays[ter + str(k)].update({"dist": 10 + ceil((self.__dom_lbays + self.__dom_sbays) / 2) * 2,
                                                   "cat": cat_list("A", "G")})
        return bays

    def get_costs_turns(self):
        # create cost matrix
        costs_turns = defaultdict(dict)
        for i in self.__map_turns:
            a = 1 if isinstance(i, int) else 3
            for k in self.__bays:
                if self.__map_turns[i]["type"] == self.__bays[k]["type"]:
                    costs_turns[i][k] = self.__ac[self.__map_turns[i]["ac"]]["cap"] * self.__bays[k]["dist"] / a
                else:
                    costs_turns[i][k] = self.__ter_penalty * self.__ac[self.__map_turns[i]["ac"]]["cap"] * \
                                        self.__bays[k]["dist"] / a

            if "PREF" in self.__map_turns[i]:
                bay_pref = self.__map_turns[i]["PREF"][0]
                pref = self.__map_turns[i]["PREF"][1]
                costs_turns[i][bay_pref] = costs_turns[i][bay_pref] / pref
        return costs_turns

    def get_costs_tows(self):
        costs_tows = {}
        tow_cat = {"A": 3000, "B": 3000, "C": 4500, "D": 4500, "E": 4500, "F": 4500, "G": 9000, "H": 9000}
        for t in self.__lturns["FULL"]:
            costs_tows[t] = tow_cat[self.__ac[self.__lturns["FULL"][t]["ac"]]["cat"]]
        return costs_tows

    def get_tconf(self):
        lst = []
        for i1 in self.__map_turns:
            arr1, dep1, n1 = self.get_buft(flight=i1)
            for i2 in self.__map_turns:
                arr2, dep2, n2 = self.get_buft(flight=i2)
                if (arr2 <= arr1 <= dep2 or arr2 <= dep1 <= dep2) and n1 != n2:
                    lst.append([i1, i2])
        # removing reversed elements in list
        lst = [v for k, v in enumerate(lst) if v[::-1] not in lst[:k] and v not in lst[:k]]
        return lst

    def get_buft(self, flight):
        arr = self.__map_turns[flight]["ETA"]
        dep = self.__map_turns[flight]["ETD"]
        if isinstance(flight, int):
            n = flight
            arr -= self.__arr_buf
            dep += self.__dep_buf
        else:
            n = int(flight[0])
            if flight[-1] == "A":
                arr -= self.__arr_buf
            elif flight[-1] == "D":
                dep += self.__dep_buf
        return arr, dep, n

    def make_vars(self):
        var_turns = LpVariable.dicts("x", ([i for i in self.__map_turns], [k for k in self.__bays]), 0, 1, LpInteger)
        var_tows = LpVariable.dicts("w", ([i for i in self.__lturns["FULL"]]), 0, 1, LpInteger)
        return var_turns, var_tows

    def make_objf(self):
        self.__prob += lpSum([self.__var_turns[i][k] * self.__costs_turns[i][k] for (i, k) in self.__keys] +
                             [self.__var_tows[t] * self.__costs_tows[t] for t in self.__lturns["FULL"]]), "obj_fun"

    def make_cons(self):
        self.make_const_bay()
        self.make_const_asg()
        self.make_const_t()

    def make_const_bay(self):
        for (i, k) in self.__keys:
            if self.__ac[self.__map_turns[i]["ac"]]["cat"] not in self.__bays[k]["cat"] or \
                    ((isinstance(i, str) and i[-1] == "P") and
                     ((k[0] == "A" and int(k.replace("A", "")) <= self.__dom_lbays + self.__dom_sbays) or
                      (k[0] == "B" and int(k.replace("B", "")) <= self.__int_lbays + self.__int_sbays))):
                self.__prob += lpSum(self.__var_turns[i][k]) == 0, "BayConstraint_Bay:%s_Flight:%s" % (i, k)

    def make_const_asg(self):
        for i in self.__turns:
            self.__prob += lpSum([self.__var_turns[i][k] for k in self.__bays]) == 1, "AssignmentConstraint_Flight:%s" % i
        for i in self.__lturns["FULL"]:
            self.__prob += lpSum(self.__var_tows[i] + [self.__var_turns[i][k] for k in self.__bays]) == 1, \
                           "AssignmentConstraint_FullTow_Flight:%s" % i
        for i in self.__lturns["SPLIT"]:
            self.__prob += lpSum(-self.__var_tows[int("".join(x for x in i if x not in "PAD"))] +
                                 [self.__var_turns[i][k] for k in self.__bays]) == 0, \
                           "AssignmentConstraint_SplitTow_Flight:%s" % i

    def make_const_t(self):
        for x in self.__tconf:
            for k in self.__bays:
                self.__prob += lpSum(self.__var_turns[x[0]][k] + self.__var_turns[x[1]][k]) <= 1, \
                               "TimeConstraint_Flights:%s&%s_Bay:%s" % (x[0], x[1], k)

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
