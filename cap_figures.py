import pickle
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os

#os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console
path_to_this_script = os.path.abspath(os.getcwd()) #instead of hardcoding C:\Users\Jonathan\Box\python

from my_utils import color_dict, order_cap, add_in_dict, tech_names, scen_names

pickleJar = ""
data = pickle.load(open(path_to_this_script+r"\PickleJar\data_results_6h.pickle", "rb"))

H2 = ['electrolyser', 'H2store', 'FC']
bat = ['bat', 'bat_cap']
VMS = [tech_names[i] for i in H2 + bat] + [i for i in H2 + bat]
"""
noFlex = data["iberia_lowFlex_noFC_2030_6h"]
highFlex = data["iberia_highFlex_noFC_2030_6h"]
base_cases = [noFlex, highFlex]
cap_noFlex = noFlex["new_cap"].level[noFlex["new_cap"].level != 0]  # from v_newcap, pick the level and drop all 0-rows
cap_highFlex = highFlex["new_cap"].level[highFlex["new_cap"].level != 0]
cap_cases = [cap_noFlex, cap_highFlex]
cap_dict = {"noFlex": {}, "highFlex": {}}
for cap, case in zip(cap_cases, ["noFlex", "highFlex"]):
    cap.index.set_names(["Tech", "Region"], inplace=True)
    cap = cap.swaplevel(i=0, j=1)
    cap = cap.sum(level=1)
    for tech in order_cap:
        if tech in cap.index:
            val = cap[tech]
            add_in_dict(cap_dict[case], tech, val, group_vre=True)

techs = []
pretty_techs = []
for tech in order_cap:
    if tech in cap_dict["noFlex"] or tech in cap_dict["highFlex"]:
        techs.append(tech)
        pretty_techs.append(tech_names[tech])

print(techs, "\n", pretty_techs)
colors = [[color_dict[tech] for tech in dic] for dic in cap_dict.values()]
for case, dic in cap_dict.items():
    for tech in dic.copy():
        dic[tech_names[tech]] = dic.pop(tech)

allcolors = [to_rgb(color_dict[tech]) for tech in techs]
s_noFlex = pd.Series(cap_dict["noFlex"])
s_highFlex = pd.Series(cap_dict["highFlex"])
fig, (ax_noFlex, ax_highFlex) = plt.subplots(nrows=2, ncols=2, figsize=(9, 6))
ax_noFlex[0].set_box_aspect(2)
ax_highFlex[0].set_box_aspect(2)
df_noFlex = s_noFlex.to_frame(name="Gen")
df_highFlex = s_highFlex.to_frame(name="Gen")
df_VMS_noFlex = s_noFlex.to_frame(name="VMS").drop(labels=[i for i in s_noFlex.index if i not in VMS], errors="ignore")
df_VMS_highFlex = s_highFlex.to_frame(name="VMS").drop(labels=[i for i in s_highFlex.index if i not in VMS], errors="ignore")
for df in [df_noFlex, df_highFlex]:
    for tech in df.index:
        if tech in VMS:
            df.loc[tech] = 0
df1 = df_noFlex.join(df_VMS_noFlex)
a = df1.T.plot(kind="bar", stacked=True, color=colors[0], ax=ax_noFlex[0], legend=False, width=0.9, rot=0)
a.set_ylabel("Installed capacity [GW(h)]")
df2 = df_highFlex.join(df_VMS_highFlex)
b = df2.T.plot(kind="bar", stacked=True, color=colors[1], ax=ax_highFlex[0], legend=False, width=0.9, rot=0)
b.set_ylabel("Installed capacity [GW(h)]")
plt.show()
fig.savefig("figures/testcap.png", bbox_inches="tight")
"""

position = 0


def add_fig_line(fig, orientation="horizontal"):
    if orientation.lower() in ["horizontal", "h"]:
        x = [0.05, 0.95]
        y = [0.5, 0.5]
    elif orientation.lower() in ["vertical", "v"]:
        x = [0.33, 0.33]
        y = [0.95, 0.05]

    # rearrange the axes for no overlap
    fig.tight_layout()

    # Draw a horizontal lines at those coordinates
    line = plt.Line2D(x, y, transform=fig.transFigure, color="black", linewidth=1, linestyle="--")
    fig.add_artist(line)


def plot_cap_singleyear(ax, data, scen, new=False):
    global position
    if new:
        cap = data[scen]["new_cap"].level
        cap = cap[cap != 0]
    else:
        cap = data[scen]["tot_cap"]

    cap = cap.swaplevel(i=0, j=1).sum(level=1)
    cap_dict = {}
    for tech in order_cap:
        if tech in cap.index:
            val = cap[tech]
            add_in_dict(cap_dict, tech, val, group_vre=True)
    cap = pd.Series(cap_dict, name="Cap")
    colors = [color_dict[tech] for tech in cap.index]
    df_gen = cap.to_frame(name="Gen")
    for tech in [t for t in df_gen.index if t in VMS]:  # doing this instead of .drop maintains tech order and colors
        df_gen.loc[tech] = 0
    df_VMS = cap.to_frame(name="VMS").drop(labels=[i for i in cap.index if i not in VMS], errors="ignore")
    df = df_gen.join(df_VMS)
    plot = df.T.plot(kind="bar", stacked=True, color=colors, legend=False, width=0.9, rot=0, ax=ax)
    return plot, list(df.index)


