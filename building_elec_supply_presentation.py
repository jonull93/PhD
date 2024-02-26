import pickle
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import print_red, print_green, print_cyan
from order_cap import VRE as VRE_tech, wind as wind_tech
import os 

scen = "nordic_lowFlex_noFC_2040"
picklefile = "data_results_1h_lowFlex.pickle"
os.makedirs("figures/presentation", exist_ok=True)

data = pickle.load(open(rf"PickleJar/{picklefile}", "rb"))
scendata = data[scen]
skip_week = 28
span = 1*7*24 # weeks*days*hours
#span = 72 # hours
xtick_interval = 24 if span > 48 else 6
xlabel = "Day" if span > 48 else "Hour"
start_index = skip_week*168+24
end_index = start_index+span
xtick_labels = range(skip_week*7+1, skip_week*7+2+span//24) if span > 48 else [f"{i%24:02d}" for i in range(0, span, 6)]
xtick_index = range(0, span+1, 24) if span > 48 else range(0, span+1, 6)

# Just the load
fig1, ax1 = plt.subplots()
load = scendata["demand"]
twload = load.sum(axis=0).iloc[start_index:end_index]
plt.plot(twload, label="Load", color="C1")
ylim = ax1.get_ylim()
ax1.set_ylim([0,123])
ax1.set_xticks(ticks=range(0, 8*24, 24), labels=range(skip_week*7+1, skip_week*7+9))
ax1.set_xlabel("Day")
ax1.set_ylabel("Power [GWh/h]")
ax1.legend()
ax1.set_title("Load during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/presentation_load.png", dpi=300)

skip_week = 28
#span = 1*7*24 # weeks*days*hours
span = 72 # hours
xtick_interval = 24 if span > 48 else 6
xlabel = "Day" if span > 48 else "Hour"
start_index = skip_week*168+24
end_index = start_index+span
xtick_labels = range(skip_week*7+1, skip_week*7+2+span//24) if span > 48 else [f"{i%24:02d}" for i in range(0, span, 6)]
xtick_index = range(0, span+1, 24) if span > 48 else range(0, span+1, 6)

# Overlayed with solar prod
fig2, ax2 = plt.subplots(figsize=(3,3))
twload = load.sum(axis=0).iloc[start_index:end_index]
gen = scendata["gen"].sum(axis=0, level=0)
full_solar = gen.copy().reindex(index=["PVPA1"]).dropna().sum(axis=0)
solar = full_solar.iloc[start_index:end_index]
solar_curtailment = scendata["curtailment_profiles"].sum(level=0).loc["PVPA1"].iloc[start_index:end_index]
solar = solar + solar_curtailment
plt.plot(solar, label="Solar PV")
plt.plot(twload, label="Load")
ylim = ax2.get_ylim()
ax2.set_yticks([])
ax2.set_xticks([])
ax2.legend(loc="upper right")
#ax2.set_title("Load and VRE during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/presentation_load_solar.png", dpi=500)

skip_week = 25
span = 2*7*24 # weeks*days*hours
#span = 72 # hours
xtick_interval = 24 if span > 48 else 6
xlabel = "Day" if span > 48 else "Hour"
start_index = skip_week*168+24
end_index = start_index+span
xtick_labels = range(skip_week*7+1, skip_week*7+2+span//24) if span > 48 else [f"{i%24:02d}" for i in range(0, span, 6)]
xtick_index = range(0, span+1, 24) if span > 48 else range(0, span+1, 6)

# Overlayed with wind prod
fig2, ax2 = plt.subplots(figsize=(4,3))
gen = scendata["gen"].sum(axis=0, level=0)
twload = load.sum(axis=0).iloc[start_index:end_index]
full_wind = gen.reindex(wind_tech).dropna().sum()
wind = full_wind.iloc[start_index:end_index]
wind_curtailment = scendata["curtailment_profiles"].sum(level=0).reindex(wind_tech).dropna().sum(axis=0).iloc[start_index:end_index]
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
plt.savefig(r"figures/presentation/presentation_load_wind.png", dpi=500)

# Overlayed with VRE prod
fig2, ax2 = plt.subplots()
load = scendata["demand"]
gen = scendata["gen"].sum(axis=0, level=0)
curtailment_profile = scendata["curtailment_profile_total"].sum(axis=0).iloc[start_index:end_index]
curtailment = scendata["curtailment_profiles"].sum(axis=0).iloc[start_index:end_index]
VRE = gen.reindex(index=VRE_tech).dropna().sum(axis=0).iloc[start_index:end_index]
solar = gen.copy().reindex(index=["PVPA1"]).dropna().sum(axis=0).iloc[start_index:end_index]
plt.plot(VRE+curtailment, label="VRE")
plt.plot(solar, label="solar")
plt.plot(twload, label="Load")
ylim = ax2.get_ylim()
#ax2.set_ylim([min(0,ylim[0]),123])
#ax2.set_xticks(ticks=range(skip_week*168+24, skip_week*168+9*24, 24), labels=range(skip_week*7+1, skip_week*7+9))
#ax2.set_xticks(ticks=range(0, 8*24, 24), labels=range(skip_week*7+1, skip_week*7+9))
ax2.set_xticks(ticks=xtick_index, labels=xtick_labels)
ax2.set_xlabel("Day")
ax2.set_ylabel("Power [GWh/h]")
ax2.legend()
ax2.set_title("Load and VRE during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/presentation_load_VRE.png", dpi=300)

# Net load
fig3, ax3 = plt.subplots()
#plt.plot(VRE+curtailment, label="VRE")
plt.plot(twload-VRE-curtailment, label="Net load")
plt.plot(twload, label="Load")
plt.axhline(color="k", linestyle=":", linewidth="1")
ylim = ax3.get_ylim()
ax3.set_ylim([min(0,ylim[0]), 123])
ax3.set_xticks(ticks=range(skip_week*168+24, skip_week*168+9*24, 24), labels=range(skip_week*7+1, skip_week*7+9))
ax3.set_xlabel("Day")
ax3.set_ylabel("Power [GWh/h]")
ax3.legend(loc="upper right")
ax3.set_title("Net load during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation/presentation_netload.png", dpi=300)

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
