import pickle
import os
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import load_from_file
# Gather the net load profiles of all years
# Sort them to get the net load duration curves
# Create an average net load duration curve
# Plot the average net load duration curve along with 2012 and 2016-2017

#in picklejar/ref999/ there are pickle files with the net load profiles
#there is also a file called PickleJar/ref999/netload_components_small_1980-2019.pickle that holds all of the net loads as a multiindexed (year,timestep) dataframe

# First, load the 1980-2019 net load profile
netload_allyears = load_from_file("PickleJar/ref999/netload_components_small_1980-2019.pickle")["net_load"]
# calculate the net load duration curve by sorting the net load profile for each year in descending order
netload_duration_allyears = netload_allyears.groupby(level=0, group_keys=False).apply(lambda x: x.sort_values(by='net_load',ascending=False))
#calculate the average net load duration curve
netload_duration_allyears = netload_duration_allyears.reset_index(level=1, drop=True)

# Create a new continuous range index for the second level
netload_duration_allyears['rank'] = netload_duration_allyears.groupby(level=0).cumcount() + 1
netload_duration_allyears = netload_duration_allyears.set_index('rank', append=True)

# Now, group by the new rank and compute the mean
average_net_load_duration = netload_duration_allyears.groupby(level=1).mean()

years_to_plot = ["2016-2017","2012"]#,"1989-1990","1994-1995"]
years_to_plot = ["2016-2017","2012","1989-1990","1994-1995"]
normalized = False
#normalized = True

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
if normalized:
    to_plot = average_net_load_duration / average_net_load_duration.max()
else:
    to_plot = average_net_load_duration
ax.plot(to_plot, label="Average", linewidth=2, color="black")

for year_str in years_to_plot:
    if normalized:
        data_for_year = duration_curves[year_str] / duration_curves[year_str].max()
    else:
        data_for_year = duration_curves[year_str]
    ax.plot(data_for_year, label=year_str, linewidth=1)
ax.set_xlabel("Hours")
if normalized:
    ax.set_ylabel("Normalized net load")
else:
    ax.set_ylabel("Net load [GW]")
ax.legend()
ax.grid()
if normalized:
    ax.set_title("Normalized net load duration curves")
else:
    ax.set_title("Net load duration curves")
#set the ymin to -0.1
ax.set_ylim(0, None)
plt.tight_layout()
#before saving, check if there already is a figure with the same name, and if so, add a number at the end
i = 1
os.makedirs("figures/netload_duration", exist_ok=True)
while os.path.exists(f"figures/netload_duration/figure_{'normalized_'*normalized}netload_duration_{i}.png"):
    i += 1
plt.savefig(f"figures/netload_duration/figure_{'normalized_'*normalized}netload_duration_{i}.png", dpi=500)


# identify the 5 years with the highest net load
peak_per_year = netload_allyears.groupby(level=0).max()
# sort the years by the peak net load
peak_per_year = peak_per_year.sort_values(by='net_load', ascending=False)
# print the 5 years with the highest net load
print("The 5 years with the highest net load are:")
for year in peak_per_year.index[:5]:
    print(f"{year}: {peak_per_year.loc[year].max():.2f} GW")

#repeat the peak part, but reseam the years to e.g. 1980-1981 where the july-dec of 1980 is the first half and the jan-june of 1981 is the second half
# step 1. restructure the netload_allyears dataframe have reseamed years
years_list = [netload_allyears.index.levels[0][i] for i in range(len(netload_allyears.index.levels[0]))]
reseamed_years = [f"{years_list[i]}-{years_list[i+1]}" for i in range(0,len(years_list)-1)]
#netload_allyears_reseamed = netload_allyears.copy()

#print(netload_allyears)
reseamed_df = pd.DataFrame()

# Iterate over unique years except the last one
unique_years = netload_allyears.index.get_level_values(0).unique()
for year in unique_years[:-1]:
    # July-December of current year
    first_half = netload_allyears.loc[year].iloc[4344:]
    # January-June of next year
    second_half = netload_allyears.loc[year+1].iloc[:4344]
    
    # Concatenate and add to the final DataFrame
    combined_data = pd.concat([first_half, second_half])
    combined_data.index = pd.MultiIndex.from_product([[f"{year}-{year+1}"], combined_data.index])
    reseamed_df = pd.concat([reseamed_df, combined_data])

# Display or save reseamed_df as needed
#print(reseamed_df)

# identify the 5 years with the highest net load
peak_per_year = reseamed_df.groupby(level=0).max()
# sort the years by the peak net load
peak_per_year = peak_per_year.sort_values(by='net_load', ascending=False)
# print the 5 years with the highest net load
print("The 10 reseamed years with the highest net load are:")
for year in peak_per_year.index[:10]:
    print(f"{year}: {peak_per_year.loc[year].max():.2f} GW")
