import pickle
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os
os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

from my_utils import color_dict, order_cap, add_in_dict, tech_names, scen_names

pickleJar = ""
data = pickle.load(open(r"C:\Users\Jonathan\Box\python\PickleJar\data_results_6h_newDH.pickle", "rb"))

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


def plot_cap_multipleyears(ax, data, scenario, years=None, new=True, patterns=None,
                           comparison_data=pd.Series({(None, None): None}), ):
    if years is None:
        years = [2030, 2040, 2050]
    if patterns is None:
        patterns = ['X', '/', '']
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
            cap[y] = data[scen]["tot_cap"].swaplevel(i=0, j=1).sum(level=1)

    cap_summedVRE = {}
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
                add_in_dict(cap_summedVRE, (tech, year), val-val2, group_vre=True)
    cap_series = pd.Series(cap_summedVRE, name="Cap")
    df_gen = cap_series.to_frame(name="Gen")
    techs = df_gen.index.levels[0]
    for tech in [t for t in techs if t in VMS]:  # doing this instead of .drop maintains tech order and colors
        df_gen.loc[tech] = 0
    df_VMS = cap_series.to_frame(name="VMS").drop(labels=[i for i in techs if i not in VMS], errors="ignore", level=0)
    df = df_gen.join(df_VMS)
    colors = [color_dict[tech] for tech in df.index.get_level_values(0)]
    plot = df.T.plot(kind="bar", stacked=True, color=colors, legend=False, width=0.9, rot=0, ax=ax, )
    if comparison: plot.axhline(linewidth=1, color="black")
    bars = ax.patches
    year_list = [df.index[i][1] for i in range(len(df))]
    year_per_bar = []
    for i, bar in enumerate(bars):
        year = year_list[int(i/2)]  # len(bars)=2*len(df) because even the zero/NaN values gets a bar
        j = years.index(year)
        year_per_bar.append((year,j))
        bar.set_hatch(patterns[j])
    return plot, list(df.index.levels[0]), df

# -- All modelled cases
cases = []
h = 6
systemFlex = ["lowFlex", "highFlex"]
modes = ["noFC", "inertia", "OR", "fullFC",]  # , "FCnoPTH", "FCnoH2", "FCnoWind", "FCnoBat", "FCnoSynth"]
nr_comparisons = len(modes)-1

# -- Building figure axes
fig = plt.figure(figsize=(9, 6))  # (width, height) in inches
outer = gridspec.GridSpec(2, 2, wspace=0.3, hspace=0.3, width_ratios=[1, nr_comparisons+1])  # an outer 2x2, inner 1x1 to the left and 1x3 to the right
r_ax = []  # will contain upper and lower right containers, each with one ax for each non-base scenario
axes = [[plt.Subplot(fig, outer[0])], [plt.Subplot(fig, outer[2])]]  # all axes, [[all upper], [all lower]]
for i in range(2):
    r_ax.append(gridspec.GridSpecFromSubplotSpec(1, nr_comparisons, subplot_spec=outer[i*2+1], wspace=0.5))
    for j in range(nr_comparisons):
        axes[i].append(plt.Subplot(fig, r_ax[i][j]))

# -- Filling axes with the data
tech_collections = []
patterns = ['X', '/', '']
years = [2030, 2040, 2050]
for i_f, flex in enumerate(["lowFlex", "highFlex"]):
    plot, t, df = plot_cap_multipleyears(axes[i_f][0], data, f"iberia_{flex}_noFC_YEAR_6h", patterns=patterns,
                                         years=years)
    plot.set_title(scen_names["noFC"])
    plot.set_ylabel("New capacity [GW(h)]")
    tech_collections.append(t)
    fig.add_subplot(plot)
    for i_m, mode in enumerate(modes[1:]):
        plot, t, _ = plot_cap_multipleyears(axes[i_f][1+i_m], data, f"iberia_{flex}_{mode}_YEAR_6h", comparison_data=df,
                                            patterns=patterns, years=years)
        if i_m == 0:
            plot.set_ylabel("Difference from $\it{Base}$ [GW(h)]")
        plot.set_title(scen_names[mode])
        tech_collections.append(t)
        fig.add_subplot(plot)
techs = []
for tech in order_cap:
    for collection in tech_collections:
        if tech in collection:
            techs.append(tech)
            break
handles = [Patch(color=color_dict[tech], label=tech_names[tech]) for tech in techs]+\
          [Patch(facecolor="#DCDCDC", hatch=patterns[i]*2, label=years[i]) for i in range(3)]
fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.91, 0.5), )
fig.show()
# plot_cap(data,first_case)
# plt.show()
# cap.unstack().plot(kind="bar",stacked=True)
data = False  # purge the 600+ MB data variable from memory
