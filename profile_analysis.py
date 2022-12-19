import mat73
import matplotlib.pyplot as plt
import pickle
import pandas as pd
import numpy as np
from statistics import mean

"""

- VRE profile analysis -

- INPUT
profiles per cluster region

- OUTPUT
FLHs
generation duration curves
accumulated net-load deficiency
    deficiency = mean netload - hourly netload
CFD-plots for 40-year period and for individual years

"""


def make_pickles(year, VRE_profiles, cap, load):
    total_VRE_prod = (VRE_profiles * cap).sum(axis=1)
    net_load = load - total_VRE_prod
    leap_year = year%4 == 0
    mi = pd.MultiIndex.from_product([[year], range(1,8761+24*leap_year)], names=["year", "hour"])
    df_small = pd.DataFrame(index=mi)
    df_small["net_load"] = list(net_load)
    small = {"netload":df_small, "cap":cap}
    small_name = f"netload_{year}.pickle"
    pickle.dump(small, open("PickleJar\\"+small_name,'wb'))
    large = {"VRE_profiles":VRE_profiles, "cap":cap, "load":load}
    large_name = f"netload_components_{year}.pickle"
    pickle.dump(large, open("PickleJar\\"+large_name,'wb'))


def get_FLH(profile, weights=False):
    """

    Parameters
    ----------
    profile
    weights

    Returns
    -------
    return the sum of profile, or a weighted sum if profile is a list of profiles

    """
    if weights:
        return profile.sum(axis=0) * weights
    else:
        return profile.sum(axis=0)


def get_sorted(profile):
    _profile = profile.copy()
    return _profile.sort(reverse=True)


def get_netload_deficiency(VRE_profiles, all_cap, demand_profile, extra_demand):
    """

    Parameters
    ----------
    VRE_profiles
    all_cap

    Returns
    -------
    accumulated VRE deficiency against mean
    """
    total_VRE_prod = (VRE_profiles * all_cap).sum(axis=1)
    mean = total_VRE_prod.mean()
    diff = mean - total_VRE_prod
    accumulated = diff.cumsum(axis=0)
    return accumulated


def rolling_average(my_list, window_size, wrap_around=True):
    rolling_average_list = []
    if window_size % 2 == 0:
        window_size += 1
    steps_in_each_direction = int((window_size - 1) / 2)
    list_length_iterator = range(len(my_list))
    for my_list_index in list_length_iterator:
        window = []
        for step in range(-steps_in_each_direction, steps_in_each_direction + 1):
            i = my_list_index + step  # can be both negative and positive
            if wrap_around:
                index = i % len(my_list)  # to wrap around when index>len(mylist)
                window.append(my_list[index])
            elif i in list_length_iterator:  # disregard i outside of my_list if not wrapping around
                window.append(my_list[i])
        rolling_average_list.append(sum(window) / len(window))
    return rolling_average_list


def fast_rolling_average(my_list, window_size):
    df = pd.DataFrame(my_list)
    return df.rolling(window_size).mean().fillna(method="bfill")


def get_high_netload(threshold, rolling_average_days, VRE_profiles, all_cap, demand_profile, extra_demand=0):
    """

    Parameters
    ----------
    rolling_average_days: how many days to average over
    threshold: fraction of MAX LOAD which determines "high net-load"
    VRE_profiles: generation profiles of all VRE technologies
    all_cap: installed capacity of all VRE technologies
    demand_profile: hourly demand profiles
    extra_demand: 1-dim profile of extra loads, or yearly load to be divided evenly onto all hours

    Returns
    -------
    longest net_load as well as high net-load duration and start-point
    """
    if demand_profile.max()>1000: demand_profile = demand_profile/1000
    total_VRE_prod = (VRE_profiles * all_cap).sum(axis=1)
    print(f"Total VRE prod: {total_VRE_prod.sum()}")
    try: demand = demand_profile.sum(axis=1)
    except np.AxisError: demand = demand_profile
    if type(extra_demand) in [list, np.ndarray]:
        demand += extra_demand
    else:
        demand += extra_demand / 8760
    net_load = demand - total_VRE_prod
    net_load_RA = rolling_average(net_load, rolling_average_days * 24)
    print(f"Max RA net-load: {max(net_load_RA)}")
    print(f"Min RA net-load: {min(net_load_RA)}")
    print(f"Mean net-load: {mean(net_load_RA)}")
    threshold_to_beat = threshold * max(rolling_average(demand, rolling_average_days * 24))
    print(f"Threshold to beat: {threshold_to_beat}")
    high_netload = [i > threshold_to_beat for i in net_load_RA]  # list of True and False
    high_netload_durations = []
    high_netload_event_starts = []
    counter = 0
    for i, over_threshold in enumerate(high_netload):
        if over_threshold:  # add to the counter if net-load is high
            counter += 1
        elif counter > 0:  # if the net-load is low and we just had high net-load, save the event
            high_netload_durations.append(counter)
            high_netload_event_starts.append(i - counter)
            counter = 0
    if len(high_netload_durations)==0:
        high_netload_durations.append(0)
        high_netload_event_starts.append(0)
    return net_load, high_netload_durations, high_netload_event_starts, threshold_to_beat


pickle_file = "PickleJar\\data_results_3h.pickle"
mat_folder = f"C:\GISdata\output\\"
initial_results = pickle.load(open(pickle_file, "rb"))
scenario_name = "nordic_lowFlex_noFC_2040_3h"
print(initial_results[scenario_name].keys())
all_cap = initial_results[scenario_name]["tot_cap"]
all_cap["WOFF3","DE_N"]=60
all_cap["WONA4","DE_S"]=45

regions = ["SE_NO_N", "SE_S", "NO_S", "FI", "DE_N", "DE_S"]