# noinspection DuplicatedCode
def plot_cap_multipleyears(ax, data, scenario, years=None, new=True, patterns=None,
                           comparison_data=pd.Series({(None, None): None}), ylabel=False, y2label=False):
    """

    Parameters
    ----------
    ax          - Axes to plot on
    data        - dictionary with data for scenarios
    scenario    - scenario to plot for (formatted with 'YEAR' instead of the actual year)
    years       - will be [2030, 2040, 2050] if none are given
    new         - if True, will plot newcap instead of totalcap for base case
    patterns
    comparison_data
    ylabel (bool for "Capacity diff. [GW]", or string for custom ylabel)
    y2label

    Returns
    -------
    plotted technologies and dataframe with all capacities to use for diff-plot

    """
    if years is None:
        years = [2030, 2040, 2050]
    if patterns is None:
        patterns = ['X', '/', '']
    if ylabel == True:
        ylabel = "Capacity diff. [GW]"
    if y2label == True:
        y2label = "Capacity diff. [GW(h)]"
        # doing it this round-about way ensures that changing the patterns/years for one function-call won't linger
        # in the next function call (google "Default arguments value is mutable")

    comparison = len(comparison_data) > 1  # True if comparison_data is longer than 0

    cap = {}
    for y in years:
        scen = scenario.replace("YEAR", str(y))
        if scen not in data:
            years.remove(y)
            print(f"! Did not find {scen.replace('YEAR', str(y))} in the data")
        elif new:
            foo = data[scen]["new_cap"].level
            cap[y] = foo[foo != 0].swaplevel(i=0, j=1).sum(level=1)
        else:
            cap[y] = data[scen]["tot_cap"].swaplevel(i=0, j=1).sum(level=1)  # summed over regions
    cap_summed = {}
    for tech in order_cap:
        for year in years:
            if tech in cap[year].index or (tech,year) in comparison_data.index:
                if tech not in cap[year].index:
                    val = 0
                else:
                    val = cap[year][tech]
                if (tech, year) not in comparison_data.index:
                    val2 = 0  # this will always happen if comparison_data is not given, so the val-val2=val
                else:
                    val2 = comparison_data.loc[(tech,year)].sum()
                to_add = val-val2 if abs(val-val2)>0.01 else 0.
                if abs(to_add) < 0.01 and to_add != 0: print(tech, year, to_add)
                add_in_dict(cap_summed, (tech, year), to_add, group_vre=True)
    cap_series = pd.Series(cap_summed, name="Cap")
    cap_series[cap_series < 0.01] = 0
    df = cap_series.to_frame(name="tot")
    df_gen = cap_series.to_frame(name="Gen")
    techs = df_gen.index.levels[0]
    df_gen.drop(labels=VMS, errors="ignore", level=0, inplace=True)
    gen_colors = [color_dict[tech] for tech in df_gen.index.get_level_values(0)]
    df_gen_pos = df_gen[df_gen > 0]["Gen"]
    df_gen_neg = df_gen[df_gen < 0]["Gen"]
    bottoms_gen_pos = [sum(df_gen_pos.iloc[:i].fillna(0)) for i in range(len(df_gen_pos))]
    bottoms_gen_neg = [sum(df_gen_neg.iloc[:i].fillna(0)) for i in range(len(df_gen_neg))]
    ax.bar(0, df_gen_pos, color=gen_colors, width=0.8, bottom=bottoms_gen_pos, edgecolor="black", linewidth=0.25)
    ax.bar(0, df_gen_neg, color=gen_colors, width=0.8, bottom=bottoms_gen_neg, edgecolor="black", linewidth=0.25)
    #ax.set_ylim(bottom=sum(df_gen_neg.fillna(0))*1.1, top=sum(df_gen_pos.fillna(0))*1.1)
    ax.set_xlim(left=-0.5, right=1.5)
    #ax.set_ylabel("Gen. capacity [GW]")
    fig.add_subplot(ax)

    ax2 = ax.twinx()
    df_VMS = cap_series.to_frame(name="VMS").drop(labels=[i for i in techs if i not in VMS], errors="ignore", level=0)
    df_VMS_pos = df_VMS[df_VMS > 0]["VMS"]
    df_VMS_neg = df_VMS[df_VMS < 0]["VMS"]
    bottoms_VMS_pos = [sum(df_VMS_pos.iloc[:i].fillna(0)) for i in range(len(df_VMS_pos))]
    bottoms_VMS_neg = [sum(df_VMS_neg.iloc[:i].fillna(0)) for i in range(len(df_VMS_neg))]
    VMS_colors = [color_dict[tech] for tech in df_VMS.index.get_level_values(0)]
    ax2.bar(1, df_VMS_pos, color=VMS_colors, width=0.8, bottom=bottoms_VMS_pos, edgecolor="black", linewidth=0.25)
    ax2.bar(1, df_VMS_neg, color=VMS_colors, width=0.8, bottom=bottoms_VMS_neg, edgecolor="black", linewidth=0.25)
    #ax2.set_ylim(bottom=sum(df_VMS_neg.fillna(0)) * 1.05, top=sum(df_VMS_pos.fillna(0)) * 1.05)
    #ax2.set_ylabel("VMS capacity [GW(h)]")
    fig.add_subplot(ax2)
    if comparison:
        ax.plot([-0.5,0.5],[0,0],"k-",linewidth=1)
        ax2.plot([0.5, 1.5], [0, 0], "k-", linewidth=1)
        if sum(df_gen["Gen"].fillna(0)) == 0:
            ax.set_yticks([0])
        elif sum(df_gen["Gen"].fillna(0).abs()) < 0.25:
            ax.set_ylim()
        if sum(df_VMS["VMS"].fillna(0)) == 0:
            ax2.set_yticks([0])

    def set_hatches(df, ax):
        bars = ax.patches
        year_list = [df.index[i][1] for i in range(len(df))]
        year_per_bar = []
        for i, bar in enumerate(bars):
            year = year_list[i%len(year_list)]  # len(bars)=2*len(df) because even the zero/NaN values gets a bar
            j = years.index(year)
            year_per_bar.append((year, j))
            bar.set_hatch(patterns[j])

    set_hatches(df_gen, ax)
    set_hatches(df_VMS, ax2)
    ax.set_xticks([0,1])
    ax.set_xticklabels(["Gen", "VMS"])
    if ylabel != False:
        ax.set_ylabel(ylabel)
    if y2label != False:
        ax2.set_ylabel(y2label)
    return list(df_gen.index.levels[0]), df

