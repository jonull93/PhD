import mat73
import matplotlib.pyplot as plt
import pickle
import pandas as pd
import numpy as np
from os import mkdir
from statistics import mean
from my_utils import print_red, print_green, print_cyan, fast_rolling_average

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


def make_pickles(year, VRE_profiles, cap, load, non_traditional_load):
    total_VRE_prod = (VRE_profiles * cap).sum(axis=1)
    # net_load = load - total_VRE_prod
    # leap_year = year % 4 == 0
    # mi = pd.MultiIndex.from_product([[year], range(1, 8761 + 24 * leap_year)], names=["year", "hour"])
    # df_small = pd.DataFrame(index=mi)
    # df_small["net_load"] = list(net_load)
    # small = {"netload": df_small, "cap": cap}
    # small_name = f"netload_{year}.pickle"
    # pickle.dump(small, open("PickleJar\\" + small_name, 'wb'))
    large = {"VRE_profiles": VRE_profiles, "cap": cap, "load": load, "non_traditional_load": non_traditional_load}
    large_name = f"netload_components_{year}.pickle"
    pickle.dump(large, open("PickleJar\\" + large_name, 'wb'))


def make_gams_profiles(year, VRE_profiles, load, pot_cap, ):
    """

    Parameters
    ----------
    year, str
    VRE_profiles, dataframe with tech and reg in the header, and time as the index
    load, list or array/series that list() can be used on
    pot_cap, series with (cap,reg) multiindex

    Returns
    -------

    """
    from datetime import datetime
    from my_utils import write_inc_from_df_columns, write_inc
    global regions
    timesteps = ['h' + str(i + 1).zfill(4) for i in range(len(VRE_profiles.index))]
    timestamp = datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
    comment = [f"Made by Jonathan Ullmark at {timestamp}"] + \
              [
                  f"Through profile_analysis.py (quality-of-life scripts repo) with data gathered from globalenergygis\\dev"]
    path = "output\\"
    VRE_filename = f"gen_profile_VRE_{year}.inc"
    load_filename = f"hourly_load_{year}.inc"
    cap_filename = f"potential_cap_VRE_{year}.inc"
    VRE_df = pd.DataFrame(VRE_profiles.unstack())
    VRE_df.index.names = ["tech", "I_reg", "timestep"]
    VRE_df.index = VRE_df.index.set_levels(timesteps, level="timestep")
    VRE_df = VRE_df.dropna().clip(lower=1e-7).round(5)
    write_inc_from_df_columns(path, VRE_filename, VRE_df, comment)
    if type(load) != pd.DataFrame:
        load = np.around(load, 4)
        # print_red(load,pd.DataFrame(load))
        load_df = pd.DataFrame(load, columns=regions, index=timesteps)
    else:
        load_df = load
    load_df = pd.DataFrame(load_df.round(4).unstack())
    load_df.index.names = ["I_reg", "timestep"]
    load_df.index = load_df.index.set_levels(timesteps, level="timestep")
    load_df.index = load_df.index.set_levels(regions, level="I_reg")
    # print_cyan(load_df)
    write_inc_from_df_columns(path, load_filename, load_df, comment=comment)
    write_inc_from_df_columns(path, cap_filename, pot_cap.to_frame(), comment=comment)


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


