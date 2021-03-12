import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import json, os
import datetime as dt


def extract_occupations_per_bay(data: dict):
    form = data['date_format']
    gates = []
    for k1, v1 in data['bays'].items():
        for k2, v2 in v1.items():
            gates.append(f'{k1}_{k2}')

    distr = {g: [] for g in gates}

    for i in range(1, data['schedule']['nflights'] + 1):
        istr = str(i)
        if istr in data['variables']['y'].keys():
            continue
        else:
            if istr in data['variables']['w'].keys():
                for letter in ['A', 'P', 'D']:
                    iistr = istr + letter
                    gate = f"{data['variables']['x'][iistr]['type']}_{data['variables']['x'][iistr]['id']}"
                    t0, t1 = data['lturns']['SPLIT'][iistr]['ETA'], data['lturns']['SPLIT'][iistr]['ETD']
                    t0, t1 = dt.datetime.strptime(t0, form), dt.datetime.strptime(t1, form)
                    distr[gate].append([i, t0, t1])

            else:
                gate = f"{data['variables']['x'][istr]['type']}_{data['variables']['x'][istr]['id']}"
                try:
                    t0, t1 = data['turns'][istr]['ETA'], data['turns'][istr]['ETD']
                except KeyError:
                    t0, t1 = data['lturns']['FULL'][istr]['ETA'], data['lturns']['FULL'][istr]['ETD']

                t0, t1 = dt.datetime.strptime(t0, form), dt.datetime.strptime(t1, form)
                distr[gate].append([i, t0, t1])

    for k, lst in distr.items():
        distr[k] = sorted(lst, key=lambda item: item[1])

    return distr


