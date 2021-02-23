import numpy as np
import matplotlib.pyplot as plt
import json, os
import datetime as dt


def extract_occupations_per_bay(data: dict):
    form = data['date_format']
    gates = []
    for k1, v1 in data['bays'].items():
        for k2, v2 in v1.items():
            gates.append(f'{k1}_{k2}')

    distr = {g : [] for g in gates}

    for i in range(1, data['schedule']['nflights']+1):
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
    nxbins = round((t1-t0)/x_step)
    ylabels = list(bins.keys())
    xlabels = [t0 + x_step*i for i in range(nxbins+1)]
    xrange  = [t0 + dt.timedelta(minutes=1)*i for i in range((t1-t0).seconds // 60)]

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

    plane_cat_map = {ac['AC'] : ac['cat'] for ac in data['ac'].values()}
    cat_count = {ac['cat'] : 0 for ac in data['ac'].values()}

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
                ax.barh(ylabels, w_vector, left=l_vector, color=colour, linewidth=1, edgecolor = (0,0,0), label=c)
            else:
                ax.barh(ylabels, w_vector, left=l_vector, color=colour, linewidth=1, edgecolor = (0,0,0))

            r, g, b, _ = colour
            center = l_vector + w_vector/2
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