"""def rolling_average(my_list, window_size, wrap_around=True):
    if type(my_list)==pd.Series: my_list = list(my_list)
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
    return rolling_average_list"""


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
    if type(demand_profile) == dict:
        load_list = []
        for year, load in demand_profile.items():
            load_list += list(load)
        if len(set([type(i) for i in load_list])) > 1:
            print_red("! More than one datatype in load_list in get_high_netload()")
            print_red(load[1943:1946])
        demand_profile = np.array(load_list)

    if demand_profile.max() > 1000: demand_profile = demand_profile / 1000
    total_VRE_prod = (VRE_profiles * all_cap).sum(axis=1)
    print(f"Total VRE prod: {round(total_VRE_prod.sum() / 1000)} TWh")
    try:
        demand = demand_profile.sum(axis=1)
    except np.AxisError:
        demand = demand_profile
    if type(extra_demand) in [list, np.ndarray]:
        demand += extra_demand
    else:
        demand += extra_demand / 8760
    net_load = demand - total_VRE_prod
    net_load_RA = fast_rolling_average(net_load, rolling_average_days * 24)
    try:
        print(
            f"Max / Mean / Min rolling average net-load: {round(max(net_load_RA))} / {round(mean(net_load_RA))} / {round(min(net_load_RA))}")
    except ValueError as e:
        print_red(sum(net_load_RA))
        print_red(len(net_load_RA))
        types = [type(i) for i in net_load_RA]
        print_red(types.index(type(pd.Series())))
        # print_red(types)
        print_red(net_load_RA[1943:1946])
        # print_red(type(net_load_RA[0]))
        # print_red(sum(net_load_RA[:])
        # net_load_RA
        raise e
    # print(f"Min RA net-load: {min(net_load_RA)}")
    # print(f"Mean net-load: {mean(net_load_RA)}")
    rolling_average_netload = fast_rolling_average(demand, rolling_average_days * 24).stack().tolist()
    # convert dataframe rolling_average_netload to list
    threshold_to_beat = threshold * max(rolling_average_netload)
    print(f"Threshold to beat: {round(threshold_to_beat)}")
    # print_cyan(threshold,rolling_average_netload.max(), threshold*float(rolling_average_netload.max()))
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
    if over_threshold is True and counter > 0:  # if the last hour should have triggered the elif
        high_netload_durations.append(counter)
        high_netload_event_starts.append(i - counter)
    if len(high_netload_durations) == 0:
        high_netload_durations.append(0)
        high_netload_event_starts.append(0)
    return net_load, high_netload_durations, high_netload_event_starts, threshold_to_beat


def find_year_and_hour(index, start_year=1980):
    year = start_year
    previous_hours = 0
    while True:
        hours_in_this_year = 8760 + 24 * (year % 4 == 0)
        if index < hours_in_this_year + previous_hours:
            return year, index - previous_hours
        previous_hours += hours_in_this_year
        year += 1


pickle_file = "PickleJar\\data_results_3h.pickle"
mat_folder = f"input\\"
# initial_results = pickle.load(open(pickle_file, "rb"))
# scenario_name = "nordic_lowFlex_noFC_2040_3h"
# print(initial_results[scenario_name].keys())
# all_cap = initial_results[scenario_name]["tot_cap"]
# all_cap["WOFF3","DE_N"]=60
# all_cap["WONA4","DE_S"]=45
cap_df = pd.read_excel("input\\cap_ref.xlsx", sheet_name="ref1", header=0, index_col=[0, 1], engine="openpyxl")
# print(cap_df)
all_cap = cap_df.squeeze()
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
PVR = ["PVR" + str(i) for i in range(1, 6)]
VRE_tech = WON + WOFF + PV + PVR
all_cap = all_cap[all_cap.index.isin(VRE_tech, level=0)]
# print(all_cap)
years = range(1980, 2020)
sites = range(1, 6)
# instead of switching to a new year at Jan 1st, a seam in summer gives a whole winter period
# 4344 = hours until 1st of July

region_name = "nordic_L"
VREs = ["WON", "WOFF", "solar", "solar_rooftop"]
VRE_tech_dict = {"WON": WON, "WOFF": WOFF, "solar": PV, "solar_rooftop": PVR}
VRE_tech_name_dict = {"WON": "WONA", "WOFF": "WOFF", "solar": "PVPA", "solar_rooftop": "PVR"}
filenames = {"WON": f"GISdata_windYEAR_{region_name}.mat", "WOFF": f"GISdata_windYEAR_{region_name}.mat",
             "solar": f"GISdata_solarYEAR_{region_name}.mat", "solar_rooftop": f"GISdata_solarYEAR_{region_name}.mat"}
profile_keys = {"WON": 'CFtime_windonshoreA', "WOFF": 'CFtime_windoffshore', 'solar': 'CFtime_pvplantA',
                'solar_rooftop': 'CFtime_pvrooftop'}
capacity_keys = {"WON": 'capacity_onshoreA', "WOFF": 'capacity_offshore', 'solar': 'capacity_pvplantA',
                 'solar_rooftop': 'capacity_pvrooftop'}
capacity = {"WON": all_cap[all_cap.index.isin(WON, level=0)], "WOFF": all_cap[all_cap.index.isin(WOFF, level=0)],
            'solar': all_cap[all_cap.index.isin(PV, level=0)],
            'solar_rooftop': all_cap[all_cap.index.isin(PVR, level=0)]}
fig_path = "figures\\profile_analysis\\"
try:
    mkdir(fig_path)
except FileExistsError:
    None


