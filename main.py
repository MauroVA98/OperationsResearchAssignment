from datetime import datetime
from typing import List
import time

from pulp import CPLEX_CMD

from src.bay_assignment import LPSolver, make_data_serializable
from src.flight_schedule import Scheduler
from src.graphics import *


def remove_clone_logs():
    for file in os.listdir(os.getcwd()):
        if 'clone' in file:
            os.remove(os.path.join(os.getcwd(), file))


def main(n_flights : int = 50,
         logging_data : List[str] = [],
         cplex_path: str = r"C:\Program Files\IBM\ILOG\CPLEX_Studio1210\cplex\bin\x64_win64\cplex.exe",
         schedule: Scheduler = None):

    start = time.time()
    CPLEX_time = LPSolver(
        nflights=n_flights,
        schedule=schedule,
        solver=CPLEX_CMD(
            path=cplex_path,
            msg=False,
        )
    )
    diff = (time.time() - start)
    remove_clone_logs()
    try:
        os.rename("BayAssignmentProblem.lp", "outputdata/BayAssignmentProblem.lp")
    except FileExistsError:
        os.replace("BayAssignmentProblem.lp", "outputdata/BayAssignmentProblem.lp")

    raw_data = CPLEX_time.return_data(
        *logging_data
    )
    data = make_data_serializable(raw_data)

    with open(fr'./outputdata/run_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}.json', 'w+') as file:
        file.write(json.dumps(data))

    return data, raw_data, diff


if __name__ == "__main__":
    N = 50
    ac_schedule = Scheduler(nflights=N, plotting=False)
    log, raw_log, solver_time = main(
        schedule=ac_schedule,
        n_flights=N,
        # logging_data=['ac', 'bays', 'schedule', 'turns', 'lturns', 'date_format', 'variables']
    )
    bins = extract_occupations_per_bay(log)
    plotter(data=log, hbar=True, ac_bar=True, len_bar=True)
