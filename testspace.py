import sys
import os
import pickle
import order_cap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from order_cap import wind
from my_utils import print_red, print_green, print_cyan
import mat73

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

'''
## Step 1: Read Hourly Profile

First, we need to read the hourly profile from the given file. We can do this using the `pandas` library.

'''
import pandas as pd

# Read the hourly profile from the given file
df = pd.read_excel(r"C:\Users\jonull\git\python\input\test_household_loadprofile.xlsx", engine="openpyxl")/30.8*0.12
'''

## Step 2: Calculate Average Hourly Value

Next, we need to calculate the average hourly value for each hour of the day. We can do this by looping through each hour and calculating the average value for that hour.

'''
# Create a list to store the average hourly values
average_hourly_value = []
hourly_values = np.zeros((24, 8785//24))
monthly_values = np.zeros((12,8784//12))
summer_slice = slice(int(366/4),int(3*366/4))
winter_slice = [i for i in range(0,int(366/4))]+[i for i in range(int(3*366/4),366)]
print(summer_slice)
# Loop through each hour
for index,val in df.iterrows():
    hour_of_day = index%24
    day = int(index/24)
    # Calculate the average value for the current hour
    hourly_values[hour_of_day,day] = val[0]
print(hourly_values)
for hour in range(24):
    average_hourly_value.append(hourly_values[hour,summer_slice].mean())

fig, ax = plt.subplots()
ax.boxplot(hourly_values[:,summer_slice].T, showfliers=False, whis=[25,75])
plt.xlabel("Timme")
plt.ylabel("Förbrukning [kW]")
plt.title("Uppskattad last i F6-10 under sommarhalvåret\nRektanglarna visar medel, lägsta 25% samt högsta 25%")
plt.savefig(r"C:\Users\jonull\git\python\figures\lastprofil.png")
plt.show()
plt.clf()
exit()

# Append the average value to the list
# average_hourly_value.append(avg_value)
'''

## Step 3: Plot Average Hourly Value and Print Variance

Finally, we can plot the average hourly value and print the statistical variance for each hour.

'''
# Import matplotlib for plotting
import matplotlib.pyplot as plt

# Plot the average hourly value
plt.plot(average_hourly_value)
plt.title("Average Hourly Value")
plt.xlabel("Hour")
plt.ylabel("Value")
plt.show()

# Print the statistical variance for each hour
for hour, value in enumerate(average_hourly_value):
    print("Hour {}: Variance = {}".format(hour, value))



exit()
years = range(1980,2020)

ref_cap = mat73.loadmat(r"C:\Users\jonull\git\python\input\GISdata_solar1980_nordic_L.mat")["capacity_pvplantA"][2,:]
#print(ref_cap)
caps = []
for year in years:
    filename = rf"C:\Users\jonull\git\python\input\old\GISdata_solar{year}_nordic_L.mat"
    caps.append(mat73.loadmat(filename)["capacity_pvplantA"][2,:])

y1 = [i[0] for i in caps]
y2 = [i[1] for i in caps]
plt.plot(years,y1,label="-1")
plt.axhline(ref_cap[0])
plt.plot(years,y2,color="r",label="-2")
plt.axhline(ref_cap[1],color="r")
plt.legend()
plt.show()

file_suffix = ""
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
#timestep = 3
#data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))


def aggregate_in_df(df, index_list: list, new_index: str):
    temp = df.loc[df.index.intersection(index_list)].sum()
    df.drop(index_list, inplace=True, errors='ignore')
    df.loc[new_index] = temp
    return df
