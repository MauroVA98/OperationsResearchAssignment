from collections import defaultdict
from datetime import datetime, timedelta


class Scheduler(object):
    def __init__(self, date: datetime = datetime(1, 1, 1)):
        self.__date = date
        self.__ttowing = timedelta(hours=4)

        # Aircraft passenger capacity and ac group from:
        # https://www.dvbbank.com/~/media/Files/D/dvbbank-corp/aviation/dvb-overview-of-commercial-aircraft-2018-2019.pdf
        self.__ac = {"Boeing 717-200": {"cap": 106, "cat": "A"},
                     "Bombardier CRJ700": {"cap": 66, "cat": "A"},
                     "Embraer ERJ-140": {"cap": 44, "cat": "A"},
                     "McDonnel Douglas MD-87": {"cap": 114, "cat": "A"},
                     "DHC-8-401/402": {"cap": 74, "cat": "A"},
                     "Airbus A320-200": {"cap": 150, "cat": "D"},
                     "Airbus A321-200": {"cap": 185, "cat": "D"},
                     "Boeing 737-700": {"cap": 141, "cat": "D"},
                     "Boeing 737-900": {"cap": 189, "cat": "D"},
                     "Airbus A330-300": {"cap": 277, "cat": "F"},
                     "Boeing 787-900": {"cap": 290, "cat": "F"},
                     "Boeing 777-300": {"cap": 425, "cat": "G"},
                     "Boeing 747-800I": {"cap": 410, "cat": "H"},
                     "Airbus A380-800": {"cap": 544, "cat": "H"}}

        self.__schedule = {1: {"ac": "Boeing 777-300", "type": "INT", "ETA": self.get_dt(hour=10, minute=25),
                               "ETD": self.get_dt(hour=15, minute=30), "PREF": [["B4", 5], ["B3", 10]]},
                           2: {"ac": "Airbus A330-300", "type": "INT", "ETA": self.get_dt(hour=12, minute=25),
                               "ETD": self.get_dt(hour=14, minute=30)},
                           3: {"ac": "Airbus A380-800", "type": "INT", "ETA": self.get_dt(hour=16, minute=25),
                               "ETD": self.get_dt(hour=17, minute=30)}}

        self.__turns, self.__lturns = self.pross_schedule()

    def get_dt(self, hour: int, minute: int):
        return datetime(self.__date.year, self.__date.month, self.__date.month, hour, minute)

    def pross_schedule(self):
        turns = self.__schedule.copy()
        lturns = defaultdict(dict)
        for flight in self.__schedule:
            if self.__schedule[flight]["ETD"] - self.__schedule[flight]["ETA"] > self.__ttowing:
                lturns["FULL"][flight] = self.__schedule[flight].copy()
                lturns["SPLIT"][str(flight)+"A"] = self.__schedule[flight].copy()
                lturns["SPLIT"][str(flight)+"P"] = self.__schedule[flight].copy()
                lturns["SPLIT"][str(flight)+"D"] = self.__schedule[flight].copy()

                lturns["SPLIT"][str(flight)+"A"]["ETD"] = self.__schedule[flight]["ETA"] + timedelta(minutes=45)
                lturns["SPLIT"][str(flight)+"D"]["ETA"] = self.__schedule[flight]["ETD"] - timedelta(minutes=45)
                lturns["SPLIT"][str(flight)+"P"]["ETA"] = lturns["SPLIT"][str(flight)+"A"]["ETD"]
                lturns["SPLIT"][str(flight)+"P"]["ETD"] = lturns["SPLIT"][str(flight)+"D"]["ETA"]

                if isinstance(self.__schedule[flight]["PREF"][0], list):
                    lturns["FULL"][flight]["PREF"] = self.__schedule[flight]["PREF"][0]
                    lturns["SPLIT"][str(flight)+"A"]["PREF"] = self.__schedule[flight]["PREF"][0]
                    lturns["SPLIT"][str(flight)+"D"]["PREF"] = self.__schedule[flight]["PREF"][1]
                del lturns["SPLIT"][str(flight)+"P"]["PREF"]
                del turns[flight]
        return turns, lturns

    def return_turns(self):
        return self.__turns

    def return_lturns(self):
        return self.__lturns

    def return_ac(self):
        return self.__ac


if __name__ == "__main__":
    schedule = Scheduler()