def make_hbar(data: dict):
    bins = extract_occupations_per_bay(data)

    t0 = dt.datetime.strptime(data['schedule']['tstart'], data['date_format'])
    t1 = dt.datetime.strptime(data['schedule']['tend'], data['date_format'])

    x_step = dt.timedelta(hours=1, minutes=0)
    nxbins = round((t1 - t0) / x_step)
    ylabels = list(bins.keys())
    xlabels = [t0 + x_step * i for i in range(nxbins + 1)]
    xrange = [t0 + dt.timedelta(minutes=1) * i for i in range((t1 - t0).seconds // 60)]

    xdata = [
        [(d[2] - d[1]).seconds for d in bin] for gate, bin in bins.items()
    ]
    xlefts = [
        [(d[1] - t0).seconds for d in bin] for gate, bin in bins.items()
    ]
    mx = max(max([len(i) for i in xdata]), max([len(i) for i in xlefts]))
    for l1, l2 in zip(xdata, xlefts):
        while len(l1) != mx:
            l1.append(0)
        while len(l2) != mx:
            l2.append(0)

    fig, ax = plt.subplots()

    cat = set()
    for k1, v1 in data['bays'].items():
        for k2, v2 in v1.items():
            cat = cat.union(set(v2['cat']))
    cat = list(sorted(list(cat), reverse=True))
    colour_gradient = plt.cm.get_cmap('brg', len(cat))

    def get_cat_id(c):
        for i, item in enumerate(cat):
            if c == item:
                return i
        return None

    plane_cat_map = {ac['AC']: ac['cat'] for ac in data['ac'].values()}
    cat_count = {ac['cat']: 0 for ac in data['ac'].values()}

    for i, (gate, bin) in enumerate(bins.items()):
        for j, item in enumerate(bin):
            w_vector = np.zeros((len(bins)), dtype=int)
            w_vector[i] = (item[2] - item[1]).seconds
            l_vector = np.zeros((len(bins)), dtype=int)
            l_vector[i] = (item[1] - t0).seconds
            plane = data['schedule']['schedule'][str(item[0])]['AC']
            c = plane_cat_map[plane]
            colour = colour_gradient(get_cat_id(c))
            if cat_count[c] == 0:
                ax.barh(ylabels, w_vector, left=l_vector, color=colour, linewidth=1, edgecolor=(0, 0, 0), label=c)
            else:
                ax.barh(ylabels, w_vector, left=l_vector, color=colour, linewidth=1, edgecolor=(0, 0, 0))

            r, g, b, _ = colour
            center = l_vector + w_vector / 2
            text_color = 'white' if r * g * b < 0.5 else 'darkgrey'
            ax.text(sum(center), ylabels.index(gate), str(item[0]), ha='center', va='center',
                    color=text_color)
            cat_count[c] += 1

    ax.set_xticks([(xlabel - t0).seconds for xlabel in xlabels])
    ax.set_xticklabels([label.strftime('%H:%M') for label in xlabels], rotation=60)
    ax.xaxis.grid(True)
    handles, labels = ax.get_legend_handles_labels()
    labels, handles = zip(*sorted(zip(labels, handles), key=lambda t: t[0]))
    ax.legend(handles, labels, ncol=len(cat), bbox_to_anchor=(0, 1),
              loc='lower left')
    plt.show()


def make_ac_bar(data: dict):
    ac_counts = defaultdict(dict)
    ac_cat = sorted(list(set(list(data["ac"][ac]["cat"] for ac in data["ac"]))))
    features = {"A": {"hatch": None, "color": "white"}, "B": {"hatch": "/", "color": "white"},
                "C": {"hatch": "\\", "color": "white"}, "D": {"hatch": "|", "color": "white"},
                "E": {"hatch": "+", "color": "white"}, "F": {"hatch": "x", "color": "white"},
                "G": {"hatch": "o", "color": "white"}, "H": {"hatch": ".", "color": "white"}}

    def get_cat(ac: str):
        for idx in data["ac"]:
            if data["ac"][idx]["AC"] == ac:
                return data["ac"][idx]["cat"]
            else:
                pass

    for cat in ac_cat:
        for turn in data["schedule"]["schedule"].values():
            if cat == get_cat(turn["AC"]) and turn["AC"] not in ac_counts:
                ac_counts[turn["AC"]]["cnt"] = 1
                ac_counts[turn["AC"]]["cat"] = cat
            elif cat == get_cat(turn["AC"]):
                ac_counts[turn["AC"]]["cnt"] += 1

    fig, ax = plt.subplots()
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.gcf().subplots_adjust(bottom=0.15)
    fig.autofmt_xdate(rotation=45)
    temp = 0
    for ac in ac_counts:
        if temp != ac_counts[ac]["cat"]:
            ax.bar(ac, ac_counts[ac]["cnt"], hatch=features[ac_counts[ac]["cat"]]["hatch"],
                   color=features[ac_counts[ac]["cat"]]["color"], label=ac_counts[ac]["cat"], edgecolor="black")
        else:
            ax.bar(ac, ac_counts[ac]["cnt"], hatch=features[ac_counts[ac]["cat"]]["hatch"],
                   color=features[ac_counts[ac]["cat"]]["color"], edgecolor="black")
        temp = ac_counts[ac]["cat"]
    ax.set_ylabel('Amount of Aircraft', fontsize=12)
    ax.set_xlabel("Aircraft", fontsize=12)
    ax.grid(True)
    plt.legend(title="    Aircraft \n Categories", loc='upper right')
    fig.show()


def make_len_bar(data: dict):
    ac_counts = {}
    lengths = []
    t_width = 30
    form = data['date_format']

    for turn in data["schedule"]["schedule"].values():
        lengths.append((dt.datetime.strptime(turn["ETD"], form) - dt.datetime.strptime(turn["ETA"], form)).seconds)
    i = 0
    while max(lengths) > i * t_width * 60:
        i += 1
        s = sum(l >= ((i - 1) * t_width * 60) for l in lengths) - sum(l >= (i * t_width * 60) for l in lengths)
        if s > 0:
            ac_counts[i * t_width] = s

    fig, ax = plt.subplots()
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.bar(range(len(ac_counts)), list(ac_counts.values()))
    labels = ["%d:%02d - %d:%02d" % (int((key - t_width) / 60), int(key - t_width - int((key - t_width) / 60) * 60),
                                     int(key / 60), int(key - int(key / 60) * 60)) for key in ac_counts]
    plt.xticks(range(len(ac_counts)), labels)
    ax.set_ylabel('Amount of Turns', fontsize=12)
    ax.set_xlabel('Duration [hours]', fontsize=12)
    ax.grid(True)
    fig.show()


def plotter(data: dict, hbar: bool = False, ac_bar: bool = False, len_bar: bool = False):
    if hbar: make_hbar(data)
    if ac_bar: make_ac_bar(data)
    if len_bar: make_len_bar(data)
