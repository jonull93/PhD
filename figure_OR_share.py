import pickle
from os import path
from my_utils import label_axes, print_cyan
import matplotlib.pyplot as plt
import matplotlib.text as mpltext
import pandas as pd


def int_if_int(i):
    if isinstance(i, int): return i
    if isinstance(i, mpltext.Text): i = i.get_text()
    if isinstance(i, str):
        try:
            i = float(i)
        except ValueError:
            return i
    if i.is_integer():
        return int(i)
    else:
        return round(i, 3)


def make_plot(df, title, secondary_y_values, xlabels=None, legend=False, left_ylabel=False, right_ylabel=False,
              bars=True,
              _ax=None):
    # ---- plotting
    # takes DataFrame and plots stacked area and optionally a line on secondary y axis
    if xlabels is None:
        xlabels = ["2020", "Near-term", "Mid-term", "Long-term"]
    if _ax is None:
        if bars is True:
            ax = df.div(df.sum(axis=1), axis=0).plot.bar(stacked=True, rot=19)
        else:
            ax = df.div(df.sum(axis=1), axis=0).plot(kind="area", linewidth=0)
    else:
        if bars is True:
            ax = df.div(df.sum(axis=1), axis=0).plot.bar(stacked=True, rot=19, ax=_ax)
        else:
            ax = df.div(df.sum(axis=1), axis=0).plot(kind="area", linewidth=0, ax=_ax)

    current_handles, current_labels = ax.get_legend_handles_labels()
    ax.set_title(title)
    if left_ylabel:
        ax.set_ylabel(left_ylabel)
    # _locs, _labels = plt.yticks()
    _ticks = [0, 0.2, 0.4, 0.6, 0.8, 1]
    ax.set_yticks(_ticks)
    ax.set_yticklabels([int_if_int(i) for i in _ticks])
    ax2 = ax.twinx()
    if right_ylabel:
        ax2.set_ylabel(right_ylabel)
    line = ax2.plot(secondary_y_values, "kD", markerfacecolor='none')
    handles = current_handles + line
    labels = [h.get_label() for h in handles]
    labels[-1] = "Cost"
    ax.set_xticklabels(xlabels)
    if legend:
        ax.legend(handles, labels)
    else:
        ax.get_legend().remove()
    # ax2.set_ylim(ymin=0)
    # ax2.ticklabel_format(style="sci", scilimits=(0, 0))
    return ax, ax2, (handles, labels)