def remake_profile_seam(new_profile_seam=4344, profile_starts_in_winter=False, years=range(1980,2020)):
    VRE_profile_dict = {}
    load_dict = {}
    for i_y, year in enumerate(years):
        #print(f"Year {year}")
        netload_components = pickle.load(open(f"PickleJar\\netload_components_{year}.pickle", "rb"))
        VRE_profile_dict[year] = netload_components["VRE_profiles"]
        load_dict[year] = netload_components["load"]
        if year == years[0]: continue  # make new VRE_profiles with seam in summer
        print_cyan(f" - Making profiles for years {years[i_y - 1]}-{year}")
        # VRE_profile = pd.concat([VRE_profile_dict[years[i_y-1]].loc[4464:], VRE_profile_dict[years[i_y]].loc[:4464]])
        VRE_df_fall = pd.DataFrame(VRE_profile_dict[years[i_y - 1]][new_profile_seam:])
        VRE_df_spring = pd.DataFrame(VRE_profile_dict[years[i_y]][:new_profile_seam])
        # print(load_dict[years[i_y - 1]],load_dict[years[i_y - 1]].shape)
        # print_green(pd.DataFrame(load_dict[years[i_y - 1]]))
        load_df_fall = pd.DataFrame(load_dict[years[i_y - 1]][new_profile_seam:])
        load_df_spring = pd.DataFrame(load_dict[years[i_y]][:new_profile_seam])
        if profile_starts_in_winter:
            VRE_df_fall.index = pd.RangeIndex(new_profile_seam, new_profile_seam + len(VRE_df_fall))
            VRE_df = pd.concat([VRE_df_spring, VRE_df_fall])
            load_df_fall.index = pd.RangeIndex(new_profile_seam, new_profile_seam + len(load_df_fall))
            load_df = pd.concat([load_df_spring, load_df_fall])
        else:
            VRE_df_fall.index = pd.RangeIndex(len(VRE_df_fall))
            VRE_df_spring.index = pd.RangeIndex(len(VRE_df_fall), new_profile_seam + len(VRE_df_fall))
            VRE_df = pd.concat([VRE_df_fall, VRE_df_spring])
            load_df_fall.index = pd.RangeIndex(len(load_df_fall))
            load_df_spring.index = pd.RangeIndex(len(load_df_fall), new_profile_seam + len(load_df_fall))
            load_df = pd.concat([load_df_fall, load_df_spring])
        # print_cyan(VRE_profile_dict[years[i_y - 1]], VRE_profile_dict[years[i_y]])
        print_green(VRE_df)
        # print_cyan(load)
        make_gams_profiles(f"{years[i_y - 1]}-{year}", VRE_df, load_df, all_cap)
        make_pickles(f"{years[i_y - 1]}-{year}", VRE_df, all_cap, load_df, non_traditional_load)
    return None


