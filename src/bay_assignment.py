"""
The Bay Assignment Problem
Authors: Mauro, Luke   2020
"""
# Importing modules
import time
import os, json
from collections import defaultdict, ChainMap

from pulp import LpProblem, LpMinimize, lpSum, LpInteger, LpVariable, LpStatus, value, CPLEX_CMD
from datetime import datetime, timedelta

from src.flight_schedule import Scheduler, return_data

def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def make_data_serializable(data: dict):
    result = {}
    for key, value in data.items():
        key = str(key)
        if isinstance(value, dict):
            result[key] = make_data_serializable(value)
        elif isinstance(value, datetime):
            date_time = value.strftime("%Y/%m/%d %H:%M:%S")
            result[key] = date_time
        elif isinstance(value, timedelta):
            result[key] = str(value)
        elif isinstance(value, LpVariable):
            result[key] = value.name
        elif isinstance(value, CPLEX_CMD):
            continue
        else:
            if is_jsonable(value):
                result[key] = value
            else:
                if isinstance(value, list):
                    result[key] = [vi.__dict__ for vi in value]
                else:
                    result[key] = value

    return result


def remove_clone_logs():
    for file in os.listdir(os.getcwd()):
        if 'clone' in file:
            os.remove(os.path.join(os.getcwd(), file))


def flight_check(flights: list):
    for idx, flight in enumerate(flights):
        flights[idx] = str("".join(x for x in flight if x not in ["P", "A", "D"]))
    return not flights or flights.count(flights[0]) == len(flights)


def solve_time(n:int, nflights: int, solver):
    solve_times = []
    for i in range(n):
        bay_assignment = LPSolver(nflights=nflights, solver=solver)
        solve_times.append(bay_assignment.return_solvetime())
    return sum(solve_times)/len(solve_times)