def percent_stacked_area(data, regions, flex, timestep, indicator_string: str, set: dict, years=None, FC=True,
                         secondary_y="FR_cost", scen_suffix="", bars=True,
                         figtitle="Interval share, and \u0394system-cost", filepath="test.png",
                         baseFC = "fullFC", compareFC = "fullFC_noDoubleUse"):
    print_cyan(f"Starting percent_stacked_area() for {indicator_string}")
    if years is None:
        years = [2020, 2025, 2030, 2040]
    if "high" not in flex and "BEV" in set: set.pop("BEV")
    fig, axes = plt.subplots(nrows=1, ncols=len(regions), figsize=(8, 4), )
    label_axes(fig, loc=(-0.1, 1.03))
    for j, region in enumerate(regions):
        print_cyan(f"- {region} -")
        scenarios = [f"{region}_{flex}_{compareFC if FC else 'noFC'}{scen_suffix}_{y}_{timestep}h" for y in years]
        print("Cost_tot:", [round(data[scen]["cost_tot"], 2) for scen in scenarios])
        if indicator_string == "FR_cost":
            indicator_data = {pretty: [0. for i in range(len(scenarios))] for pretty in set}
            for pretty, name in set.items():
                for i, scen in enumerate(scenarios):
                    try:
                        indicator_data[pretty][i] = data[scen]["FR_cost"].sum(axis=1).groupby(level=1).sum()[str(name)]
                    except KeyError:
                        indicator_data[pretty][i] = 0
                    except ValueError:
                        print("!! weird formatting in FR_cost !!")
                        try:
                            indicator_data[pretty][i] = data[scen]["FR_cost"].groupby(level=2).sum()[str(name)]
                        except Exception as e:
                            print(type(e), e)
        else:
            indicator_data = {pretty: [data[scen][f"{indicator_string}{name}"] for scen in scenarios] for pretty, name
                              in set.items()}
        if secondary_y == "FR_cost":
            secondary_y_values = [data[scen][secondary_y].sum().sum().round() / 1000 for scen in scenarios]
        elif secondary_y == "FR_cost_per_gen":
            secondary_y_values = [data[scen]["FR_cost"].sum().sum().round() * 1000 *100
                                  / data[scen]["gen_per_eltech"].sum().round() for scen in scenarios]
        elif secondary_y == "FR_syscost":
            secondary_y_values = [(data[scen]["cost_tot"]-data[scen.replace(compareFC, baseFC)]["cost_tot"]).round(4) for scen in scenarios]
        elif secondary_y == "FR_syscost_per_gen":
            secondary_y_values = [((data[scen]["cost_tot"]-data[scen.replace(compareFC, baseFC)]["cost_tot"])*1e6*100/data[scen]["gen_per_eltech"].sum()).round(4) for scen in scenarios]

        df = pd.DataFrame(data=
                          {pretty_name: indicator_data[pretty_name] for pretty_name in indicator_data}
                          , index=years).round(decimals=4)
        #print(indicator_string)
        #print(df)
        print(f"{secondary_y}: {secondary_y_values}")
        if indicator_string == "FR_cost":
            title = f"{region.capitalize()}"
        else:
            title = f"{region.capitalize()}"
        if j == 0: left_ylabel="Reserve share"
        else: left_ylabel=False
        if j == len(regions)-1: right_ylabel="System cost increase [€ cent/MWh]"
        else: right_ylabel=False
        _, _, (handles, labels) = make_plot(df, title, secondary_y_values, left_ylabel=left_ylabel,
                                            right_ylabel=right_ylabel, _ax=axes[j])
    plt.sca(axes[1])
    fig.legend(handles,labels,bbox_to_anchor=(0.5, 0.93), ncol=4, loc="lower center")
    fig.suptitle(f"{figtitle}: {flex}", y=1.13)
    plt.subplots_adjust(wspace=0.49)
    plt.savefig(filepath, dpi=600, bbox_inches="tight")


flex = "lowFlex"
timestep = 3
pickle_suffix = "noDoubleUse"
if len(pickle_suffix) > 0: pickle_suffix = "_" + pickle_suffix
data = pickle.load(open(path.relpath(rf"PickleJar\data_results_{timestep}h{pickle_suffix}.pickle"), "rb"))
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
secondary_y = "FR_syscost_per_gen"  # _per_gen
reserve_technologies = {"Thermals": "thermal", "VRE": "VRE", "ESS": "ESS", "BEV": "BEV", "PtH": "PtH", "Hydro": "hydro"}
FR_intervals = {"FFR": 1, "5-30s": 2, "30s-5min": 3, "5-15min": 4, "15-30min": 5, "30-60min": 6}

# ax = percent_stacked_area("nordic", mode, timestep, "FR_value_share_", reserve_technologies, secondary_y="FR_cost_per_gen")
# plt.show()
regions = ["nordic", "brit", "iberia"]
print("________________" * 3)
print(f" .. Making figure for {regions} .. ")
percent_stacked_area(data, regions, flex, timestep, "FR_value_share_", reserve_technologies, secondary_y=secondary_y,
                     scen_suffix=scen_suffix, figtitle="Cost-weighted technology share, and \u0394system-cost",
                     filepath=rf"figures\reserve_valueshare_{flex}{scen_suffix}{pickle_suffix}_{timestep}h.png")

percent_stacked_area(data, regions, flex, timestep, "FR_share_", reserve_technologies, secondary_y=secondary_y,
                     scen_suffix=scen_suffix, figtitle="Technology reserve share, and \u0394system-cost",
                     filepath=rf"figures\reserve_share_{flex}{scen_suffix}{pickle_suffix}_{timestep}h.png")
#plt.savefig(rf"figures\reserve_share_{mode}{pickle_suff}_{timestep}h.png", dpi=600, bbox_inches="tight")
percent_stacked_area(data, regions, flex, timestep, "FR_cost", FR_intervals, secondary_y=secondary_y,
                     scen_suffix=scen_suffix, figtitle="Interval reserve share, and \u0394system-cost",
                     filepath=rf"figures\interval_costs_{flex}{scen_suffix}{pickle_suffix}_{timestep}h.png")
#plt.savefig(rf"figures\interval_costs_{mode}{pickle_suff}_{timestep}h.png", dpi=600, bbox_inches="tight")
