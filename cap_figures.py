import pickle  # for dumping and loading variable to/from file

import matplotlib.pyplot as plt
from my_utils import order as tech_order, tech_names, color_dict
# try: type(folder)
# except: folder = "figures/"
try:
    _ = data.keys()  # if we ran this file from elsewhere with data already loaded, then this will work
except:
    data = pickle.load(open("PickleJar\\data_PS_base.pickle", "rb"))  # and then this wont run
# tech_order = pickle.load(open("tech_order.pickle","rb")) #creates order list

cases = []
reg_names = {"ES3": "Solar", "HU": "Inland", "IE": "Wind", "SE2": "Hydro+wind"}
for reg in ["ES3", "HU", "SE2", "IE"]:
    scenarios = []
    folder = "figures\\" + reg + "_curves\\"
    name = "cap_" + reg + ""
    for scen in ["reg_pre", "reg_OR", "reg_OR_inertia", "reg_inertia", "reg_inertia_noSyn"]:  # ["reg_pre","reg_leanOR",
        # "reg_OR", "reg_OR+inertia","reg_inertia","reg_inertia_noSyn","reg_inertia_2x"]
        scenarios.append(scen.replace("reg", reg))
    scenario_names = ["Base case", "OR", "OR + Inertia", "Inertia",
                      "Inertia (noSyn)"]  # , "SNSP limit (65%)"]#, "SE_pre", "SE_DR", "SE_VT", "SE_DR+VT"]
    variants = [""]
    file_list = []
    for i in scenarios:
        for j in variants:
            file_list.append(i + j)

    tech = []  # list of all technologies used in all scenarios OBS: not sorted according to tech_order
    patterns = ['/', '\\', '|', '-', '+', 'x', '.', '//', '||', '--', 'o', '.', 'x'] * 2
    # exclude_tech = ["efuel", "H2LRC","GF"] + allwind + CHP_wa + CHP_bio + HP + HOB_bio + TES
    for i in file_list:
        allwind = data[i]['allwind']
        exclude_tech = ["efuel", "H2LRC", "H2tank", "GF", "GF_H2", "GF_el", "GF_H2el", "RO_imp", "RO", "bat_flow", "bat_flow_cap",
                        "bat_LiIon", "bat", "bat_cap"] + allwind
        cap = data[i]['cap']  # dictionary with all capacities in scenario i
        for j in cap:
            if (j not in tech) and (j not in exclude_tech) and (cap[j] > 0):
                tech.append(j)
        if "wind_offshore" not in tech and cap["WOFF"] > 0:
            tech.append('wind_offshore')
            print("found offshore wind in", reg)

    tech.append('wind_onshore')

    w = 0.65
    c = 0
    uniques1 = []
    line1 = []
    # fig1 = plt.figure(1)
    # ax1 = plt.subplot(111)
    fig1, ax1 = plt.subplots(ncols=1, nrows=1, figsize=(6, 7.5))
    plt.title(f"Cost-optimal capacities: $\it{reg_names[reg]}$", fontsize=14)
    # label_axes(fig1,loc=(-0.17,0.5)) #THIS PART ADDS LABELS TO SUBPLOTS: a), b) etc
    for k in file_list:
        # print("working on "+k+" with a total cost of "+str(data[k]['cost_tot'][0]))
        allwind = data[k]['allwind']
        onwind = [i for i in allwind if "OFF" not in i]
        cap = {x: data[k]['cap'][x] for x in data[k]['cap'] if data[k]['cap'][x] > 0 and x not in exclude_tech}  # dictionary[
    # tech] = FLOAT
        cap['wind_onshore'] = sum([data[k]['cap'][y] for y in onwind])
        cap['wind_offshore'] = data[k]['cap']['WOFF']
        if data[k]['cap']['RO'] + data[k]['cap']['RO_imp'] > 0:
            cap["RO"] = data[k]['cap']['RO'] + data[k]['cap']['RO_imp']
        cap["bat"] = data[k]['cap']['bat_cap']  # + data[k]['cap']['bat_flow_cap']
        if "flywheel" in cap: cap["flywheel"] = cap["flywheel"] * 6

        c += 1
        bar1 = []  # originally non-TES and TES, but these two vectors can still be useful for comparing the capacities with or without an implementation
        bar2 = []
        # print('-- ',k)
        cruched = 0
        for i in [j for j in tech_order if j in cap and cap[j] > 0]:
            if cap[i] > 50 or (cap[i] > 25 and ("IE" in k or "HU" in k)):
                bar1.append(cap[i] / 10)
                crunched = i
            else:
                bar1.append(cap[i])
                crunched = 0

            if i not in uniques1:  # this makes sure we add all unique entries to a list ("line") so that we can make a legend with only unique entries
                uniques1.append(i)
                line1.append(ax1.bar(c, bar1[-1], width=w - 0.008, align='center', color=color_dict[i], bottom=sum(bar1) - bar1[
                    -1]))
            else:
                ax1.bar(c, bar1[-1], width=w - 0.008, align='center', color=color_dict[i], bottom=sum(bar1) - bar1[-1])
            if round(bar1[-1], 2) > 0.1 or (reg == "HU" and round(bar1[-1], 2) > 0.05):
                if i in ['wind_onshore', 'wind_offshore', 'PV_cSiOPT', 'WG', 'GWGCCS', 'WG_peak', 'FC', 'flywheel', 'sync_cond']:
                    txt = ax1.text(c, sum(bar1) - bar1[-1] / 2, round(bar1[-1], 2), ha="center", va="center", color="black",
                                   fontsize=10)
                elif i == 'bat':
                    txt = ax1.text(c, sum(bar1) - bar1[-1] / 2, f"{round(bar1[-1], 2)}\n({round(data[k]['cap']['bat'], 1)})",
                                   ha="center", va="center", color="black", fontsize=10)
                elif i == crunched:
                    txt = ax1.text(c, sum(bar1) - bar1[-1] / 2, round(bar1[-1] * 10, 1), ha="center", va="center", color="white",
                                   fontsize=10)
                else:
                    txt = ax1.text(c, sum(bar1) - bar1[-1] / 2, round(bar1[-1], 2), ha="center", va="center", color="white",
                                   fontsize=10)

    plt.sca(ax1)
    plt.xticks([i for i in range(1, len(scenarios) + 1)], scenario_names, fontsize=14, rotation=25, ha="center")
    # for i in range(1,len(scenarios)+1):
    #    ax1.text(i-w/1.9,-1.4,'No TES', ha="center", fontsize=9, rotation=14)
    # ax1.text(i+w/1.9,-1.4,'All TES', ha="center", fontsize=9, rotation=14)
    # ax1.xaxis.set_tick_params(pad=16)
    ax1.set_ylabel('Power capacity [GW]', fontsize=14, )
    # ax1.legend()

    sorted_uniques1 = []
    sorted_line1 = []
    # sorted_uniques = [i for i in tech_order if i in uniques]
    for i in [j for j in tech_order]:
        if i in uniques1:
            sorted_uniques1.append(i)
            sorted_line1.append(line1[uniques1.index(i)])
    tech_names["bat"] = "Battery"
    plt.legend(sorted_line1[::-1], [tech_names[i] for i in sorted_uniques1][::-1], bbox_to_anchor=(1, 1),
                      fontsize=14)  # uniques,loc=9, bbox_to_anchor=(0.5, -0.07), ncol=4

    plt.savefig(folder + name + ".png", bbox_inches="tight", dpi=600)
    plt.savefig(folder + name + ".svg", bbox_inches="tight")