class LPSolver(object):
    def __init__(self, nflights: int, solver = None, date: datetime = datetime(2010, 6, 15), tbuf: dict = None,
                 plotting: bool = False, adj_file: str = r"./programdata/adj.json", cost_file: str = r"./programdata/costs.json"):

        self.__schedule = Scheduler(nflights, date=date, plotting=plotting)
        if tbuf is None:
            tbuf = timedelta(minutes=15)
        self.__tbuf = tbuf
        self.__solver = solver

        self.__ac = self.__schedule.return_ac()

        self.__bays = self.__schedule.return_bays()
        self.__terminals = self.__schedule.return_termianls()
        self.__ter_penalty = 100  # penalty multiplier for inappropriate terminal

        self.__turns = self.__schedule.return_turns()
        self.__lturns = self.__schedule.return_lturns()
        # create chain map of all turns
        self.__map_turns = ChainMap(self.__turns, self.__lturns["FULL"], self.__lturns["SPLIT"])
        self.__map_fturns = ChainMap(self.__turns, self.__lturns["FULL"])

        self.__costs_turns = defaultdict(lambda: defaultdict(dict))
        self.__costs_tows = {}
        self.__costs_nobay = {}

        # USE .get() to avoid unnecessary adjacency constraints
        with open(adj_file, 'r') as file:
            self.__adj = json.load(file)

        self.__keys_bays = [(ter, k) for ter in self.__bays for k in self.__bays[ter]]
        self.__keys = [(i, ter, k) for i in self.__map_turns for ter in self.__bays for k in self.__bays[ter]]

        # get costs matrices for turns and tows for objective function
        with open(cost_file, 'r') as file:
            cost_data = json.load(file)
        self.costs_turns()
        self.costs_tows(cost_data['tow'])
        self.costs_nobay(cost_data['nobay'])

        # Creates the 'prob' variable to contain the problem data
        self.__prob = LpProblem("Bay_Assignment", LpMinimize)
        self.__var_tow = LpVariable.dicts("w", ([i for i in self.__lturns["FULL"]]), 0, 1, LpInteger)
        self.__var_turn = LpVariable.dicts("x", ([i for i in self.__map_turns], [ter for ter in self.__bays],
                                                 [k for ter in self.__bays for k in self.__bays[ter]]), 0, 1, LpInteger)
        self.__var_nobay = LpVariable.dicts("y", ([i for i in self.__map_fturns]), 0, 1, LpInteger)
        self.make_objf()
        self.make_const()

        self.writeLP()

        start = time.perf_counter()
        self.solve(solver=self.__solver)
        self.__solvetime = time.perf_counter() - start

    def return_solvetime(self):
        return self.__solvetime

    def ac_data(self, flight: str):
        return self.__ac[
            list(self.__ac.keys())[[self.__ac[x]["AC"] for x in self.__ac].index(self.__map_turns[flight]["AC"])]]

    def costs_turns(self):
        for i in self.__map_turns:
            for ter, k in self.__keys_bays:
                if "P" in i:
                    self.__costs_turns[i][ter][k] = 1
                else:
                    a = 2 if ("A" in i) or ("D" in i) else 1
                    if self.__map_turns[i]["ter"] == ter or ter == "BUS":
                        self.__costs_turns[i][ter][k] = self.ac_data(flight=i)["cap"] * self.__bays[ter][k]["dist"] / a
                    else:
                        self.__costs_turns[i][ter][k] = self.__ter_penalty * self.ac_data(flight=i)["cap"] * \
                                                        self.__bays[ter][k]["dist"] / a
            if "pref" in self.__map_turns[i]:
                ter_pref = self.__map_turns[i]["pref"]["ter"]
                bay_pref = self.__map_turns[i]["pref"]["bay"]
                pref = self.__map_turns[i]["pref"]["val"]
                self.__costs_turns[i][ter_pref][bay_pref] = self.__costs_turns[i][ter_pref][bay_pref] / pref

    def costs_nobay(self, nobay_cat):
        for i in self.__turns:
            self.__costs_nobay[i] = nobay_cat[self.ac_data(flight=i)["cat"]]
        for l in self.__lturns["FULL"]:
            self.__costs_nobay[l] = nobay_cat[self.ac_data(flight=l)["cat"]]

    def costs_tows(self, tow_cat):
        for l in self.__lturns["FULL"]:
            self.__costs_tows[l] = tow_cat[self.ac_data(flight=l)["cat"]]

    def make_objf(self):
        self.__prob += lpSum(
            [self.__var_turn[i][ter][k] * self.__costs_turns[i][ter][k] for (i, ter, k) in self.__keys] +
            [self.__var_tow[t] * self.__costs_tows[t] for t in self.__lturns["FULL"]] +
            [self.__var_nobay[i] * self.__costs_nobay[i] for i in self.__map_fturns]), "obj_fun"

    def make_const(self):
        self.asg_turns()
        self.asg_lturns()
        self.tow_const()
        self.adj_const()
        self.time_const()

    def asg_turns(self):
        for i in self.__turns:
            bays = defaultdict(dict)
            for ter, k in self.__keys_bays:
                if self.ac_data(flight=i)["cat"] in self.__bays[ter][k]["cat"]:
                    bays[ter][k] = True
            self.__prob += lpSum([self.__var_turn[i][ter][k] for ter in bays for k in bays[ter]] +
                                 self.__var_nobay[i]) == 1, "AssignConstFlight%s" % i

    def asg_lturns(self):
        for l in self.__lturns["FULL"]:
            bays = defaultdict(dict)
            bays_split = defaultdict(dict)
            bays_park = defaultdict(dict)
            for ter, k in self.__keys_bays:
                if self.ac_data(flight=l)["cat"] in self.__bays[ter][k]["cat"]:
                    bays[ter][k] = True
                    if ter != "BUS":
                        bays_split[ter][k] = True
                    else:
                        bays_park[ter][k] = True
            self.__prob += lpSum(self.__var_tow[l] + self.__var_nobay[l] + [self.__var_turn[l][ter][k] for ter in bays \
                                for k in bays[ter]]) == 1, "AssignConstraintFullFlight%s" % l
            self.__prob += lpSum(self.__var_tow[l] - [self.__var_turn[l + "P"][ter][k] for ter in bays for k in
                                                      bays_park[ter]]) == 0, "AssignConstSplitFlight%s" % l + "P"
            for s in ["A", "D"]:
                self.__prob += lpSum(self.__var_tow[l] - [self.__var_turn[l + s][ter][k] for ter in bays for k in
                                                      bays_split[ter]]) == 0, "AssignConstSplitFlight%s" % l + s

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
                            self.__prob += lpSum(self.__var_turn[i1][ter][k] + self.__var_turn[i2][ter][k]) <= 1, \
                                           "TimeConstTer%sBay%sFlights%s&%s" % (ter, k, i1, i2)

    def get_tbuf(self, flight):
        arr = self.__map_turns[flight]["ETA"]
        dep = self.__map_turns[flight]["ETD"]
        return arr+self.__tbuf, dep+self.__tbuf

    def tow_const(self):
        for l in self.__lturns["FULL"]:
            if self.__lturns["FULL"][l].get("tow"):
                self.__prob += lpSum(self.__var_tow[l]) == 1, "TowConstFlight%s" % l

    def adj_const(self):
        for idx, i1 in enumerate(list(self.__map_turns.keys())):
            arr1, dep1 = self.get_tbuf(flight=i1)
            for ter, k in self.__keys_bays:
                for i2 in list(self.__map_turns.keys())[idx + 1:]:
                    arr2, dep2 = self.get_tbuf(flight=i2)
                    if not flight_check(flights=[i1, i2]) and ((arr1 <= arr2 <= dep1 or arr1 <= dep2 <= dep1) or
                                                               (arr2 <= arr1 and dep2 >= dep1)):
                        if self.ac_data(flight=i1)["cat"] in self.__bays[ter][k]['cat'] and \
                            self.ac_data(flight=i2)["cat"] in self.__bays[ter].get(k + 2, {}).get('cat', []) and \
                            self.ac_data(flight=i2)["cat"] in self.__adj.get(ter, {}).get(self.__bays[ter][k]["size"], {})\
                                .get(self.__bays[ter].get(k + 2, {}).get("size"), {}).get(self.ac_data(flight=i1)["cat"], []):
                            self.__prob += lpSum(self.__var_turn[i1][ter][k] + self.__var_turn[i2][ter][k + 2]) == 0, \
                                           "AdjConstTer%sBay%sFlights%s&%s" % (ter, k, i1, i2)

    def writeLP(self):
        # The problem data is written to an .lp file
        self.__prob.writeLP("BayAssignmentProblem.lp")

    def solve(self, solver):
        # The problem is solved using PuLP's choice of Solver
        self.__prob.solve(solver)

        # The status of the solution is printed to the screen
        print("Status:", LpStatus[self.__prob.status])

        # Each of the variables is printed with it's resolved optimum value
        for v in self.__prob.variables():
            if v.varValue == 1:
                print(v.name, "=", v.varValue)

        # The optimised objective function value is printed to the screen
        print("Objective Function Value = ", value(self.__prob.objective))

    def return_data(self, *vars):
        attr = return_data(self, 'map')
        attr['schedule'] = attr['schedule'].return_data()['schedule']
        attr['prob'] = return_data(attr['prob'], custom=False)
        attr['solver'] = return_data(attr['solver'])
        if len(vars) == 0:
            return attr
        else:
            return {k : v for k, v in attr.items() if k in vars}


if __name__ == "__main__":

    CPLEX_time = LPSolver(nflights=50, solver=CPLEX_CMD(path=r"C:\Program Files\IBM\ILOG\CPLEX_Studio1210\cplex\bin\x64_win64\cplex.exe"))
    remove_clone_logs()
    try:
        os.rename("BayAssignmentProblem.lp", "outputdata/BayAssignmentProblem.lp")
    except FileExistsError:
        os.replace("BayAssignmentProblem.lp", "outputdata/BayAssignmentProblem.lp")

    data = make_data_serializable(CPLEX_time.return_data(
        #*['ac', 'bays', 'schedule', 'lturns']
    ))

    with open(fr'./outputdata/run_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}.json', 'w+') as file:
        file.write(json.dumps(data))
