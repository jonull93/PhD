import os
import pickle
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import cpu_count, Process, Queue
#from queue import Queue
import threading
import time as tm
import datetime as dt
from timeit import default_timer as timer
from my_utils import print_red, print_cyan, print_green, fast_rolling_average, print_magenta, print_blue, print_yellow, load_from_file, save_to_file
import scipy.io
import h5py
import json

"""
Inputs:
df of net load

Outputs:
CFD plot and VRE event df for fingerprint matching
"""

os.system('color')
print_cyan(f"Starting figure_CFD.py at {dt.datetime.now().strftime('%d-%m-%Y, %H:%M:%S')}")

# in \output\ there are subfolders called "ref#", save the name of the ref folder with the highest number
global ref_folder
def get_ref_folder():
    ref_folders = []
    for folder in os.listdir("PickleJar"):
        if folder.startswith("ref"):
            ref_folders.append(folder)
    ref_folders.sort(key=lambda x: int(x[3:6]))
    ref_folder = ref_folders[-1]
    # ask user whether to use the latest ref_folder or to enter a new one
    print(f"The latest ref in the PickleJar is: {ref_folder}")
    ref_folder_input = input("Enter the ref_folder to use (or press enter to use the latest): ")
    if ref_folder_input == "":
        print(f"Using ref_folder from PickleJar: {ref_folder}")
    elif ref_folder_input.isnumeric():
        ref_folder = "ref" + ref_folder_input
        print(f"Setting ref_folder to: {ref_folder}")
    else:
        if ref_folder_input.startswith("ref"):
            ref_folder = ref_folder_input
            print(f"Setting ref_folder to: {ref_folder}")
        else:
            raise ValueError(f"ref_folder {ref_folder_input} not recognized")
    return ref_folder


def sign(num):
    if num==0: return 1
    return np.sign(num)


def get_contour(Z, transpose=False):
    if transpose:
        Z = Z.T
    # Z is a 2D array of values
    # returns a 2D array of 0s and 1s where 1s are the contour (along rows, looking for non-zeros left to right)
    # for each row, find the last non-zero value and set the corresponding index in the contour array to 1
    contour = np.zeros(Z.shape)
    # if there are nan values, convert them to 0
    Z[np.isnan(Z)] = 0
    for i, row in enumerate(Z):
        if np.count_nonzero(row) == 0:
            continue
        last_nonzero = np.nonzero(row)[0][-1]  # returns a tuple (len=1) of arrays of indices
        contour[i, last_nonzero] = 1
    return contour