def separate_years(years, add_nontraditional_load=True, make_output=True, make_figure=False, window_size_days=3,
                   threshold=0.5):
    print_cyan(f"Starting the 'separate_years()' script")
    if type(years) == type(1980): years = [years]
    for year in years:
        print_green(f"Year {year}")
        leap = year % 4 == 0
        VRE_profiles = pd.DataFrame(index=range(8760 + leap * 24),
                                    columns=pd.MultiIndex.from_product([VRE_tech, regions], names=["tech", "I_reg"]))
        FLHs = {}
        for VRE in VREs:
            filename = filenames[VRE].replace("YEAR", str(year))
            VRE_mat = mat73.loadmat(mat_folder + filename)
            # [site,region]
            # if there is a time dimension, the dimensions are [time,region,site]
            profiles = VRE_mat[profile_keys[VRE]]
            for site in sites:  # need another loop which wont break
                tech_name = VRE_tech_name_dict[VRE] + str(site)
                VRE_profiles[tech_name] = profiles[:, :, site - 1]
                # pot_cap = pd.DataFrame(capacities.T, index=sites, columns=regions, )
            FLHs[VRE] = get_FLH(profiles[:, :, :])
        demand_filename = f'SyntheticDemand_nordic_L_ssp2-26-2050_{year}.mat'
        mat_demand = mat73.loadmat(mat_folder + demand_filename)
        demand = mat_demand["demand"]
        prepped_tot_demand = demand.sum(axis=1) / 1000
        if add_nontraditional_load: prepped_tot_demand += non_traditional_load.sum() / len(prepped_tot_demand)
        # print_red(demand.shape,non_traditional_load.shape)
        # print_red(type(demand), type(non_traditional_load))
        # print_red(demand, non_traditional_load)
        prepped_demand = demand / 1000  # + np.array(non_traditional_load)*np.ones(demand.shape)
        mod = 1
        net_load, high_netload_durations, high_netload_event_starts, threshold_to_beat = get_high_netload(threshold,
                                                                                          window_size_days,
                                                                                          VRE_profiles,
                                                                                          all_cap * mod,
                                                                                          demand,
                                                                                          sum(non_traditional_load))
        max_val = max(high_netload_durations)
        max_val_start = high_netload_event_starts[high_netload_durations.index(max_val)]

        # print(f"These are the high_netload_durations: {high_netload_durations}")
        # print(f"These are the start times: {high_netload_event_starts}")
        sorted_high_netload_durations = high_netload_durations.copy()
        sorted_high_netload_durations.sort(reverse=True)
        print_red(f"Sorted high_netload_durations: {sorted_high_netload_durations}")
        # accumulated = get_accumulated_deficiency(VRE_profiles,all_cap,demand)
        # print(net_load)
        if make_figure:
            plt.plot(fast_rolling_average(net_load, 24 * window_size_days), label="Net load")
            plt.plot(prepped_tot_demand, color="gray", linestyle="--", label="Load" )
            plt.axhline(y=mean(net_load), color="black", linestyle="-.", label="Average net load")
            plt.axhline(y=threshold_to_beat, color="red", label=f"{threshold}% of peak load")
            plt.axvline(x=max_val_start, color="red", label="Start of longest period")
            plt.xticks(range(0, 8760, 730),
                       labels=["1 Jan.", "1 Feb.", "1 Mar.", "1 Apr.", "1 May", "1 Jun.", "1 Jul.", "1 Aug.",
                               "1 Sep.", "1 Oct.", "1 Nov.", "1 Dec."])
            # plt.legend(labels=regions)
            plt.title(
                f"Longest event in Year {year} is: {round(max(high_netload_durations) / 24)} days and starts day {round(max_val_start / 24)}")
            plt.ylabel("Load [GW]")
            plt.xlabel("Date")
            plt.legend()
            # plt.xlim([0,168*3])
            plt.tight_layout()
            # plt.show()
            plt.savefig(f"{fig_path}over{int(threshold * 100)}_netload_events_{year}.png", dpi=400)
            plt.close()
        # print_cyan(VRE_profiles)
        # print_green(all_cap)
        # print_red(prepped_tot_demand)
        if make_output:
            make_pickles(year, VRE_profiles, all_cap, prepped_demand, non_traditional_load)
            make_gams_profiles(year, VRE_profiles, prepped_demand, all_cap)
            VRE_profile_dict = {}
            load_dict = {}
    return net_load


