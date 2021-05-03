import pickle
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import os
os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

from my_utils import color_dict, order_cap, add_in_dict, tech_names

pickleJar = ""
data = pickle.load(open(r"C:\Users\Jonathan\Box\python\PickleJar\data_results_6h_newDH.pickle", "rb"))

H2 = ['electrolyser', 'H2store', 'FC']
bat = ['bat', 'bat_cap']
VMS = [tech_names[i] for i in H2 + bat]

cases = []
h = 6
systemFlex = ["lowFlex", "highFlex"]
modes = ["noFC", "fullFC", "inertia", "OR"]  # , "FCnoPTH", "FCnoH2", "FCnoWind", "FCnoBat", "FCnoSynth"]
for reg in ["iberia", "brit", "nordic"]:
    for flex in systemFlex:
        for mode in modes:
            for year in [2030, 2040, 2050]:
                cases.append(f"{reg}_{flex}_{mode}_{year}{'_' + str(h) + 'h' if h > 1 else ''}")

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
handles = [Patch(color=allcolors[::-1][i], label=tech_names[tech]) for i, tech in enumerate(techs[::-1])]
fig.legend(handles=handles, loc="center left", bbox_to_anchor=(-0.037, 0.5), )
plt.show()
fig.savefig("figures/testcap.png", bbox_inches="tight")


def plot_cap(data, scen, new=True,):
    if new:
        cap = data[scen]["new_cap"].level
        cap = cap[cap != 0]
    else:
        cap = data[scen]["tot_cap"]

    cap.index.set_names(["Tech", "Region"], inplace=True)
    cap = cap.swaplevel(i=0, j=1)
    cap = cap.sum(level=1)
    for i, region in enumerate(cap.index.levels[0]):
        WONS = [tech for tech in cap[region].index if "WON" in tech]
        cap[region]["WON"] = cap[region][WONS].sum()
        print(cap[region], WONS)
        foo = cap.drop(labels=WONS)
        c = [color_dict[tech] for tech in foo.index]
        foo.plot(kind="bar", color=c, position=i, width=0.05)
    # cap.unstack().plot(kind="bar",stacked=True)

# plot_cap(data,first_case)
# plt.show()
# cap.unstack().plot(kind="bar",stacked=True)