def fast_cfd(df_netload, xmin, xmax, amp_length=0.1, area_method=False, thread=False, debugging=False):
    # a significantly faster version of of the original recurrence-matrix function
    if not thread: thread = "main"
    df_freq = pd.DataFrame()
    output = {}
    net_loads_array = np.array(df_netload["net load"].values)
    amps = np.arange(xmin, xmax, amp_length).tolist()
    start_time = timer()
    if debugging: print("Amps1: ", end="")
    for amp in amps:
        if debugging: print(amp, end=",")
        # initiate variables before hour loop
        d = {'net load': net_loads_array, 'count1': 0, 'count2': 0}
        df_netload = pd.DataFrame(data=d)
        hours = df_netload.index
        previous_hour = hours[0]
        previous_net_load_val = net_loads_array[0]
        amp_positive = amp >= 0
        amp_negative = not amp_positive
        for i_h, hour in enumerate(hours):
            # net_load_val = df_netload.at[hour,'net load']
            net_load_val = net_loads_array[i_h]
            netload_greater_than_amp = net_load_val >= amp
            netload_smaller_than_amp = not netload_greater_than_amp
            previous_netload_greater_than_amp = previous_net_load_val >= amp
            previous_netload_smaller_than_amp = not previous_netload_greater_than_amp
            # both count1 and count2 are related to the duration of events
            if amp_positive and netload_greater_than_amp:
                # df_netload.set_value(hour, 'count1', df_netload.at[previous_hour,'count1']+1)
                try:
                    df_netload.at[hour, 'count1'] = df_netload.at[previous_hour, 'count1'] + 1
                except KeyError as e:
                    print(hour, amp)
                    print(df_netload.at[hour, 'count1'])
                    print(df_netload.at[previous_hour, 'count1'])
                    raise e
            elif amp_negative and netload_smaller_than_amp:
                # df_netload.set_value(hour, 'count1', df_netload.at[previous_hour,'count1']+1)
                try:
                    df_netload.at[hour, 'count1'] = df_netload.at[previous_hour, 'count1'] + 1
                except KeyError as e:
                    print(hour, amp)
                    print(df_netload.at[hour, 'count1'])
                    print(df_netload.at[previous_hour, 'count1'])
                    raise e
            # spara sedan varje periods längd vid sluttillfället
            if amp_positive and previous_netload_greater_than_amp and netload_smaller_than_amp:
                #            df_netload.set_value(previous_hour, 'count2', df_netload.at[previous_hour,'count1'])
                df_netload.at[previous_hour, 'count2'] = df_netload.at[previous_hour, 'count1']
            elif amp_negative and previous_netload_smaller_than_amp and netload_greater_than_amp:
                #            df_netload.set_value(previous_hour, 'count2', df_netload.at[previous_hour,'count1'])
                df_netload.at[previous_hour, 'count2'] = df_netload.at[previous_hour, 'count1']
            previous_hour = hour
            previous_net_load_val = net_load_val
        # this sets the recurrence by counting the durations for each amplitude
        s = df_netload.count2.value_counts()
        df_freq = pd.DataFrame(data=s)
        output[amp] = df_freq
    if debugging: print(f"{thread} finished building output[amp] after {round((timer() - start_time)/60, 1)} minutes. Now building df_out_tot")
    timer_dfouttot = timer()
    #df_out_tot = pd.DataFrame()
    df_out_list = []
    for amp in amps:
        df_out = output[amp]
        df_out = df_out.iloc[1:]
        df_out.index.name = 'Duration'
        df_out = pd.concat([df_out], keys=[amp], names=['Amplitude'])
        df_out.rename(columns={'count2': 'Occurences'}, inplace=True)
        df_out_list.append(df_out)
    df_out_tot = pd.concat(df_out_list) #roughly a 700*3000 dataframe
    print_green(f"time to build df_out_tot = {round((timer() - start_time)/60, 1)} min")
    if area_method:
        # this section takes almost all of the execution time and can probably be improved
        print_red(f"Starting second area_method loop with {len(df_out_tot.index)} rows at {dt.datetime.now().strftime('%H:%M:%S')}")
        start_time = timer()
        #print_red(df_out_tot.index.get_level_values(0).unique())
        # df_out_tot hold a single column and a few multiindexed rows
        if debugging: print("Amps2: ", end="")
        amps = df_out_tot.index.get_level_values(0).unique().tolist()
        for amp in amps: #roughly 700 amps
            if debugging: print(f"{amp},", end="")
            to_pass_on = 0
            df = df_out_tot.loc[amp].copy()
            df = df.reindex(range(0, df.index.max() + 1), fill_value=0).sort_index(ascending=False) # reindexing and sorting a 3000*1 dataframe 700 times cannot be efficient
            indexes = df_out_tot.loc[amp].index
            for index, val in df.iterrows(): # apparently using iterrows is generally discouraged due to its slow speed
                if (amp, index) in indexes:
                    df_out_tot.loc[(amp, index), :] += to_pass_on # the only thng slower than iterrows is supposedly updating a dataframe cell-by-cell
                else:
                    df_out_tot.loc[(amp, index), :] = to_pass_on
                to_pass_on = to_pass_on + val[0]
        if debugging: print("")
        print_green(f"Done with second area_method loop after {round((timer() - start_time)/60, 1)} minutes")
    #print(f"time to build CFD data = {round(timer() - start_time, 1)}")
    return df_out_tot

