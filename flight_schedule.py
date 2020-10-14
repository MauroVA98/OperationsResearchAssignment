from collections import defaultdict
from datetime import datetime, timedelta


class scheduler(object):
    def __init__(self, date: datetime = datetime(2010, 4, 1)):
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

        self.__turns = {1: {"ac": "Boeing 777-300", "type": "INT", "ETA": self.get_dt(hour=10, minute=25),
                               "ETD": self.get_dt(hour=15, minute=30)},
                        2: {"ac": "Airbus A330-300", "type": "INT", "ETA": self.get_dt(hour=12, minute=25),
                               "ETD": self.get_dt(hour=14, minute=30)},
                        3: {"ac": "Airbus A380-800", "type": "INT", "ETA": self.get_dt(hour=16, minute=25),
                               "ETD": self.get_dt(hour=17, minute=30)}}

        self.__lturns = self.pross_lturns()

    def get_dt(self, hour: int, minute: int):
        return datetime(self.__date.year, self.__date.month, self.__date.month, hour, minute)

    def pross_lturns(self):
        lturns = defaultdict(dict)
        for flight in self.__turns:
            if self.__turns[flight]["ETD"] - self.__turns[flight]["ETA"] > self.__ttowing:
                lturns[flight]["A"] = self.__turns[flight].copy()
                lturns[flight]["P"] = self.__turns[flight].copy()
                lturns[flight]["D"] = self.__turns[flight].copy()

                lturns[flight]["A"]["ETD"] = self.__turns[flight]["ETA"] + timedelta(minutes=45)
                lturns[flight]["D"]["ETA"] = self.__turns[flight]["ETD"] - timedelta(minutes=45)
                lturns[flight]["P"]["ETA"] = lturns[flight]["A"]["ETD"]
                lturns[flight]["P"]["ETD"] = lturns[flight]["D"]["ETA"]
        return lturns


if __name__ == "__main__":
    s = scheduler()
