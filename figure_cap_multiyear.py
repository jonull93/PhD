import pickle
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os
#os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

from my_utils import color_dict, order_cap, add_in_dict, tech_names, scen_names, print_cyan, print_red, print_green, year_names

pickleJar = ""
h = 3
suffix = "noGpeak"
suffix = "_"+suffix if len(suffix)>0 else ""
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{h}h{suffix}.pickle"), "rb"))

H2 = ['H2store']
bat = ['bat']
VMS = [tech_names[i] for i in H2 + bat] + [i for i in H2 + bat]
exclude = ["electrolyser"]

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
                           comparison_data=pd.DataFrame({(None, None): None}, index=[None])):
    if years is None:
        years = [2025, 2030, 2040, 2050]
#    if patterns is None:
#        patterns = ['X', '/','o', '']*2
        # doing it this round-about way ensures that changing the patterns/years for one function-call won't linger
        # in the next function call (google "Default arguments value is mutable")
    comparison = len(comparison_data) > 1  # True if comparison_data is longer than 1

    cap = {}
    for y in years:
        scen = scenario.replace("YEAR", str(y))
        if scen not in data:
            years.remove(y)
            print(f"! Did not find {scen.replace('YEAR', str(y))} in the data")
        elif new:
            foo = data[scen]["new_cap"].level
            cap[y] = foo[foo != 0].swaplevel(i=0, j=1).groupby(level=1).sum()
        else:
            cap[y] = data[scen]["tot_cap"].swaplevel(i=0, j=1).groupby(level=1).sum()

    cap_summed = {}
    for tech in order_cap:
        for year in years:
            compare_this = comparison and tech in comparison_data.index
            if tech in cap[year].index or compare_this:
                val = cap[year].get(tech,default=0)
                if not comparison or not compare_this:
                    val2 = 0  # this will always happen if comparison_data is not given, so the val-val2=val
                else:
                    val2 = comparison_data.loc[tech].loc[(slice(None),year)].sum()
                add_in_dict(cap_summed, (tech, year), val-val2, group_vre=True)
    cap_series = pd.Series(cap_summed, name="Cap")
    df_gen = cap_series.to_frame(name="Gen.")
    techs = df_gen.index.levels[0]
    for tech in techs:
        if tech in VMS:  # doing this instead of .drop maintains tech order and colors
            df_gen.loc[tech] = 0
        elif tech in exclude:
            df_gen.drop(index=tech, level=0, inplace=True)

    df_VMS = cap_series.to_frame(name="Storage").drop(labels=[i for i in techs if i not in VMS], errors="ignore", level=0)
    df = df_gen.join(df_VMS)
    df = df[df.abs() > 0.01].fillna(0)
    df = df.unstack(fill_value=0)
    gen = []
    storage = []
    counter = 0
    for col, colvalues in df.iteritems():
        year = col[1]
        if year == 2020:
            counter = 0
        if col[1]=="Gen.":
            gen.append(counter)
        else:
            storage.append(counter)
        counter += sum(colvalues)

    df.loc["offset"] = 0#gen+storage
    reindexing = [len(df)-1]+[i for i in range(len(df)-1)]
    df = df.iloc[reindexing]
    colors = [color_dict[tech] for tech in df.index.get_level_values(0)]
    hatches = ['//' if tech in VMS else '' for tech in df.index.get_level_values(0)]
    plot = df.T.plot(kind="bar", stacked=True, color=colors, legend=False, width=0.9, rot=0, ax=ax)
    plot.set_xticklabels([year_names[year] for year in years*2], rotation=28, ha="right", rotation_mode='anchor')
    if comparison: plot.axhline(linewidth=1, color="black")
    bars = ax.patches
    #year_list = [df.columns[i][1] for i in range(len(df.columns))]*len(df.index)
    #year_list = [df.index[i][1] for i in range(len(df))]
    #year_per_bar = []
    print(len(bars), len(hatches), df)
    for i, bar in enumerate(bars):
        if bar.get_x()>3:
            bar.set_hatch('/')
    #return plot, list(df.index.levels[0]), df"""
    return plot, list(df.index), df


