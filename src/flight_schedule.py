import inspect
import json

from math import ceil
from random import choices, gauss
from collections import defaultdict
from datetime import datetime, timedelta
from matplotlib.dates import DateFormatter, HourLocator
from matplotlib.ticker import MaxNLocator

import matplotlib.pyplot as plt


def convert_dict_keys(data: dict, keytype: type = int):
    result = {}
    for key, value in data.items():
        if(isinstance(value, dict)):
            try:
                result[keytype(key)] = convert_dict_keys(value, keytype)
            except ValueError:
                result[key] = convert_dict_keys(value, keytype)
        else:
            try:
                result[keytype(key)] = value
            except ValueError:
                result[key] = value

    return result


def return_data(obj, *excludes, custom=True):
    attributes = inspect.getmembers(obj, lambda a: not (inspect.isroutine(a)))
    attr = {'_'.join(a[0].split('_')[3:]) * bool(custom) + a[0] * bool(custom - 1): a[1] for a in attributes if
            not (a[0].startswith('__') and a[0].endswith('__') or
                 sum([(e in a[0]) for e in excludes]))}
    return attr


def cat_list(lst: list):
    w = [chr(i) for i in range(ord(lst[0]), ord(lst[1]) + 1)]
    return w[::-1]

def minmaxd(data:dict):
    d = [0, 10]
    for k in data:
        for i in data[k]:
            if d[0] < data[k][i]["dist"] and k != "BUS":
                d[0] = data[k][i]["dist"]
            elif d[1] > data[k][i]["dist"] and k != "BUS":
                d[1] = data[k][i]["dist"]
    return d