def combined_years(years, threshold=0.5, window_size_days=3):
    print_cyan(f"Starting the 'combined_years()' script")
    VRE_profiles = pd.DataFrame(columns=pd.MultiIndex.from_product([VRE_tech, regions], names=["tech", "I_reg"]))
    demands = {}
    for year in years:
        print_green(f"- Reading data for Year {year}")
        leap = year % 4 == 0
        VRE_profile = pd.DataFrame(index=range(8760 + 24 * leap),
                                   columns=pd.MultiIndex.from_product([VRE_tech, regions], names=["tech", "I_reg"]))
        # regions = ["SE_NO_N", "SE_S", "NO_S", "FI", "DE_N", "DE_S"]
        FLHs = {}
        for VRE in VREs:  # ["WON", "WOFF", "solar", "solar_rooftop"]
            # print(f"- {VRE} -")
            filename = filenames[VRE].replace("YEAR", str(year))
            # [site,region]
            # if there is a time dimension, the dimensions are [time,region,site]
            VRE_mat = mat73.loadmat(mat_folder + filename)
            profiles = VRE_mat[profile_keys[VRE]]
            for site in sites:
                tech_name = VRE_tech_name_dict[VRE] + str(site)
                VRE_profile[tech_name] = profiles[:, :, site - 1]
                # pot_cap = pd.DataFrame(capacities.T, index=sites, columns=regions, )
            FLHs[VRE] = get_FLH(profiles[:, :, :])
        VRE_profile.index = pd.MultiIndex.from_product([[year], [f"h{h:04}" for h in range(1, len(VRE_profile) + 1)]],
                                                       names=["year", "timestep"])
        VRE_profiles = pd.concat([VRE_profiles, VRE_profile])
        VRE_profiles.index = pd.MultiIndex.from_tuples(VRE_profiles.index)
        error_labels = []
        for label, col in VRE_profiles.items():
            if pd.isna(max(col)) != pd.isna(sum(col)):
                print_red("inconsistent NA at", label)
                error_labels.append(label)
        demand_filename = f'SyntheticDemand_nordic_L_ssp2-26-2050_{year}.mat'
        mat_demand = mat73.loadmat(mat_folder + demand_filename)
        demand = mat_demand["demand"]  # np.ndarray
        if len(set([type(i) for i in demand])) > 1:
            print_red("! More than one datatype in demand in combined_years()")
        print_green("\nAverage net-load per region:")
        print_green(regions)
        print_green((-(VRE_profile * all_cap).sum(axis=0).sum(level="I_reg") + demand.sum(
            axis=0) / 1000 + non_traditional_load) / 8760)
        prepped_tot_demand = demand.sum(axis=1) / 1000
        prepped_tot_demand += non_traditional_load.sum() / len(prepped_tot_demand)
        demands[year] = demand.sum(axis=1) / 1000
        # print_red(demands[year].shape)
        print(
            f"VRE_profiles and demands are now appended and the lengths are {len(VRE_profiles)} and {sum([len(load) for load in demands.values()])}, respectively")
    if len(error_labels) > 0:
        print_red(VRE_profiles[error_labels].loc[(slice(None), "h0012"), :])
    else:
        print_green("No missing profiles :)")
    mod = 1
    net_load, high_netload_durations, high_netload_event_starts, threshold_to_beat = get_high_netload(threshold,
                                                                                                      window_size_days,
                                                                                                      VRE_profiles,
                                                                                                      all_cap * mod,
                                                                                                      demands,
                                                                                                      sum(non_traditional_load))
    max_val = max(high_netload_durations)
    max_val_start = high_netload_event_starts[high_netload_durations.index(max_val)]
    print(f"These are the high_netload_durations: {high_netload_durations}")
    print(f"These are the start times: {high_netload_event_starts}")
    sorted_high_netload_durations = high_netload_durations.copy()  # event length in days
    sorted_high_netload_durations.sort(reverse=True)
    print_red(f"Sorted high_netload_durations (days): {sorted_high_netload_durations}")
    index_longest_event = high_netload_durations.index(sorted_high_netload_durations[0])
    index_second_longest_event = high_netload_durations.index(sorted_high_netload_durations[1])
    year_of_longest_event, starthour_of_longest_event = find_year_and_hour(
        high_netload_event_starts[index_longest_event])
    print_red(
        f"The longest event ({round(sorted_high_netload_durations[0] / 24)} days) start during Year {year_of_longest_event}, Hour {starthour_of_longest_event}")
    year_of_second_longest_event, starthour_of_second_longest_event = find_year_and_hour(
        high_netload_event_starts[index_second_longest_event])
    print_red(
        f"The second longest event ({round(sorted_high_netload_durations[1] / 24)} days) start during Year {year_of_second_longest_event}, Hour {starthour_of_second_longest_event}")
    # accumulated = get_accumulated_deficiency(VRE_profiles,all_cap,demand)
    # print(net_load)
    make_pickles(f"{years[0]}-{years[-1]}", VRE_profiles, all_cap, demands, non_traditional_load)


separate_years(years, threshold=0.33, make_output=True, make_figure=True)
#combined_years(years)
combined_years(years,threshold=0.33)
remake_profile_seam()


"""net_load = separate_years(1980, add_nontraditional_load=False, make_figure=True, make_output=False, window_size_days=1)

from timeit import default_timer as timer
start_time = timer()
for i in range(20):
    a = rolling_average(net_load,window_size=1)
end_time = timer()
print(f"elapsed time slow = {round(end_time - start_time, 1)}")
start_time = timer()

for i in range(20):
    b = fast_rolling_average(net_load, window_size=24, center=True, min_periods=1)
end_time = timer()
print(f"elapsed time fast = {round(end_time - start_time, 1)}")

a = pd.DataFrame(data=a)
#plt.plot(a)
plt.plot(b)
#plt.plot(a-b)
plt.show()
print(a)
print(b)
#print(a.rolling(5, center=True).mean())

#for i in range(len(a)):
#        error += (a[i] - b.iloc[i])**2
#print(f" Error = {error}")
"""
# accumulated * potential cap
# accumulated * "cost-optimal" cap mix
# - one line per subregion
# - one line for wind and one for solar
# - one total per year