# -- All modelled cases
separate_figures = ["lowFlex",]
for flex in separate_figures:
    cases = []
    regions = ["nordic", "brit", "iberia"]
    modes = ["noFC", "fullFC"]  # , "FCnoPTH", "FCnoH2", "FCnoWind", "FCnoBat", "FCnoSynth"]
    nr_comparisons = len(modes)-1
    y_subplots = len(regions)

    # -- Building figure axes
    fig = plt.figure(figsize=(7, 8))  # (width, height) in inches
    outer = gridspec.GridSpec(ncols=2, nrows=y_subplots, wspace=0.33, hspace=0.5, width_ratios=[1, nr_comparisons])  # an outer 2x2, inner 1x1 to the left and 1x3 to the right
    r_ax = []  # will contain upper and lower right containers, each with one ax for each non-base scenario
    axes = [[plt.Subplot(fig, outer[0])], [plt.Subplot(fig, outer[2])], [plt.Subplot(fig, outer[4])]]  # all axes, [[all upper], [all lower]]
    for i in range(y_subplots):
        r_ax.append(gridspec.GridSpecFromSubplotSpec(1, nr_comparisons, subplot_spec=outer[i*2+1], wspace=0.5))
        for j in range(nr_comparisons):
            axes[i].append(plt.Subplot(fig, r_ax[i][j]))

    # -- Filling axes with the data
    tech_collections = []
    patterns = ['X', '/', '.', '']
    years = [2020, 2025, 2030, 2040]
    print_cyan('-',flex,'-')
    for i_f, reg in enumerate(regions):
        print_cyan(reg.capitalize())
        plot, t, df = plot_cap_multipleyears(axes[i_f][0], data, f"{reg}_{flex}_noFC_YEAR{suffix}_{h}h", patterns=patterns,
                                             years=years)
        if i_f == 0: plot.set_title(scen_names["noFC"], pad=15)

        if y_subplots % 2 == 1:  # if odd number of y_plots
            if i_f % 2 == 1: plot.set_ylabel("New capacity", fontsize=12)
        else:
            plot.set_ylabel("New capacity", fontsize=12)
        tech_collections.append(t)
        fig.add_subplot(plot)
        for i_m, mode in enumerate(modes[1:]):
            plot, t, df_return = plot_cap_multipleyears(axes[i_f][1+i_m], data, f"{reg}_{flex}_{mode}_YEAR{suffix}_{h}h",
                                                comparison_data=df, patterns=patterns, years=years)
            if y_subplots % 2 == 1:  # if odd number of y_plots
                if i_f % 2 == 1 and i_m == 0: plot.set_ylabel("Difference from $\it{No FC}$", fontsize=12)
            elif i_m == 0:
                plot.set_ylabel("Difference from $\it{No FC}$", fontsize=12)
            if i_f == 0: plot.set_title(scen_names[mode], pad=15)
            tech_collections.append(t)
            fig.add_subplot(plot)
        axes[i_f][0].text(-0.35, 0.5, f"{reg.capitalize()}:", transform=axes[i_f][0].transAxes, ha='right', ma='center', fontsize=14)
        for i_m in range(len(modes)):
            ylim = axes[i_f][i_m].get_ylim()
            axes[i_f][i_m].set_ylim([i*1.15 for i in ylim])
            axes[i_f][i_m].axvline(x=3.5, color='k', linewidth=1)
            text = axes[i_f][i_m].text(0.25, 1, "Power [GW]", transform=axes[i_f][i_m].transAxes, va="center", ha="center")
            text.set_bbox(dict(facecolor='white', alpha=1, edgecolor='black'))
            text = axes[i_f][i_m].text(0.75, 1, "Storage [GWh]", transform=axes[i_f][i_m].transAxes, va="center", ha="center")
            text.set_bbox(dict(facecolor='white', alpha=1, edgecolor='black'))
    axes[-1][0].text(0.5, 0.015, f"Year", transform=fig.transFigure, ha='center', ma='center', fontsize=12)

# -- Finishing off fig
    techs = []
    for tech in order_cap:
        for collection in tech_collections:
            if tech in collection:
                techs.append(tech)
                break
    print(techs)
    handles = [Patch(facecolor=color_dict[tech], label=tech_names[tech], hatch=f"{'///' if tech in VMS else ''}") for tech in techs[::-1]]#+\
              #[Patch(facecolor="#FFF", hatch=patterns[i]*2, label=years[i]) for i in range(4)]
    #axes[0][0].text(-0.35, 0.5, "Low\nFlex:", transform=axes[0][0].transAxes, ha='right', ma='center', fontsize=14)
    #axes[1][0].text(-0.35, 0.5, "High\nFlex:", transform=axes[1][0].transAxes, ha='right', ma='center', fontsize=14)
    #axes[2][0].text(-0.35, 0.5, "High\nFlex:", transform=axes[1][0].transAxes, ha='right', ma='center', fontsize=14)
    fig.suptitle(f"Investments, {flex.capitalize()}",fontsize=16)
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.91, 0.5), )
    fig.show()
    fig.savefig(f"figures/cap_{flex}_{h}h.png",bbox_inches="tight", dpi=600)
# plot_cap(data,first_case)
# plt.show()
# cap.unstack().plot(kind="bar",stacked=True)
del data  # purge the 600+ MB data variable from memory
