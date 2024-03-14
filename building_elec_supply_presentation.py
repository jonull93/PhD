# runs with python 3.9.12, but not 3.6 or 3.11
import pickle
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import print_red, print_green, print_cyan
from order_cap import VRE as VRE_tech, wind as wind_tech
import os 

scen = "nordic_lowFlex_noFC_2040"
picklefile = "data_results_1h_lowFlex.pickle"
os.makedirs("figures/presentation/week_example", exist_ok=True)

data = pickle.load(open(rf"PickleJar/{picklefile}", "rb"))
scendata = data[scen]
skip_week = 3
span = 1*7*24 # weeks*days*hours
#span = 72 # hours
xtick_interval = 24 if span > 48 else 6
xlabel = "Day" if span > 48 else "Hour"
start_index = skip_week*168+24
end_index = start_index+span
xtick_labels = range(skip_week*7+1, skip_week*7+2+span//24) if span > 48 else [f"{i%24:02d}" for i in range(0, span, 6)]
xtick_index = range(0, span+1, 24) if span > 48 else range(0, span+1, 6)
week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Just the load
fig1, ax1 = plt.subplots()
load = scendata["demand"]
gen = scendata["gen"].sum(axis=0, level=0)
twload = load.sum(axis=0).iloc[start_index:end_index]
plt.plot(twload, label="Consumption", color="C1")
ylim = ax1.get_ylim()
ax1.set_ylim([0,123])
ax1.set_xticks(ticks=range(12, 7*24, 24), labels=week_days)
ax1.set_xlabel("Day")
ax1.set_ylabel("Electricity per hour [GWh/h]")
ax1.legend()
#ax1.set_title("Load during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/week_example/presentation_load.png", dpi=500)

skip_week = 3
span = 1*7*24 # weeks*days*hours
#span = 72 # hours
xtick_interval = 24 if span > 48 else 6
xlabel = "Day" if span > 48 else "Hour"
start_index = skip_week*168+24
end_index = start_index+span
xtick_labels = range(skip_week*7+1, skip_week*7+2+span//24) if span > 48 else [f"{i%24:02d}" for i in range(0, span, 6)]
xtick_index = range(0, span+1, 24) if span > 48 else range(0, span+1, 6)

# Overlayed with solar prod
fig2, ax2 = plt.subplots()
twload = load.sum(axis=0).iloc[start_index:end_index]
#gen = scendata["gen"].sum(axis=0, level=0)
full_solar = gen.copy().reindex(index=["PVPA1"]).dropna().sum(axis=0)
solar = full_solar.iloc[start_index:end_index]
solar_curtailment = scendata["curtailment_profiles"].groupby(level=0).sum().loc["PVPA1"].iloc[start_index:end_index]
solar = solar + solar_curtailment
plt.plot(twload, label="Consumption", color="C1", zorder=1)
#set ymin to 0
#ylim = ax2.get_ylim()
ax1.set_ylim([0,123])
#plt.axis('off')
#ax2.spines.clear()
#plt.savefig(r"figures/presentation/presentation_load_solar_noSolar.png",bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
plt.plot(solar, label="Solar PV", color="orange")
#ylim = ax2.get_ylim()
#ax2.set_yticks([])
#ax2.set_xticks([])
ax2.legend(loc="upper right")
ax1.set_xticks(ticks=range(12, span, 24), labels=week_days)
ax1.set_xlabel("Day")
ax1.set_ylabel("Power [GWh/h]")
#ax2.set_title("Load and VRE during a winter week in northern Europe, 2040")
#remove the plot frame lines
plt.savefig(r"figures/presentation/week_example/presentation_load_solar.png",bbox_inches="tight",pad_inches=0, dpi=500)
plt.axis('off')
ax2.spines.clear()
plt.savefig(r"figures/presentation/week_example/presentation_load_solar_noSpine.png",bbox_inches="tight",pad_inches=0, transparent=True,  dpi=500)

skip_week = 3
span = 1*7*24 # weeks*days*hours
#span = 72 # hours
xtick_interval = 24 if span > 48 else 6
xlabel = "Day" if span > 48 else "Hour"
start_index = skip_week*168+24
end_index = start_index+span
xtick_labels = range(skip_week*7+1, skip_week*7+2+span//24) if span > 48 else [f"{i%24:02d}" for i in range(0, span, 6)]
xtick_index = range(0, span+1, 24) if span > 48 else range(0, span+1, 6)

# Overlayed with wind prod
fig2, ax2 = plt.subplots()
#gen = scendata["gen"].sum(axis=0, level=0)
twload = load.sum(axis=0).iloc[start_index:end_index]
full_wind = gen.reindex(wind_tech).dropna().sum()
wind = full_wind.iloc[start_index:end_index]
wind_curtailment = scendata["curtailment_profiles"].groupby(level=0).sum().reindex(wind_tech).dropna().sum(axis=0).iloc[start_index:end_index]
#wind = wind + wind_curtailment
plt.plot(wind+wind_curtailment, label="Wind")
#plt.plot(wind_curtailment, label="Curtailment")
plt.plot(twload, label="Load")
ylim = ax2.get_ylim()
ax2.set_yticks([])
ax2.set_xticks([])
ax2.legend(loc="upper right")
#ax2.set_title("Load and VRE during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/week_example/presentation_load_wind.png", dpi=500)
plt.legend().remove()
plt.axis('off')
ax2.spines.clear()
plt.savefig(r"figures/presentation/week_example/presentation_load_wind_noSpine.png",bbox_inches="tight",pad_inches=0, dpi=500)


# Overlayed with VRE prod
fig2, ax2 = plt.subplots()
#load = scendata["demand"]
#gen = scendata["gen"].sum(axis=0, level=0)
curtailment_profile = scendata["curtailment_profile_total"].sum(axis=0).iloc[start_index:end_index]
curtailment = scendata["curtailment_profiles"].sum(axis=0).iloc[start_index:end_index]
VRE = gen.reindex(index=VRE_tech).dropna().sum(axis=0).iloc[start_index:end_index]
solar = gen.copy().reindex(index=["PVPA1"]).dropna().sum(axis=0).iloc[start_index:end_index]
plt.plot(twload, label="Consumption", color="C1", zorder=1)
plt.plot(VRE+curtailment, label="Wind + Solar", color="C0", zorder=0)
#plt.plot(solar, label="solar")
ylim = ax2.get_ylim()
ax2.set_ylim([min(0,ylim[0]),123])
#ax2.set_xticks(ticks=range(skip_week*168+24, skip_week*168+9*24, 24), labels=range(skip_week*7+1, skip_week*7+9))
#ax2.set_xticks(ticks=range(0, 8*24, 24), labels=range(skip_week*7+1, skip_week*7+9))
#ax2.set_xticks(ticks=xtick_index, labels=xtick_labels)
ax2.legend(loc="upper right")
ax2.set_xticks(ticks=range(12, span, 24), labels=week_days)
ax2.set_xlabel("Day")
ax2.set_ylabel("Electricity per hour [GWh/h]")
#ax2.set_title("Load and VRE during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/week_example/presentation_load_VRE.png", dpi=500)
ax2.fill_between(twload.index, twload, VRE+curtailment, where=VRE+curtailment<twload, color="C0", alpha=0.8, interpolate=True, zorder=0)
plt.savefig(r"figures/presentation/week_example/presentation_load_VRE_fill.png", dpi=500)


# Net load
fig3, ax3 = plt.subplots()
#plt.plot(VRE+curtailment, label="VRE")
ax3.axhline(color="k", linestyle="--",  linewidth="1", alpha=0.5) #linestyle=":", 
ax3.plot(twload, label="Consumption", color="C1", zorder=1)
ax3.plot(twload-VRE-curtailment, label="Net load", color="C0", zorder=0)
ax3.fill_between(twload.index, twload-VRE-curtailment, where=twload-VRE-curtailment>0, color="C0", alpha=0.8, interpolate=True)
ylim = ax3.get_ylim()
ax3.set_ylim([min(0,ylim[0]), 113])
ax3.set_xticks(ticks=range(12, span, 24), labels=week_days)
ax3.set_xlabel("Day")
ax3.set_ylabel("Electricity per hour [GWh/h]")
ax3.legend(loc="upper right")
#ax3.set_title("Net load during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/week_example/presentation_netload.png", dpi=500)


# Overlayed with hydro cap
fig4, ax4 = plt.subplots()
#plt.plot(VRE+curtailment, label="VRE")
plt.plot(twload-VRE-curtailment, label="Net load")
plt.axhline(color="k", linestyle=":", linewidth="1")
ylim = ax4.get_ylim()
ax4.set_xticks(ticks=range(skip_week*168+24, skip_week*168+9*24, 24), labels=range(skip_week*7+1, skip_week*7+9))
ax4.set_xlabel("Day")
ax4.set_ylabel("Power [GWh/h]")
ax4.set_title("Net load during a winter week in northern Europe, 2040")
cap = scendata["tot_cap"].sum(axis=0, level="tech")
hydro_cap = cap["RO"].round(2)
print(hydro_cap)
plt.axhline(hydro_cap, color="deepskyblue", linestyle="--", label="Hydro cap.")
ax4.legend(loc="upper right")
plt.tight_layout()
plt.savefig(r"figures/presentation/presentation_netload_hydrocap.png", dpi=300)


def gen_indices_etc(start_week, span):
    global start_index, end_index, xtick_labels, xtick_index, xlabel
    start_index = start_week*168+24
    end_index = start_index+span
    if span <= 48:
        xtick_labels = [f"{i%24:02d}" for i in range(0, span+1, 6)]
        xtick_index = range(0, span+1, 6)
        xlabel = "Hour"
    elif span <= 2*168:
        xtick_labels = range(start_week*7+1, start_week*7+2+span//24)
        xtick_index = range(0, span+1, 24)
        xlabel = "Day"
    elif span <= 6*168:
        xtick_labels = range(start_week*7+1, start_week*7+2+span//72)
        xtick_index = range(0, span+1, 72)
        xlabel = "Day"
    elif span <= 12*168:
        #weeks
        xtick_labels = range(start_week*7+1, start_week*7+2+span//168)
        xtick_index = range(0, span+1, 168)
        xlabel = "Week"
    else: #spans longer than 4 months
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        first_month_index = (start_week*7+1)//30
        last_month_index = (start_week*7+1+span//24)//30
        xtick_labels = [months[i%12] for i in range(first_month_index, last_month_index+1)][:-1]
        xtick_index = list(range(0, span+1, 24*30))[:-1]
        xlabel = "Month"


    #xtick_labels = range(skip_week*7+1, skip_week*7+2+span//24) if span > 48 else [f"{i%24:02d}" for i in range(0, span+1, 6)]
    #xtick_index = range(0, span+1, 24) if span > 48 else range(0, span+1, 6)

#make load plots
start_weeks = [0]
spans = {"2d": 2*24, "3d": 3*24, "1w": 7*24, "2w": 14*24, "4w": 4*7*24, "8w": 8*7*24, "52w": 52*7*24}
spans = {"52w": 52*7*24}
load = scendata["demand"]
load = load.sum(axis=0)
for start_week in start_weeks:
    for span_str, span in spans.items():
        os.makedirs(rf"figures/presentation/load/noSpine", exist_ok=True)
        gen_indices_etc(start_week, span)
        if end_index > 8760:
            continue
        fig, ax = plt.subplots()
        twload = load.iloc[start_index:end_index]
        plt.plot(twload, label="Load", color="black")
        ax.set_ylim([0,105])
        ax.set_xticks(ticks=xtick_index, labels=xtick_labels)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Power [GWh/h]")
        #ax.legend()
        ax.set_title(f"Load during {span_str} in northern Europe, 2040")
        #plt.tight_layout()
        plt.savefig(rf"figures/presentation/load/presentation_load_w{start_week}_{span_str}.png", bbox_inches="tight",pad_inches=0.1, transparent=True, dpi=500)
        #save without axis
        plt.axis('off')
        ax.spines.clear()
        #plt.legend().remove()
        # remove the title
        ax.set_title("")
        plt.savefig(rf"figures/presentation/load/noSpine/presentation_load_w{start_week}_{span_str}_noSpine.png",bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
        plt.close()

#make PV plots
start_weeks = range(0, 52, 4)
spans = {"2d": 2*24, "3d": 3*24, "1w": 7*24, "2w": 14*24, "4w": 4*7*24, "8w": 8*7*24, "52w": 52*7*24}
gen = scendata["gen"].groupby(level=0).sum()
full_solar = gen.copy().reindex(index=["PVPA1"]).dropna().sum(axis=0)
solar_curtailment = scendata["curtailment_profiles"].groupby(level=0).sum().loc["PVPA1"]
for span_str, span in spans.items():
    for start_week in start_weeks:
        #save figs in separate subfolders for each span length
        os.makedirs(rf"figures/presentation/PV/{span_str}", exist_ok=True)
        gen_indices_etc(start_week, span)
        if end_index > 8760:
            continue
        if span <= 72:
            fig, ax = plt.subplots(figsize=(3,3))
        else:
            fig, ax = plt.subplots()
        solar = full_solar.iloc[start_index:end_index]
        solar = solar + solar_curtailment.iloc[start_index:end_index]
        fill = plt.fill_between(solar.index, solar, color="orange", label="Solar PV")
        ax.set_ylim([-1, 108])
        plt.axis('off')
        ax.spines.clear()
        plt.savefig(rf"figures/presentation/PV/{span_str}/w{start_week}_{span_str}_fill.png", bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
        # remove the fill
        fill.remove()
        #plt.clf()
        plt.plot(solar, label="Solar PV", linewidth=1.5, color="orange")       
        ax.set_ylim([-1,108])
        #ax.set_xticks(ticks=xtick_index, labels=xtick_labels)
        #ax.set_xlabel(xlabel)
        #ax.set_ylabel("Power [GWh/h]")
        #ax.legend()
        #ax.set_title(f"Solar PV during {span_str} in northern Europe, 2040")
        #plt.tight_layout()
        #plt.savefig(rf"figures/presentation/PV/{span_str}/w{start_week}_{span_str}.png", bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
        #save without axis
        #plt.axis('off')
        #ax.spines.clear()
        #plt.legend().remove()
        # remove the title
        #ax.set_title("")
        plt.savefig(rf"figures/presentation/PV/{span_str}/noSpine_w{start_week}_{span_str}.png",bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
        plt.close()


#make wind plots
start_weeks = range(0, 52, 4)
spans = {"2d": 2*24, "3d": 3*24, "1w": 7*24, "2w": 14*24, "4w": 4*7*24, "8w": 8*7*24, "52w": 52*7*24}
full_wind = gen.reindex(wind_tech).dropna().sum()
wind_curtailment = scendata["curtailment_profiles"].groupby(level=0).sum().reindex(wind_tech).dropna().sum(axis=0)
for span_str, span in spans.items():
    for start_week in start_weeks:
        #save figs in separate subfolders for each span length
        os.makedirs(rf"figures/presentation/wind/{span_str}", exist_ok=True)
        gen_indices_etc(start_week, span)
        if end_index > 8760:
            continue
        fig, ax = plt.subplots()
        #wind = wind + wind_curtailment
        wind = full_wind.iloc[start_index:end_index]+wind_curtailment.iloc[start_index:end_index]
        fill = plt.fill_between(wind.index, wind, color="C0", label="Wind")
        ax.set_ylim([-1, 112])
        plt.axis('off')
        ax.spines.clear()
        plt.savefig(rf"figures/presentation/wind/{span_str}/w{start_week}_{span_str}_fill.png", bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
        fill.remove()
        plt.plot(wind, label="Wind", linewidth=1.5, color="C0")
        #ax.set_ylim([0, 112])
        #ax.set_xticks(ticks=xtick_index, labels=xtick_labels)
        #ax.set_xlabel(xlabel)
        #ax.set_ylabel("Power [GWh/h]")
        #ax.legend()
        #ax.set_title(f"Wind during {span_str} in northern Europe, 2040")
        #plt.tight_layout()
        #plt.savefig(rf"figures/presentation/wind/{span_str}/w{start_week}_{span_str}.png", bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
        #save without axis
        #plt.axis('off')
        #ax.spines.clear()
        #plt.legend().remove()
        # remove the title
        #ax.set_title("")
        plt.savefig(rf"figures/presentation/wind/{span_str}/noSpine_w{start_week}_{span_str}.png",bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)
        plt.close()

#find the 4 weeks with the lowest total wind production
wind = full_wind + wind_curtailment
window = 4*7*24
wind_rolling = wind.rolling(window).sum().sort_values()
right_index = wind_rolling.index[0]
right_index = wind.index.get_loc(right_index)
left_index = right_index - window
gen_indices_etc(start_week, span)
wind = wind.iloc[left_index:right_index]
fig, ax = plt.subplots()
plt.fill_between(wind.index, wind, color="C0", label="Wind")
ax.set_ylim([-1, 112])
plt.axis('off')
ax.spines.clear()
plt.savefig(rf"figures/presentation/wind/lowest4weeks.png",bbox_inches="tight",pad_inches=0, transparent=True, dpi=500)

