import pickle
import os
import pandas as pd
import matplotlib.pyplot as plt
# Gather the net load profiles of all years
# Sort them to get the net load duration curves
# Create an average net load duration curve
# Plot the average net load duration curve along with 2012 and 2016-2017

#in picklejar/ref999/ there are pickle files with the net load profiles
#there is also a file called PickleJar/ref999/netload_components_small_1980-2019.pickle that holds all of the net loads as a multiindexed (year,timestep) dataframe

# First, load the 1980-2019 net load profile
netload_allyears = pickle.load(open("PickleJar/ref999/netload_components_small_1980-2019.pickle", "rb"))["net_load"]
# calculate the net load duration curve by sorting the net load profile for each year in descending order
netload_duration_allyears = netload_allyears.groupby(level=0, group_keys=False).apply(lambda x: x.sort_values(by='net_load',ascending=False))
#calculate the average net load duration curve
netload_duration_allyears = netload_duration_allyears.reset_index(level=1, drop=True)

# Create a new continuous range index for the second level
netload_duration_allyears['rank'] = netload_duration_allyears.groupby(level=0).cumcount() + 1
netload_duration_allyears = netload_duration_allyears.set_index('rank', append=True)

# Now, group by the new rank and compute the mean
average_net_load_duration = netload_duration_allyears.groupby(level=1).mean()

years_to_plot = ["2016-2017","2012",]

def extract_data_for_year(year_str, df):
    if "-" in year_str:
        start_year, end_year = map(int, year_str.split("-"))
        # Extract second half of the start year
        start_half = df.loc[(start_year, slice(4381, 8760)), :]
        # Extract first half of the end year
        end_half = df.loc[(end_year, slice(1, 4380)), :]
        return pd.concat([start_half, end_half])
    else:
        year = int(year_str)
        return df.loc[year]

# Initialize an empty dictionary to store the duration curves for each year or year range
duration_curves = {}

for year_str in years_to_plot:
    data_for_year = extract_data_for_year(year_str, netload_allyears)
    sorted_data = data_for_year.sort_values(by='net_load', ascending=False)
    duration_curves[year_str] = pd.Series(sorted_data['net_load'].values)

print(duration_curves)
# Now, duration_curves contains the sorted net load duration curves for each specified year or year range

# Plot the average net load duration curve along with the specified years
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(average_net_load_duration / average_net_load_duration.max(), label="Average", linewidth=2, color="black")
for year_str in years_to_plot:
    data_for_year = duration_curves[year_str]
    ax.plot(data_for_year / data_for_year.max(), label=year_str, linewidth=1)
ax.set_xlabel("Hours")
ax.set_ylabel("Net load [GW]")
ax.legend()
ax.grid()
ax.set_title("Net load duration curves")
#set the ymin to -0.1
ax.set_ylim(0, 1.02)
plt.tight_layout()
#before saving, check if there already is a figure with the same name, and if so, add a number at the end
i = 1
os.makedirs("figures/netload_duration", exist_ok=True)
while os.path.exists(f"figures/netload_duration/figure_netload_duration_{i}.png"):
    i += 1
plt.savefig(f"figures/netload_duration/figure_netload_duration_{i}.png", dpi=500)


# identify the 5 years with the highest net load
peak_per_year = netload_allyears.groupby(level=0).max()
# sort the years by the peak net load
peak_per_year = peak_per_year.sort_values(by='net_load', ascending=False)
# print the 5 years with the highest net load
print("The 5 years with the highest net load are:")
for year in peak_per_year.index[:5]:
    print(f"{year}: {peak_per_year.loc[year].max():.2f} GW")