# -- All modelled cases
cases = []
h = 6
systemFlex = ["lowFlex", "highFlex"]
modes = ["noFC", "inertia", "OR", "fullFC",]  # , "FCnoPTH", "FCnoH2", "FCnoWind", "FCnoBat", "FCnoSynth"]
nr_comparisons = len(modes)-1

# -- Building figure axes
fig = plt.figure(figsize=(9, 6))  # (width, height) in inches
outer = gridspec.GridSpec(2, 2, wspace=0.45, hspace=0.3, width_ratios=[1, nr_comparisons+1])  # an outer 2x2, inner 1x1 to the left and 1x3 to the right
r_ax = []  # will contain upper and lower right containers, each with one ax for each non-base scenario
axes = [[plt.Subplot(fig, outer[0])], [plt.Subplot(fig, outer[2])]]  # all axes, [[all upper], [all lower]]
for i in range(2):
    r_ax.append(gridspec.GridSpecFromSubplotSpec(1, nr_comparisons, subplot_spec=outer[i*2+1], wspace=0.75))
    for j in range(nr_comparisons):
        axes[i].append(plt.Subplot(fig, r_ax[i][j]))

# -- Filling axes with the data
tech_collections = []
patterns = ['XX', '..', '']
years = [2030, 2040, 2050]
reg = "nordic"
for i_f, flex in enumerate(["lowFlex", "highFlex"]):
    t, df = plot_cap_multipleyears(axes[i_f][0], data, f"{reg}_{flex}_noFC_YEAR_6h", patterns=patterns, years=years,
                                   ylabel="Added capacity [GW]", y2label="Added capacity [GW(h)]")
    axes[i_f][0].set_title(scen_names["noFC"])
    tech_collections.append(t)

    for i_m, mode in enumerate(modes[1:]):
        t, _ = plot_cap_multipleyears(axes[i_f][1+i_m], data, f"{reg}_{flex}_{mode}_YEAR_6h", comparison_data=df,
                                            patterns=patterns, years=years, ylabel=i_m==0, y2label=i_m==2)
        #if i_m == 0:
        #    plot.set_ylabel("Difference from $\it{Base}$ [GW(h)]")
        axes[i_f][i_m+1].set_title(scen_names[mode])
        tech_collections.append(t)

techs = []
for tech in order_cap:
    for collection in tech_collections:
        if tech in collection:
            techs.append(tech)
            break
handles = [Patch(color=color_dict[tech], label=tech_names[tech]) for tech in techs[::-1]]+\
          [Patch(facecolor="#FFF", hatch=patterns[i]*2, label=years[i]) for i in range(3)]
axes[0][0].text(-0.6, 0.5, "Low\nFlex:", transform=axes[0][0].transAxes, ha='right', ma='center', fontsize=14)
axes[1][0].text(-0.6, 0.5, "High\nFlex:", transform=axes[1][0].transAxes, ha='right', ma='center', fontsize=14)
fig.suptitle(reg.capitalize(), fontsize=16)
add_fig_line(fig)
add_fig_line(fig, orientation="vertical")
fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.97, 0.5), )
fig.show()
fig.savefig(f"figures/cap_{reg}_test.png",bbox_inches="tight", dpi=600)
# plot_cap(data,first_case)
# plt.show()
# cap.unstack().plot(kind="bar",stacked=True)
data = False  # purge the 600+ MB data variable from memory
