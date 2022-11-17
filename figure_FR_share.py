import pickle
from os import path
from my_utils import label_axes, print_cyan, regions_corrected, print_red
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
        xlabels = ["Ref.\n2020", "Near-\nterm", "Mid-\nterm", "Long-\nterm"]
    if _ax is None:
        if bars is True:
            ax = df.div(df.sum(axis=1), axis=0).plot.bar(stacked=True, rot=15, width=0.7)
        else:
            ax = df.div(df.sum(axis=1), axis=0).plot(kind="area", linewidth=0)
    else:
        if bars is True:
            ax = df.div(df.sum(axis=1), axis=0).plot.bar(stacked=True, rot=15, ax=_ax, width=0.7)
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


def percent_stacked_area(axes, fig, data, regions, flex, timestep, indicator_string: str, set: dict, years=None,
                         FC=True, secondary_y="FR_cost", scen_suffix="", bars=True,
                         figtitle="Interval share, and \u0394system-cost", filepath="test.png",
                         baseFC="noFC", compareFC="fullFC", right_ylabel="System cost increase [€ cent/MWh]"):
    print_cyan(f"Starting percent_stacked_area() for {indicator_string}")
    if years is None:
        years = [2020, 2025, 2030, 2040]
    set.pop("BEV", None)
    if "high" not in flex:
        set.pop("H2", None)
    # label_axes(fig, loc=(-0.1, 1.03))
    for j, region in enumerate(regions):
        print_cyan(f"- {region} -")
        scenarios = [f"{region}_{flex}_{compareFC if FC else 'noFC'}{scen_suffix}_{y}{timestep}" for y in years]
        print("Cost_tot:", [round(data[scen]["cost_tot"], 2) for scen in scenarios])
        if indicator_string == "FR_cost":
            indicator_data = {pretty: [0. for i in range(len(scenarios))] for pretty in set}
            for pretty, name in set.items():
                for i, scen in enumerate(scenarios):
                    try:
                        indicator_data[pretty][i] = data[scen]["FR_cost"].sum(axis=1).groupby(level=1).sum()[str(name)]
                    except KeyError:
                        print_red("! Failed to get", name, "in", region, scen)
                        print_red(data[scen]["FR_cost"])
                        print_red(data[scen]["FR_cost"].sum(axis=1).groupby(level=1).sum())
                        raise
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
            secondary_y_values = [data[scen]["FR_cost"].sum().sum().round() * 100
                              / data[scen]["gen_per_eltech"].sum().round() for scen in scenarios]
        elif secondary_y == "FR_cost_average":
            secondary_y_values = [data[scen]["FR_cost"].mean().mean() for scen in scenarios]
        elif secondary_y == "FR_market_size":
            secondary_y_values = [(data[scen]["FR_cost"]*data[scen]["FR_demand"]["total"]).sum().sum().round()/1000 for scen in scenarios]
        elif secondary_y == "FR_syscost":
            secondary_y_values = [(data[scen]["cost_tot"] - data[scen.replace(compareFC, baseFC)]["cost_tot"]).round(4)
                              for scen in scenarios]
        elif secondary_y == "FR_syscost_per_gen":
            secondary_y_values = [((data[scen]["cost_tot"] - data[scen.replace(compareFC, baseFC)][
                "cost_tot"]) * 1e6 * 100 / data[scen]["gen_per_eltech"].sum()).round(4) for scen in scenarios]

        df = pd.DataFrame(data=
                          {pretty_name: indicator_data[pretty_name] for pretty_name in indicator_data}
                          , index=years).round(decimals=4)
        # print(indicator_string)
        # print(df)
        print(f"{secondary_y}: {secondary_y_values}")
        if indicator_string == "FR_cost":
            title = f"{regions_corrected[region]}"
        else:
            title = f"{regions_corrected[region]}"
        if j == 0:
            left_ylabel = "Reserve share"
        else:
            left_ylabel = False
        if j == len(regions) - 1:
            right_ylabel_ = right_ylabel
        else:
            right_ylabel_ = False
        _, _, (handles, labels) = make_plot(df, title, secondary_y_values, left_ylabel=left_ylabel,
                                            right_ylabel=right_ylabel_, _ax=axes[j])
    plt.sca(axes[1])
    #    fig.legend(handles,labels,bbox_to_anchor=(0.5, 0.92), ncol=4, loc="lower center")
    fig.suptitle(f"{figtitle}: {flex}", y=1.05)
    plt.subplots_adjust(wspace=0.49, hspace=0.4)
    return handles, labels