# non_traditional_load = initial_results[scenario_name]["o_yearly_nontraditional_load"]
# non_traditional_load = non_traditional_load[non_traditional_load.index.get_level_values(level="stochastic_scenario")[0]]
non_traditional_load = pd.Series([
    8285.78,
    51514.8,
    93605.4,
    1148.72,
    7659.52,
    9178.34,
], index=regions)
WON = ["WONA" + str(i) for i in range(1, 6)]
WOFF = ["WOFF" + str(i) for i in range(1, 6)]
PV = ["PVPA" + str(i) for i in range(1, 6)]
VRE_tech = WON + WOFF + PV
all_cap = all_cap[all_cap.index.isin(VRE_tech, level=0)]
print(all_cap)
years = range(1980, 1983)
sites = range(1, 6)
region_name = "nordic_L"
VREs = ["WON", "WOFF", "solar"]
VRE_tech_dict = {"WON": WON, "WOFF": WOFF, "solar": PV}
VRE_tech_name_dict = {"WON": "WONA", "WOFF": "WOFF", "solar": "PVPA"}
filenames = {"WON": f"GISdata_windYEAR_{region_name}.mat", "WOFF": f"GISdata_windYEAR_{region_name}.mat",
             "solar": f"GISdata_solarYEAR_{region_name}.mat"}
profile_keys = {"WON": 'CFtime_windonshoreA', "WOFF": 'CFtime_windoffshore', 'solar': 'CFtime_pvplantA'}
capacity_keys = {"WON": 'capacity_onshoreA', "WOFF": 'capacity_offshore', 'solar': 'capacity_pvplantA'}
capacity = {"WON": all_cap[all_cap.index.isin(WON, level=0)], "WOFF": all_cap[all_cap.index.isin(WOFF, level=0)],
            'solar': all_cap[all_cap.index.isin(PV, level=0)]}
for year in years:
    print(f"Year {year}")
    leap = year%4==0
    VRE_profiles = pd.DataFrame(index=range(8760+leap*24),columns=pd.MultiIndex.from_product([VRE_tech, regions], names=["tech", "I_reg"]))
    FLHs = {}
    for VRE in VREs:
        print(f"- {VRE} -")
        filename = filenames[VRE].replace("YEAR", str(year))
        # [site,region]
        # if there is a time dimension, the dimensions are [time,region,site]
        VRE_mat = mat73.loadmat(mat_folder + filename)
        profiles = VRE_mat[profile_keys[VRE]]
        # VRE_cap = capacity[VRE]
        capacities = VRE_mat[capacity_keys[VRE]]
        # print(capacities)
        for site in sites:
            caps = capacities[:, 5 - site]
            caps.sort()
            print(f"Testing site {6 - site} where cap is {caps}")
            # testing the sites backwards to stop at the first feasible option
            if caps[0] > 1:
                viable_site = 5 - site
                print(f"best viable site is {viable_site + 1}")
                break
            elif site==5:
                viable_site = 4
                print(f"no 'viable' site found, using {viable_site + 1} instead")
        for site in sites:  # need another loop which wont break
            tech_name = VRE_tech_name_dict[VRE] + str(site)
            VRE_profiles[tech_name] = profiles[:, :, site - 1]
            # pot_cap = pd.DataFrame(capacities.T, index=sites, columns=regions, )
        FLHs[VRE] = get_FLH(profiles[:, :, :])
        #print(FLHs)#[:, viable_site - 1])
        # print(profiles[:, :, viable_site - 1])
    demand_filename = f'SyntheticDemand_nordic_L_ssp2-26-2050_{year}.mat'
    mat_demand = mat73.loadmat(mat_folder + demand_filename)
    demand = mat_demand["demand"]
    prepped_demand = demand.sum(axis=1)/1000
    prepped_demand += non_traditional_load.sum()/len(prepped_demand)
    threshold = 0.5
    mod = 1.5
    window_size_days = 3
    net_load, high_netload_durations, high_netload_event_starts, threshold_to_beat = get_high_netload(threshold, window_size_days,
                                                                                    VRE_profiles, all_cap*mod,
                                                                                    demand, sum(non_traditional_load))
    max_val = max(high_netload_durations)
    max_val_start = high_netload_event_starts[high_netload_durations.index(max_val)]

    print(f"These are the high_netload_durations: {high_netload_durations}")
    print(f"These are the start times: {high_netload_event_starts}")
    # accumulated = get_accumulated_deficiency(VRE_profiles,all_cap,demand)
    # print(net_load)
    plt.plot(rolling_average(net_load,24*window_size_days))
    plt.plot(prepped_demand, color="gray", linestyle="--")
    plt.axhline(y=mean(net_load),color="black", linestyle="-.")
    plt.axhline(y=threshold_to_beat, color="red")
    plt.axvline(x=max_val_start, color="red")
    plt.xticks(range(0,8760,730), labels=["1 Jan.", "1 Feb.", "1 Mar.", "1 Apr.", "1 May", "1 Jun.", "1 Jul.", "1 Aug.",
                                          "1 Sep.", "1 Oct.", "1 Nov.", "1 Dec."])
    # plt.legend(labels=regions)
    plt.title(f"Longest event in Year {year} is: {round(max(high_netload_durations)/24)} days and starts day {round(max_val_start/24)}")
    #plt.title(f"Year {year}, mean is {round(mean(net_load))} with mod={mod}")
    #plt.xlim([0,168*3])
    plt.tight_layout()
    plt.show()
    make_pickles(year,VRE_profiles,all_cap,prepped_demand)

# accumulated * potential cap
# accumulated * "cost-optimal" cap mix
# - one line per subregion
# - one line for wind and one for solar
# - one total per year