def faster_cfd(df_netload, xmin, xmax, amp_length=0.1, area_method=False, thread=False, debugging=False):
    # a significantly faster version of of the original recurrence-matrix function
    if not thread: thread = "main"
    df_freq = pd.DataFrame()
    output = {}
    net_loads_array = np.array(df_netload["net load"].values)
    amps = np.arange(xmin, xmax, amp_length).tolist()
    start_time = timer()
    if debugging: print("Amps1: ", end="")
    for amp in amps:
        if debugging: print(amp, end=",")
        # initiate variables before hour loop
        d = {'net load': net_loads_array, 'count1': 0, 'count2': 0}
        df_netload = pd.DataFrame(data=d)
        hours = df_netload.index
        previous_hour = hours[0]
        previous_net_load_val = net_loads_array[0]
        amp_positive = amp >= 0
        amp_negative = not amp_positive
        for i_h, hour in enumerate(hours):
            # net_load_val = df_netload.at[hour,'net load']
            net_load_val = net_loads_array[i_h]
            netload_greater_than_amp = net_load_val >= amp
            netload_smaller_than_amp = not netload_greater_than_amp
            previous_netload_greater_than_amp = previous_net_load_val >= amp
            previous_netload_smaller_than_amp = not previous_netload_greater_than_amp
            # both count1 and count2 are related to the duration of events
            if amp_positive and netload_greater_than_amp:
                # df_netload.set_value(hour, 'count1', df_netload.at[previous_hour,'count1']+1)
                try:
                    df_netload.at[hour, 'count1'] = df_netload.at[previous_hour, 'count1'] + 1
                except KeyError as e:
                    print(hour, amp)
                    print(df_netload.at[hour, 'count1'])
                    print(df_netload.at[previous_hour, 'count1'])
                    raise e
            elif amp_negative and netload_smaller_than_amp:
                # df_netload.set_value(hour, 'count1', df_netload.at[previous_hour,'count1']+1)
                try:
                    df_netload.at[hour, 'count1'] = df_netload.at[previous_hour, 'count1'] + 1
                except KeyError as e:
                    print(hour, amp)
                    print(df_netload.at[hour, 'count1'])
                    print(df_netload.at[previous_hour, 'count1'])
                    raise e
            # spara sedan varje periods längd vid sluttillfället
            if amp_positive and previous_netload_greater_than_amp and netload_smaller_than_amp:
                #            df_netload.set_value(previous_hour, 'count2', df_netload.at[previous_hour,'count1'])
                df_netload.at[previous_hour, 'count2'] = df_netload.at[previous_hour, 'count1']
            elif amp_negative and previous_netload_smaller_than_amp and netload_greater_than_amp:
                #            df_netload.set_value(previous_hour, 'count2', df_netload.at[previous_hour,'count1'])
                df_netload.at[previous_hour, 'count2'] = df_netload.at[previous_hour, 'count1']
            previous_hour = hour
            previous_net_load_val = net_load_val
        # this sets the recurrence by counting the durations for each amplitude
        s = df_netload.count2.value_counts()
        df_freq = pd.DataFrame(data=s)
        output[amp] = df_freq
    if debugging: print(f"{thread} finished building output[amp] after {round((timer() - start_time)/60, 1)} minutes. Now building df_out_tot")
    timer_dfouttot = timer()
    #df_out_tot = pd.DataFrame()
    df_out_list = []
    for amp in amps:
        df_out = output[amp]
        df_out = df_out.iloc[1:]
        df_out.index.name = 'Duration'
        df_out = pd.concat([df_out], keys=[amp], names=['Amplitude'])
        df_out.rename(columns={'count2': 'Occurences'}, inplace=True)
        df_out_list.append(df_out)
    df_out_tot = pd.concat(df_out_list) #roughly a 700*3000 dataframe
    print_green(f"time to build df_out_tot = {round((timer() - start_time)/60, 1)} min")
    if area_method:
        # this section takes almost all of the execution time and can probably be improved
        print_red(f"Starting second area_method loop with {len(df_out_tot.index)} rows at {dt.datetime.now().strftime('%H:%M:%S')}")
        start_time = timer()
        #print_red(df_out_tot.index.get_level_values(0).unique())
        # df_out_tot hold a single column and a few multiindexed rows
        if debugging: print("Amps2: ", end="")
        amps = df_out_tot.index.get_level_values(0).unique().tolist()
        amp_dfs = {amp: 0. for amp in amps}
        for amp in amps: #roughly 700 amps
            if debugging: print(f"{amp},", end="")
            df = df_out_tot.loc[amp].copy()
            df = df.reindex(range(0, df.index.max() + 1), fill_value=0).sort_index(ascending=False) # reindexing and sorting a 3000*1 dataframe 700 times cannot be efficient
            #indexes = df_out_tot.loc[amp].index
            #for index, val in df.iterrows(): # apparently using iterrows is generally discouraged due to its slow speed
            #    if (amp, index) in indexes:
            #        df_out_tot.loc[(amp, index), :] += to_pass_on # the only thng slower than iterrows is supposedly updating a dataframe cell-by-cell
            #    else:
            #        df_out_tot.loc[(amp, index), :] = to_pass_on
            #    to_pass_on = to_pass_on + val[0]
            df["cumulative"] = df["Occurences"].cumsum()
            amp_dfs[amp] = df["cumulative"]
        df_out_tot = pd.concat(amp_dfs) # this alternative to the above loop appears to have almost completely eliminated the execution time of this section
        df_out_tot.index.names = ["Amplitude", "Duration"]
        df_out_tot.rename("Occurences", inplace=True)
        if debugging: print("")
        print_green(f"Done with second area_method loop after {round((timer() - start_time)/60, 1)} minutes")
    #print(f"time to build CFD data = {round(timer() - start_time, 1)}")
    return df_out_tot