timestep = 1
fig_file_suffix = "old"
if len(fig_file_suffix) > 0: fig_file_suffix = "_" + fig_file_suffix
pickle_suffix = "old"
if len(pickle_suffix) > 0: pickle_suffix = "_" + pickle_suffix
data = pickle.load(open(path.relpath(rf"PickleJar\data_results_{timestep}h{pickle_suffix}.pickle"), "rb"))

scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
secondary_y = "FR_market_size"  # _per_gen
right_ylabel = "Reserve market size [M€/yr]"
reserve_technologies = {"Thermals": "thermal", "VRE": "VRE", "Storage": "ESS", "Power-to-heat": "PtH", "Hydro": "hydro",
                        "BEV": "BEV"}
FR_intervals = {"FFR": 1, "5-30s": 2, "30s-5min": 3, "5-15min": 4, "15-30min": 5, "30-60min": 6}

if timestep > 1:
    timestep = f"_{timestep}h"
else:
    timestep = ""

# ax = percent_stacked_area("nordic", mode, timestep, "FR_value_share_", reserve_technologies, secondary_y="FR_cost_per_gen")
# plt.show()
regions = ["nordic", "brit", "iberia"]
flexes = ["lowFlex", "highFlex"]
print("________________" * 3)
print(f" .. Making figure for {regions} .. ")
# -- info about the three figures:
indicator_strings = ["FR_cost", "FR_value_share_", "FR_share_", ]
figtitles = {"FR_cost": "Interval reserve share and \u0394system-cost",
             "FR_value_share_": "Cost-weighted technology share and \u0394system-cost",
             "FR_share_": "Technology reserve share and \u0394system-cost", }
filenames = {"FR_cost": "interval_costs",
             "FR_value_share_": "reserve_valueshare",
             "FR_share_": "reserve_share"}
label_sets = {"FR_cost": FR_intervals,
              "FR_value_share_": reserve_technologies,
              "FR_share_": reserve_technologies}
# --
for i_t, type in enumerate(indicator_strings):
    fig, axes = plt.subplots(nrows=len(flexes), ncols=len(regions), figsize=(len(regions) + 4.7, 3 * len(flexes)), )
    for i_f, flex in enumerate(flexes):
        (handles, labels) = percent_stacked_area(axes[i_f], fig, data, regions, flex, timestep, indicator_strings[i_t],
                                                 label_sets[type], secondary_y=secondary_y, right_ylabel=right_ylabel,
                                                 scen_suffix=scen_suffix, figtitle=figtitles[type])
        axes[i_f][0].annotate(flex[0].upper()+flex[1:], xy=(-0.45, 0.5), xycoords='axes fraction', va="center", ha="right", fontsize=12)
    fig.legend(handles, labels, bbox_to_anchor=(0.5, 0.92), ncol=4, loc="lower center")
    plt.savefig(rf"figures\{filenames[type]}{scen_suffix}{pickle_suffix}{timestep}{fig_file_suffix}.png", dpi=600,
                bbox_inches="tight")
    plt.savefig(rf"figures\{filenames[type]}{scen_suffix}{pickle_suffix}{timestep}{fig_file_suffix}.eps",
                bbox_inches="tight", format="eps")
