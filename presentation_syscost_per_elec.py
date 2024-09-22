from my_utils import load_from_file
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import numpy as np
import pandas as pd
import os

#print current dir


fig_path = r"figures\presentation\p2"
os.makedirs(fig_path, exist_ok=True)

#"C:\Users\vijulk\OneDrive - Chalmers\notes.xlsx", Sheet3
# Load data
cost_df = pd.read_excel(r"H:\OneDrive - Chalmers\notes.xlsx", 
                        sheet_name="Sheet3", index_col=[0,1],header=0)
"""
		Brit	Iberia	Nordic
Total system cost [G€]	Full FC 	71.181	44.044	63.586
	No bat. FC	2.99	1.1	3.11
	No VRE FC	0.03	0	0.34
	No PtH FC	0.01	0	0.73
Thermal cycling cost [G€]	Full FC 	0.94	0.22	0.1
	No bat. FC	0.27	0.11	0.49
	No VRE FC	0	0	0.02
	No PtH FC	0	0	0.02
"""
cost_df.iloc[1:4] += cost_df.iloc[0]
cost_df.iloc[5:] += cost_df.iloc[4]
total_load = {
    "Brit": 1817013,
    "Iberia": 1704615,
    "Nordic": 2949582
}

# Calculate system cost per MWh [€/MWh]
sp_cost_df = cost_df.div(total_load, axis=1)*1e6

# Plot a bar chart with data from sp_cost_df.iloc[0:4]
# 2 clusters of bars, one for Nordic and one for Brit
# Each cluster will have 4 bars, one for each scenario
fig, ax = plt.subplots(figsize=(5,4))
bar_width = 0.2

labels = sp_cost_df.index.get_level_values(1).unique().to_list()
nordic = sp_cost_df.loc["Total system cost [G€]", "Nordic"].values  # y values for nordic
brit = sp_cost_df.loc["Total system cost [G€]", "Brit"].values  # y values for brit
nordic_x = [0+bar_width*i*1.1 for i in range(len(labels))]
brit_x = [1+bar_width*i*1.1 for i in range(len(labels))]
rects1 = ax.bar(nordic_x, nordic, bar_width, label=labels, color=sns.color_palette('ch:start=.2,rot=-.3',6)[::-1][1:5])
rects2 = ax.bar(brit_x, brit, bar_width, color=sns.color_palette('ch:start=.2,rot=-.3',6)[::-1][1:5])
#add markers for the thermal cycling cost
mark1 = ax.plot(nordic_x, sp_cost_df.loc["Thermal cycling cost [G€]", "Nordic"].values, 'd', color='black', label="Extra cycling cost")
mark2 = ax.plot(brit_x, sp_cost_df.loc["Thermal cycling cost [G€]", "Brit"].values, 'd', color='black')
plt.xticks([np.mean(nordic_x), np.mean(brit_x)], ["Nordic", "Brit"], fontsize=12)
plt.ylabel("System cost increase [€/MWh]", fontsize=12)
plt.legend(loc='lower center', bbox_to_anchor=(0.5, 1.03), ncol=1, fancybox=True)
plt.savefig(fig_path + "/syscost_per_elec.png", bbox_inches='tight', dpi=500, transparent=True)
print("Figure saved as syscost_per_elec.png in ", fig_path)