def create_df_out_tot(year, xmin, xmax, ref_folder, rolling_hours=12, amp_length=1, area_mode_in_cfd=True, debugging=False, thread=False):
    print_cyan(f"create_df_out_tot({year}, {xmin}, {xmax}, {rolling_hours}, {amp_length}, {area_mode_in_cfd})")
    data = load_from_file(f"PickleJar\\{ref_folder}\\netload_components_small_{year}")
    #VRE_profiles = data["VRE_profiles"]
    #load = data["total_hourly_load"]
    #cap = data["cap"]
    """
    VRE_gen = data["VRE_gen"]
    load = data["total_hourly_load"]
    if type(load) == dict:
        load_list = []
        for _year, load in load.items():
            load_list += list(load)
        load = np.array(load_list)
    if load.ndim > 1:
        load = load.sum(axis=1)
    #net_load = -(VRE_profiles * cap).sum(axis=1) + load
    net_load = load - VRE_gen
    print_red(net_load)
    print_red(type(net_load))"""
    net_load = data["net_load"].squeeze()
    #print_cyan(net_load)
    #print_cyan(type(net_load))
    # print(VRE_profiles.shape, net_load.shape, cap.shape)
    # d = {'net load': net_load,'count1':0,'count2':0}
    # df_netload = fast_rolling_average(pd.DataFrame(data=d),1)
    RA_netload = fast_rolling_average(net_load, rolling_hours)
    #print(array_netload)
    df_netload = pd.DataFrame(data={'net load': RA_netload, 'count1': 0, 'count2': 0})
    xmax = max(xmax, int(math.ceil(df_netload["net load"].max())))
    xmin = min(xmin, int(math.floor(df_netload["net load"].min())))
    print_cyan(f"Done preparing the netload for {year} ({round(max(RA_netload))}/{round(RA_netload.mean())}/{round(min(RA_netload))}), starting fast_cfd now")
    df_out_tot = faster_cfd(df_netload, xmin, xmax, amp_length=amp_length, area_method=area_mode_in_cfd, debugging=debugging, thread=thread)
    return df_out_tot, xmin, xmax


def make_cfd_plot(ax, Xnetload, Ynetload, Znetload, xmin=False, xmax=False, ymin=False, ymax=False,
                  color=plt.cm.turbo, vmin=False, vmax=False):
    if not vmin:
        vmin = round(Znetload[~np.isnan(Znetload)].min(),2)
    if not vmax:
        vmax = round(Znetload[~np.isnan(Znetload)].max(),2)
    #print_red(f"vmin={vmin}, vmax={vmax}")
    cm = ax.pcolormesh(Xnetload, Ynetload, Znetload, alpha=1, linewidth=0, shading='nearest',
                   cmap=color, vmin=vmin, vmax=vmax)  # , alpha=0.7)
    if xmin and xmax:
        ax.set_xlim([xmin, xmax])
    if ymin and ymax:
        ax.set_ylim([ymin, ymax])
    from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.grid(visible=True, color="black", lw=1, axis="both", alpha=0.15, which="both")
    ax.set_xlabel("Amplitude [GW]")
    ax.set_ylabel("Duration [days]")
    return cm