class Scheduler(object):
    def __init__(self, nflights: int, date: datetime = datetime(2010, 6, 15), plotting: bool = False,
                 ac_file: str = r"./programdata/ac.json", terminal_file: str = r"./programdata/terminals.json",
                 feature_file : str = r"./programdata/features.json", schedule_file: str = r"./programdata/scheduling.json"):
        self.__date = date
        self.__nflights = nflights

        with open(schedule_file, 'r') as file:
            time_data = json.load(file)
            self.__tstart = self.get_dt(hours=time_data['tstart'][0], minutes=time_data['tstart'][1])
            self.__tend = self.get_dt(hours=time_data['tend'][0], minutes=time_data['tend'][1])
            self.__tmin = timedelta(hours=time_data['tmin'][0], minutes=time_data['tmin'][1])
            self.__ttow = timedelta(hours=time_data['ttow'][0], minutes=time_data['ttow'][1])

        with open(terminal_file, 'r') as file:
            self.__terminals = json.load(file)

        # Aircraft passenger capacity and ac group from:
        # https://www.dvbbank.com/~/media/Files/D/dvbbank-corp/aviation/dvb-overview-of-commercial-aircraft-2018-2019.pdf
        with open(ac_file, 'r') as file:
            self.__ac = json.load(file)
            self.__ac = {int(key): value for key, value in self.__ac.items()}

        with open(feature_file, 'r') as file:
            temp = json.load(file)
            self.__prob = convert_dict_keys(temp["prob"], int)
            self.__weights = convert_dict_keys(temp["weights"], int)

            for key in self.__prob.keys():
                for var, val in self.__prob[key].items():
                    if var == 'mean_arr':
                        self.__prob[key][var] = self.get_dt(hours=val[0], minutes=val[1])
                    elif var == 'mean_len':
                        self.__prob[key][var] = timedelta(minutes=val)

        self.__bays = defaultdict(dict)
        self.__schedule = {}

        # create bay data dictionary
        self.get_bays()

        self.make_schedule()

        self.__turns, self.__lturns = self.pross_schedule()

        self.__costs = self.make_costs()

        self.plotter() if plotting else None

    def get_dt(self, hours: int, minutes: int):
        return datetime(self.__date.year, self.__date.month, self.__date.day, hours, minutes)

    def ac_data(self, AC: str):
        return self.__ac[
            list(self.__ac.keys())[[self.__ac[x]["AC"] for x in self.__ac].index(AC)]]

    def make_costs(self):
        ac_cat = list(set(list(self.__ac[ac]["cat"] for ac in self.__ac)))
        tow_costs = dict.fromkeys(ac_cat, 0)
        nobay_costs = tow_costs.copy()
        data = defaultdict(dict)

        max_d, min_d = minmaxd(data=self.__bays)
        bus_dist = self.__terminals["BUS"]["B"]["dist"]
        ter_penalty = 1.5*bus_dist/min_d

        for ac in self.__ac:
            if "cap" not in data[self.__ac[ac]["cat"]]:
                data[self.__ac[ac]["cat"]]["cap"] = [self.__ac[ac]["cap"]]
            else:
                data[self.__ac[ac]["cat"]]["cap"].append(self.__ac[ac]["cap"])

        for ter in self.__weights:
            for ac in self.__weights[ter]["AC"]:
                idx_min, idx_max = min(list(self.__bays[ter].keys())), max(list(self.__bays[ter].keys()))
                if "dist" not in data[self.__ac[ac]["cat"]]:
                    data[self.__ac[ac]["cat"]]["dist"] = [self.__bays[ter][idx_min]["dist"],
                                                               self.__bays[ter][idx_max]["dist"]]
                else:
                    data[self.__ac[ac]["cat"]]["dist"].extend([self.__bays[ter][idx_min]["dist"],
                                                                   self.__bays[ter][idx_max]["dist"]])

        for cat in tow_costs:
            tow_min = max(data[cat]["cap"])*(max(data[cat]["dist"])-min(data[cat]["dist"]))
            tow_max = min(data[cat]["cap"])*(bus_dist-max(data[cat]["dist"]))
            assert(tow_max > tow_min)
            tow_costs[cat] = (tow_max+tow_min)/2

            nobay_costs[cat] = 1.1*max(data[cat]["cap"])*13*ter_penalty*max_d
            assert(tow_costs[cat] < nobay_costs[cat])
        return tow_costs, nobay_costs, ter_penalty

    def get_bays(self):
        for ter in list(self.__terminals.keys()):
            bays = sum([(list(self.__terminals[ter][tbay].values())[0]) for tbay in self.__terminals[ter]])
            for k in range(1, bays + 1):
                if k <= self.__terminals[ter].get("L", {}).get("num", 0):
                    self.__bays[ter][k] = {"cat": cat_list(self.__terminals[ter]["L"]["cat"]), "size": "L",
                                           "dist": ceil(k / 2) * self.__terminals[ter]["L"]["dist"] -
                                                   self.__terminals[ter]["L"]["dist"] / 2}
                elif k <= self.__terminals[ter].get("L", {}).get("num", 0) + \
                        self.__terminals[ter].get("S", {}).get("num", 0):
                    self.__bays[ter][k] = {"cat": cat_list(self.__terminals[ter]["S"]["cat"]), "size": "S",
                                           "dist": self.__terminals[ter]["S"]["dist"] / 2 +
                                                   ceil(self.__terminals[ter]["L"]["num"] / 2) *
                                                   self.__terminals[ter]["L"]["dist"] +
                                                   self.__terminals[ter]["S"]["dist"] *
                                                   (ceil((k - self.__terminals[ter]["L"]["num"]) / 2) - 1)}
                else:
                    self.__bays[ter][k] = {"cat": cat_list(self.__terminals[ter]["B"]["cat"]), "size": "B",
                                           "dist": self.__terminals[ter]["B"]["dist"]}

    def make_schedule(self):
        for n in range(1, self.__nflights + 1):
            vals = list(self.__prob.keys())
            weights = list(self.__prob[k]['weight'] for k in self.__prob.keys())
            tzone = choices(vals, weights)[0]
            ter = self.__prob[tzone]['type']
            plane = choices(list(self.__weights[ter]["AC"].keys()), self.__weights[ter]["AC"].values())[0]
            arr, dep = self.make_t(mean_arr=self.__prob[tzone]["mean_arr"],
                                   std_arr=self.__prob[tzone]["std_arr"],
                                   mean_len=self.__prob[tzone]["mean_len"],
                                   std_len=self.__prob[tzone]["std_len"])
            self.__schedule[str(n)] = {"AC": self.__ac[plane]["AC"], "ETA": arr, "ETD": dep, "ter": ter}
            if dep - arr > self.__ttow and self.__ac[plane]["cat"] not in ["H", "A"]:
                tow = choices([True, False], [self.__weights[ter]["tow"], 1 - self.__weights[ter]["tow"]])[0]
                if tow:
                    self.__schedule[str(n)].update({"tow": tow})
            if self.__ac[plane]["cat"] != "A":
                pref = choices([True, False], [self.__weights[ter]["pref"], 1 - self.__weights[ter]["pref"]])[0]
                if pref:
                    av_bays = []
                    for k in self.__bays[ter]:
                        if self.__ac[plane]["cat"] in self.__bays[ter][k]["cat"] and \
                                (self.__ac[plane]["cat"] == "A" or self.__bays[ter][k]["size"] != "B"):
                            av_bays.append(k)
                    self.__schedule[str(n)].update({"pref": {"ter": ter, "bay": choices(av_bays)[0],
                                                             "val": choices([v for v in range(5, 11)])[0]}})

    def make_t(self, mean_arr: datetime, std_arr: float, mean_len: timedelta, std_len: float):
        arr = round(gauss(0, std_arr * 60) / 60) * 60
        leng = round(gauss(0, std_len * 60) / 60) * 60
        while -(mean_arr - self.__tstart).seconds >= arr or arr >= (
                self.__tend - mean_arr).seconds - self.__tmin.seconds \
                or leng <= self.__tmin.seconds or leng >= (self.__tend - mean_arr).seconds - mean_len.seconds - arr:
            arr = round(gauss(0, std_arr * 60) / 60) * 60
            leng = round(gauss(0, std_len * 60) / 60) * 60
        arr_dt = mean_arr + timedelta(seconds=arr)
        dep_dt = mean_arr + mean_len + timedelta(seconds=arr + leng)
        return arr_dt, dep_dt

    def plotter(self):
        times = [self.__tstart + timedelta(seconds=5 * 60 * x) for x in
                 range(int((self.__tend - self.__tstart).seconds / (5 * 60)) + 2)]
        data = []

        for ter in list(self.__weights.keys()):
            lst = []
            for time in times:
                i = 0
                for flight in self.__schedule:
                    if self.__schedule[flight]["ETA"] <= time < self.__schedule[flight]["ETD"] and \
                            self.__schedule[flight]["ter"] == ter:
                        i += 1
                lst.append(i)
            data.append(lst)

        data.append([sum(x) for x in zip(*data)])

        fig, ax = plt.subplots()
        plt.plot(times, data[0])
        plt.plot(times, data[1])
        plt.plot(times, data[2])

        lgd = list(self.__weights.keys())
        lgd.append("TOTAL")
        plt.legend(lgd)

        plt.ylim(0, max(data[2]) + 1)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.xlim(min(times), max(times))
        ax.xaxis.set_major_locator(HourLocator(interval=2))
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        fig.autofmt_xdate()

        plt.xlabel("Time")
        plt.ylabel("Aircraft")
        plt.grid()

        plt.show()

    def pross_schedule(self):
        turns = self.__schedule.copy()
        lturns = defaultdict(dict)
        for flight in self.__schedule:
            if self.__schedule[flight]["ETD"] - self.__schedule[flight]["ETA"] > self.__ttow and \
                    self.__ac[list(self.__ac.keys())[[self.__ac[x]["AC"] for x in
                                                      self.__ac].index(self.__schedule[flight]["AC"])]]["cat"] not in [
                "H", "A"]:
                lturns["FULL"][flight] = self.__schedule[flight].copy()
                lturns["SPLIT"][flight + "A"] = self.__schedule[flight].copy()
                lturns["SPLIT"][flight + "D"] = self.__schedule[flight].copy()
                lturns["SPLIT"][flight + "P"] = self.__schedule[flight].copy()

                lturns["SPLIT"][flight + "A"]["ETD"] = self.__schedule[flight]["ETA"] + timedelta(minutes=30)
                lturns["SPLIT"][flight + "D"]["ETA"] = self.__schedule[flight]["ETD"] - timedelta(minutes=30)
                lturns["SPLIT"][flight + "P"]["ETA"] = lturns["SPLIT"][flight + "A"]["ETD"]
                lturns["SPLIT"][flight + "P"]["ETD"] = lturns["SPLIT"][flight + "D"]["ETA"]
                if "pref" in lturns["SPLIT"][flight + "P"]:
                    del lturns["SPLIT"][flight + "P"]['pref']
                del turns[flight]
        return turns, lturns

    def return_data(self):
        return return_data(self)

    def return_turns(self):
        return self.__turns

    def return_lturns(self):
        return self.__lturns

    def return_ac(self):
        return self.__ac

    def return_bays(self):
        return self.__bays

    def return_termianls(self):
        return self.__terminals

    def return_cost_data(self):
        return self.__costs


if __name__ == "__main__":
    ac_schedule = Scheduler(nflights=100, plotting=True)
