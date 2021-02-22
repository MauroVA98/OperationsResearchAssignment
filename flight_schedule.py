import inspect
import json
from math import ceil
from random import choices, gauss
from collections import defaultdict
from datetime import datetime, timedelta
from matplotlib.dates import DateFormatter, HourLocator
from matplotlib.ticker import MaxNLocator

import matplotlib.pyplot as plt


def return_data(obj, *excludes, custom=True):
    attributes = inspect.getmembers(obj, lambda a: not (inspect.isroutine(a)))
    attr = {'_'.join(a[0].split('_')[3:]) * bool(custom) + a[0] * bool(custom - 1): a[1] for a in attributes if
            not (a[0].startswith('__') and a[0].endswith('__') or
                 sum([(e in a[0]) for e in excludes]))}
    return attr


def cat_list(lst: list):
    w = [chr(i) for i in range(ord(lst[0]), ord(lst[1]) + 1)]
    return w[::-1]


class Scheduler(object):
    def __init__(self, nflights: int, date: datetime = datetime(2010, 6, 15), plotting: bool = False,
                 ac_file: str = r"./programdata/ac.json", terminal_file: str = r"./programdata/terminals.json"):
        self.__date = date
        self.__nflights = nflights

        self.__tstart = self.get_dt(hours=6, minutes=0)
        self.__tend = self.get_dt(hours=23, minutes=59)

        self.__tmin = timedelta(minutes=60)
        self.__ttow = timedelta(hours=3)

        with open(terminal_file, 'r') as file:
            self.__terminals = json.load(file)

        # Aircraft passenger capacity and ac group from:
        # https://www.dvbbank.com/~/media/Files/D/dvbbank-corp/aviation/dvb-overview-of-commercial-aircraft-2018-2019.pdf
        with open(ac_file, 'r') as file:
            self.__ac = json.load(file)
            self.__ac = {int(key): value for key, value in self.__ac.items()}

        self.__prob = {"INT": {1: {"mean_arr": self.get_dt(hours=8, minutes=0), "std_arr": 1 * 60,
                                   "mean_len": timedelta(minutes=1.5 * 60), "std_len": 1 * 60},
                               2: {"mean_arr": self.get_dt(hours=14, minutes=0), "std_arr": 3 * 60,
                                   "mean_len": timedelta(minutes=1.5 * 60), "std_len": 1.5 * 60},
                               3: {"mean_arr": self.get_dt(hours=21, minutes=00), "std_arr": 1 * 60,
                                   "mean_len": timedelta(minutes=1.5 * 60), "std_len": 1 * 60}},
                       "DOM": {4: {"mean_arr": self.get_dt(hours=14, minutes=0), "std_arr": 6 * 60,
                                   "mean_len": timedelta(minutes=60), "std_len": 30}}}

        self.__weights = {
            "INT": {"AC": {10: 0.35, 11: 0.3, 12: 0.2, 13: 0.13, 14: 0.02}, "tzone": {1: 0.25, 2: 0.1, 3: 0.05},
                    "tow": 0, "pref": 0.3},
            "DOM": {"AC": {1: 0.05, 2: 0.05, 3: 0.05, 4: 0.05, 5: 0.1, 6: 0.2, 7: 0.1, 8: 0.1,
                           9: 0.2, 10: 0.1}, "tzone": {4: 0.6}, "tow": 0, "pref": 0.2}}

        self.__bays = defaultdict(dict)
        self.__schedule = {}

        # create bay data dictionary
        self.get_bays()

        self.make_schedule()

        self.__turns, self.__lturns = self.pross_schedule()

        self.plotter() if plotting else None

    def get_dt(self, hours: int, minutes: int):
        return datetime(self.__date.year, self.__date.month, self.__date.day, hours, minutes)

    def ac_data(self, AC: str):
        return self.__ac[
            list(self.__ac.keys())[[self.__ac[x]["AC"] for x in self.__ac].index(AC)]]

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
            tzone = choices(list(val for t in self.__weights for val in self.__weights[t]["tzone"]),
                            list(weight for t in self.__weights for weight in self.__weights[t]["tzone"]))[0]
            for t in self.__weights:
                if tzone in self.__prob[t]:
                    ter = t
                else:
                    continue
            plane = choices(list(self.__weights[ter]["AC"].keys()), self.__weights[ter]["AC"].values())[0]
            arr, dep = self.make_t(mean_arr=self.__prob[ter][tzone]["mean_arr"],
                                   std_arr=self.__prob[ter][tzone]["std_arr"],
                                   mean_len=self.__prob[ter][tzone]["mean_len"],
                                   std_len=self.__prob[ter][tzone]["std_len"])
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


if __name__ == "__main__":
    ac_schedule = Scheduler(nflights=80, plotting=True)