def main(year, ref_folder, amp_length=1, rolling_hours=12, area_mode_in_cfd=True, write_files=True, read_pickle=True, xmin=0,
         xmax=0, ymin=0, ymax=0, weights=False, thread_nr=False, debugging=False, sum_func="", errors=False):
    if not thread_nr:
        thread_nr = "MAIN"
    if type(year) != list and type(year) != tuple:
        #print_cyan(f"\nStarting loop for year -- {year} --")
        pickle_read_name = rf"PickleJar\{ref_folder}\{year}_CFD_netload_df_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}"
        pickle_dump_name = rf"PickleJar\{ref_folder}\{year}_CFD_netload_df_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}"
        # df_netload = df_netload.reset_index()[["net load", "count1", "count2"]]
        try:
            if not read_pickle: raise ImportError
            #print_yellow(f" Attempting to read pickle")#{pickle_read_name}")
            df_out_tot = load_from_file(pickle_read_name)
        except Exception as e:
            #if read_pickle: print_red(f"Failed due to {type(e)} .. creating a new one instead")
            start_time = timer()
            df_out_tot, xmin, xmax = create_df_out_tot(year, xmin, xmax, ref_folder, rolling_hours=rolling_hours, amp_length=amp_length, debugging=debugging, thread=thread_nr, area_mode_in_cfd=area_mode_in_cfd)
            # 248s at 1 year then more changes and now 156-157s at 1 year
            end_time = timer()
            print(f"elapsed time to build CFD in thread {thread_nr} = {round(end_time - start_time, 1)}")
            if write_files: 
                print_yellow(f"Writing {pickle_dump_name}")
                save_to_file(df_out_tot, pickle_dump_name)
            else:
                print_yellow(f"NOT writing {pickle_dump_name}")
        df_reset = df_out_tot.reset_index()
        df_reset.columns = ['Amplitude', 'Duration', 'Occurrence']
        print(f" max/mean/min net load for {year} is {round(df_reset['Amplitude'].max())}/{round(df_reset['Amplitude'].mean())}/{round(df_reset['Amplitude'].min())}")
        if int(math.ceil(df_reset["Amplitude"].max())) > xmax-2: print_magenta(f"OBS: max(Amplitude)={int(math.ceil(df_reset['Amplitude'].max()))} >= xmax-2")
        xmax = max(xmax, int(math.ceil(df_reset["Amplitude"].max())))
        xmin = min(xmin, int(math.floor(df_reset["Amplitude"].min())))
        df_pivot = df_reset.pivot(index='Amplitude', columns='Duration')
        # df_reset["Energy"] = df_reset["Amplitude"]*df_reset["Duration"]*np.sign(df_reset["Amplitude"])
        Y = df_pivot.columns.levels[1].values/24  # convert y axis values to days
        ymin = min(ymin, Y.min())
        ymax = max(ymax, Y.max())
        X = df_pivot.index.values
        Z = df_pivot.values
        Ynetload, Xnetload = np.meshgrid(Y, X)
        if write_files:
            scipy.io.savemat(f"output\\{ref_folder}\\heatmap_values_{year}_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.mat",
                         {"amplitude": Ynetload, "duration": Xnetload, "recurrance": Z})
        if year == "1980-2019":
            #Z = Z / 40
            z_cap = 100
            None
        else:
            z_cap = 50
        Znetload = np.where(Z > z_cap, z_cap, Z)
        Znetload = np.where(Znetload == 0., np.nan, Znetload)
        fig, ax = plt.subplots()
        cm = make_cfd_plot(ax, Xnetload, Ynetload, Znetload, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)
        ax.set_title(f"Net load recurrence for {year}, {rolling_hours}h rolling average")
        fig.colorbar(cm)
        fig.tight_layout()
        filename = f"figures\\CFD plots\\{ref_folder}\\cfd_{year}_amp{amp_length}_window{rolling_hours}{'_area' * area_mode_in_cfd}.png"
        fig.savefig(filename, dpi=500)
        plt.close(fig)

    else:  # this is the loop for multiple years from fingerprintmatching.jl
        print_cyan(f"\nStarting loop for years -- {year} --")
        year, weights = year
        if len(year) != len(weights):
            if len(year) == len(weights) + 2:
                weights = [0.025, 0.025] + weights
            else:
                raise ValueError(f"years {year} and weights {weights} must have the same length")
        m = {}
        Zs = {}
        for y in year:
            print_cyan(f"\nReading mat for year -- {y} --")
            with h5py.File(
                    f"output/{ref_folder}/heatmap_values_{y}_amp{amp_length}_window{rolling_hours}{'_area' * area_mode_in_cfd}_padded.mat",
                    "r") as f:
                Ynetload = np.array(f["amplitude"])
                Xnetload = np.array(f["duration"])
                Zs[y] = np.array(f["recurrance"])
            #m[y] = scipy.io.loadmat(f"output\\heatmap_values_{y}_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}_padded.mat")
        # load the reference Znetload from 1980-2019
        try:
            with h5py.File(
                f"output/{ref_folder}/heatmap_values_1980-2019_amp{amp_length}_window{rolling_hours}{'_area' * area_mode_in_cfd}.mat",
                "r") as f:
                Z_ref = np.array(f["recurrance"])
        except OSError:
            _ = scipy.io.loadmat(f"output/{ref_folder}\\heatmap_values_1980-2019_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.mat")
            Z_ref = _["recurrance"]

        # make sure all matrices in Zs have 0s instead of nans
        for y in year:
            Zs[y] = np.where(np.isnan(Zs[y]), 0, Zs[y])
        # construct Z using m and the weights
        Z = sum([Zs[y] * w for y, w in zip(year, weights)])
        # make both Z and Z ref have 0s instead of nans
        Z = np.where(np.isnan(Z), 0, Z) #redundant
        Z_ref = np.where(np.isnan(Z_ref), 0, Z_ref)
        # get the difference matrix
        Z_diff = Z - Z_ref.T/40
        print_yellow(f"{year}\n" + 
                     f"Min and max of Z_diff: {Z_diff.min():.01f}, {Z_diff.max():.01f}\n" + 
                     f"Actual max of Z: {Z.max():.01f}")
        
        if sum_func == "sqrt_sum":
            sum_func_latex = r"$\sum_{i,j} \sqrt{|M^{diff}_{i,j}|}$"
            Z_error = np.sqrt(np.abs(Z_diff)) #Z_error is the diff matrix with sqrt of each element
        elif sum_func == "abs_sum":
            sum_func_latex = r"$\sum_{i,j} |M^{diff}_{i,j}|$"
            Z_error = np.abs(Z_diff) #Z_error is the diff matrix with abs of each element
        elif sum_func == "sse":
            sum_func_latex = r"$\sum_{i,j} (M^{diff}_{i,j})^2$"
            Z_error = Z_diff**2 #Z_error is the diff matrix with square of each element
        elif sum_func == "log_sum":
            sum_func_latex = r"$\sum_{i,j} \log(|M^{diff}_{i,j}|+1)$"
            Z_error = np.log(np.abs(Z_diff)+1) #Z_error is the diff matrix with log of each element
        else:
            raise NotImplementedError(f"sum_func {sum_func} not recognized")
        Z_contour = {y: get_contour(Zs[y]) for y in year}
        _diff = round(Z_error.sum())/round(errors[str(year)])
        if _diff < 0.99 or _diff > 1.01:
            print_red(f"Error in {year}: {Z_error.sum():.01f} != {errors[str(year)]:.01f}")
        # restore nans so that plot is white instead of black
        Z = np.where(Z == 0., np.nan, Z)
        Z_ref = np.where(Z_ref == 0., np.nan, Z_ref)
        Z_diff = np.where(Z_diff == 0., np.nan, Z_diff)
        Z_error = np.where(Z_error == 0., np.nan, Z_error)
        #Z = np.where(Z > 30, 30, Z)
        #Z_diff = np.where(Z_diff > 50, 50, Z_diff)
        Z = np.where(Z == 0., np.nan, Z)
        fig, axes = plt.subplots(1, 3, figsize=(10, 5))
        try: cm = make_cfd_plot(axes[0], Xnetload, Ynetload, Z, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, vmax=20)
        except Exception as e:
            print_red(f"Error in {year} when plotting Z: {e}")
            raise e
        # print the contours for each year from the dictionary Z_contour (year: 2d-array), alternate colors
        colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        for i, y in enumerate(year):
            axes[0].contour(Xnetload, Ynetload, Z_contour[y], colors=colors[i], linewidths=0.5)
            #add the year to the legend, but reformat the years from 1980-2019 to '80-'19
            axes[0].plot([], [], color=colors[i], label=f"'{y[2:4]}-'{y[7:]}")
        axes[0].legend()
        fig.colorbar(cm, ax=axes[0])
        cm = make_cfd_plot(axes[1], Xnetload, Ynetload, Z_diff, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
                           color="seismic", vmin=-5, vmax=5)
        fig.colorbar(cm, ax=axes[1])
        axes[0].set_title(r"$\sum_{i} M_{i} w_{i}$")
        axes[1].set_title(r"$M_{diff} = \sum_{i} M_{i} w_{i} - M_{ref}$")
        #axes[1].set_title(f"Zref-Z = diff_mat")
        # set vmax to the 99th percentile of the absolute values of Z_error
        vmax = np.nanpercentile(Z_error, 99)
        cm = make_cfd_plot(axes[2], Xnetload, Ynetload, Z_error, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,vmax=vmax)
        fig.colorbar(cm, ax=axes[2])
        axes[2].set_title(f"{sum_func_latex} = "+f"{errors[str(year)]:,.0f}".replace(",", " "))
        fig.tight_layout()
        with open(f"results\\{ref_folder}/most_recent_results.txt", "r") as f:
            results_folder_name = f.read().strip()
        filename = f"{results_folder_name}/{errors[str(year)]:.0f}_{year}.png"
        fig.savefig(filename, dpi=500)
        plt.close(fig)

    #plt.show()
    return xmin, xmax, ymin, ymax


def crawler(queue_years,thread_nr,amp_length,rolling_hours,area_mode_in_cfd,write_pickle,read_pickle,xmin,xmax,ymin,ymax,sum_func,errors,ref_folder):
    while not queue_years.empty():
        year = queue_years.get()  # fetch new work from the Queue
        weights = False
        if type(year) == list:
            year, weights = year
        print_green(f"Starting Year {year} in thread {thread_nr}. Remaining years: {queue_years.qsize()}")
        start_time_thread = timer()
        main(year,ref_folder,amp_length=amp_length,rolling_hours=rolling_hours,area_mode_in_cfd=area_mode_in_cfd,write_files=write_pickle,
             read_pickle=read_pickle,xmin=xmin,xmax=xmax,ymin=ymin,ymax=ymax,weights=weights,thread_nr=thread_nr, sum_func=sum_func, errors=errors)
        print_green(f"   Finished Year {year} after {round(timer() - start_time_thread, 1)} seconds")
        #queue_years.task_done()
    return None

def initiate(ref_folder,rolling_window=12):
    print_magenta(f"ref_folder: {ref_folder}")
    os.makedirs(f"figures\\CFD plots\\{ref_folder}", exist_ok=True)

    amp_length = 1
    test_mode = False
    write_pickle = not test_mode
    area_mode_in_cfd = True
    read_pickle = True  # should be false if new netload_components have been created since last run
    debugging = False
    years = range(1980, 2020)
    years_iter2 = [f"{years[i]}-{years[i+1]}" for i in range(len(years)-1)]
    print(f"{years_iter2 = }")
    long_period = f"1980-2019"

    xmax= 0
    xmin, xmax, ymin, ymax = main(long_period, ref_folder, amp_length=amp_length, rolling_hours=rolling_window, area_mode_in_cfd=area_mode_in_cfd,
                                  write_files=True, read_pickle=True, debugging=debugging)
    print("Xmin =", xmin, "Xmax =", xmax, "Ymin =", ymin, "Ymax =", round(ymax, 1))
    queue_years = Queue(maxsize=0)
    sum_func = ""
    make_fingerprinted_figures = os.path.exists(f"results\\{ref_folder}/most_recent_results.txt")
    if make_fingerprinted_figures: # Load results from most recent fingerprinting run
        with open(f"results\\{ref_folder}/most_recent_results.txt", "r") as f:
            results_folder_name = f.read().strip()
#            results_folder_name = r"results\ref14\FP sse Jun_06_16.52.18".strip()
        print_cyan(f"Loading results from {results_folder_name}...")
        import json
        with open(f"{results_folder_name}/results.json", "r") as f:
            results = json.load(f)
        with open(f"{results_folder_name}/parameters.txt", "r") as f:
            parameters = json.load(f)
        combinations = results["combinations"]
        combinations_strings = [str(comb).replace("'",'"') for comb in combinations]
        weights = results["best_weights"]
        errors = results["best_errors"]
        # In weights and errors, remove 'Any' from the keys
        weights = {key.replace('Any',''): weights[key] for key in weights}
        errors = {key.replace('Any',''): errors[key] for key in errors}
        sum_func = results["sum_func"]
        maxtime = parameters["maxtime"]
        #find all non-float values in errors and remove the corresponding key from weights, errors, combinations and combinations_strings
        for key in list(errors.keys()):
            try:
                float(errors[key])
            except TypeError:
                print_red(f"Bad value for {key} = {errors[key]}")
                del weights[key]
                del errors[key]
                del combinations[combinations_strings.index(key)]
                del combinations_strings[combinations_strings.index(key)]
        #errors is a dictionary, sort it by value
        errors_sorted = sorted(errors.items(), key=lambda x: x[1])
        #save the best 100 combinations to a JSON file
        with open(f"{results_folder_name}/best_100.json", "w") as f:
            to_dump = [key.replace('Any','').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(',') for key, value in errors_sorted[:100]]
            json.dump(to_dump, f, indent=4)
        #save the best 50 combinations to a JSON file
        with open(f"{results_folder_name}/best_50.json", "w") as f:
            to_dump = [key.replace('Any','').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(',') for key, value in errors_sorted[:50]]
            json.dump(to_dump, f, indent=4)
        with open(f"{results_folder_name}/best_25.json", "w") as f:
            to_dump = [key.replace('Any','').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(',') for key, value in errors_sorted[:25]]
            json.dump(to_dump, f, indent=4)
        with open(f"{results_folder_name}/best_10.json", "w") as f:
            to_dump = [key.replace('Any','').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(',') for key, value in errors_sorted[:10]]
            json.dump(to_dump, f, indent=4)
        with open(f"{results_folder_name}/best_5.json", "w") as f:
            to_dump = [key.replace('Any','').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(',') for key, value in errors_sorted[:5]]
            json.dump(to_dump, f, indent=4)
        with open(f"{results_folder_name}/best_2x.json", "w") as f:
            #calculate how many combinations are within 200% of the best case
            best_keys = [key for key, value in errors_sorted if value <= errors_sorted[0][1] * 2]
            to_dump = [key.replace('Any','').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(',') for key in best_keys]
            json.dump(to_dump, f, indent=4)
        with open(f"{results_folder_name}/best_1.5x.json", "w") as f:
            # calculate how many combinations are within 200% of the best case
            best_keys = [key for key, value in errors_sorted if value <= errors_sorted[0][1] * 1.5]
            to_dump = [
                key.replace('Any', '').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(
                    ',') for key in best_keys]
            json.dump(to_dump, f, indent=4)
        with open(f"{results_folder_name}/best_1.3x.json", "w") as f:
            # calculate how many combinations are within 200% of the best case
            best_keys = [key for key, value in errors_sorted if value <= errors_sorted[0][1] * 1.3]
            to_dump = [
                key.replace('Any', '').replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(
                    ',') for key in best_keys]
            json.dump(to_dump, f, indent=4)
        # save the keys to the items in errors_sorted where the value is at most 5% higher than the best error
        for percent in list(range(5,55,5))+[100]:
            percent = percent/10
            best_keys = [key for key, value in errors_sorted if value <= errors_sorted[0][1] * (1 + percent/100)]
            print_green(f"-- Combinations within {percent}% of the best case: {len(best_keys)}")
            # each element in best_keys is a list of strings, save each string in a list
            best_years = [key.replace('"', '').replace('[', '').replace(']', '').replace(' ', '').split(',') for key in best_keys]
            # each element in best_years is a list of strings, save each string in a list
            best_years = list(set([year for sublist in best_years for year in sublist])) # [int(year[:4]) for sublist in best_years for year in sublist]))
            best_years.sort()
            print(f"Unique years within {percent} of the best case: {len(best_years)}")
            print(f"Combinations that {len(best_years)} years can make: {math.comb(len(best_years)-1, 3)*2}")
            print(f"Years: {best_years}")
        #if combinations is longer than 8, only take the first 4 and last 4
        if len(combinations) > 8:
            combinations = combinations[:6] + combinations[-2:]
            combinations_strings = combinations_strings[:6] + combinations_strings[-2:]
            print_yellow(f"Making figures for {len(combinations_strings)} / {len(errors)} combinations")
            weights = {key: weights[key] for key in combinations_strings}
            errors = {key: errors[key] for key in combinations_strings}
        # make errors also accept keys with only ' instead of "
        for comb in combinations_strings:
            alt_comb = comb.replace('"',"'")
            errors[alt_comb] = errors[comb]
        print(f"{combinations_strings[0] = }")
        #for i, comb in enumerate(combinations):
        #    errors[comb] = errors[combinations_strings[i]]

        combined_results = [(comb, [round(weights[key][i], 3) for i in range(len(weights[key]))]) for key, comb in zip(combinations_strings, combinations) if sum(weights[key]) > 0]
        #print(combined_results)
        for i in combined_results:
            queue_years.put(i)
            continue
    for year in years_iter2:
        if True:#not make_fingerprinted_figures: 
            queue_years.put(year)
        continue
    print("Queue contains", queue_years.qsize(), "years")
    threads = {}
    thread_nr = {}
    num_threads = min(max(cpu_count() - 2, 4), int(queue_years.qsize()))

    workers = []
    for i in range(num_threads):
        #print_cyan(f'Starting thread {i + 1}')
        #worker = threading.Thread(target=crawler, args=(), daemon=False)
        #if errors is not defined, make it None
        if "errors" not in locals():
            errors = None
        workers.append(Process(target=crawler, args=(queue_years,i,amp_length,rolling_window,area_mode_in_cfd,write_pickle,read_pickle,xmin,xmax,ymin,ymax,sum_func,errors,ref_folder)))
        # setting threads as "daemon" allows main program to exit eventually even if these dont finish correctly
        workers[-1].start()
        tm.sleep(0.05)
    
    for worker in workers:
        worker.join()

if __name__ == "__main__":
    ref_folder = get_ref_folder()
    #ref_folder = "ref23"
    initiate(ref_folder, rolling_window=12)
