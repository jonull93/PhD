import os
import pickle
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import cpu_count
from queue import Queue
import threading
import time as tm
from timeit import default_timer as timer
from my_utils import print_red, print_cyan, print_green, fast_rolling_average
import scipy.io

"""
Inputs:
df of net load

Outputs:
CFD plot and VRE event df for fingerprint matching
"""

os.system('color')


def sign(num):
    if num==0: return 1
    return np.sign(num)


def fast_cfd(df_netload, xmin, xmax, amp_length=0.1, area_method=False):
    df_freq = pd.DataFrame()
    output = {}
    # print("index = ", hours)
    net_loads_array = np.array(df_netload["net load"].values)
    # print("vals = ", net_loads_array)
    # print("len of vals = ", len(net_loads_array))
    amps = np.arange(xmin, xmax, amp_length).tolist()
    # print("length of amps:", len(amps))
    start_time = timer()
    for amp in amps:
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
    if area_method and False:
        for amp in amps:  # smidge and add all edges towards the vertical middle
            my_range = range(0, amp, amp_length*sign(amp))
            for amp2 in my_range:
                output[amp2] = output[amp2].add(output[amp], fill_value=0)
        for amp in amps:  # smidge and add all areas downwards
            None
    # df_out=pd.DataFrame(data=output, index=[amp])
    # df_out = pd.DataFrame()
    #print(f"time to build df_freq for all amps = {round(timer() - start_time, 1)}")
    #start_time = timer()
    df_out_tot = pd.DataFrame()
    for amp in amps:
        df_out = output[amp]
        df_out = df_out.iloc[1:]
        df_out.index.name = 'Duration'
        df_out = pd.concat([df_out], keys=[amp], names=['Amplitude'])
        df_out.rename(columns={'count2': 'Occurences'}, inplace=True)
        df_out_tot = pd.concat([df_out_tot, df_out])
    #print(f"time to build df_out_tot = {round(timer() - start_time, 1)}")
    if area_method:
        #start_time = timer()
        #print_red(df_out_tot.index.get_level_values(0).unique())
        # df_out_tot hold a single column and a few multiindexed rows
        for amp in df_out_tot.index.get_level_values(0).unique():
            to_pass_on = 0
            df = df_out_tot.loc[amp].copy()
            df = df.reindex(range(0, df.index.max() + 1), fill_value=0).sort_index(ascending=False)
            indexes = df_out_tot.loc[amp].index
            for index, val in df.iterrows():
                if (amp, index) in indexes:
                    df_out_tot.loc[(amp, index), :] += to_pass_on
                else:
                    df_out_tot.loc[(amp, index), :] = to_pass_on
                to_pass_on = to_pass_on + val[0]
    #print(f"time to build CFD data = {round(timer() - start_time, 1)}")
    return df_out_tot


def main(year, amp_length=1, rolling_hours=12, area_mode_in_cfd=True, write_pickle=True, read_pickle=True, xmin=0, xmax=0, ymin=0, ymax=0, weights=False):
    if type(year) != list and type(year) != tuple:
        print_cyan(f"\nStarting loop for year -- {year} --")
        pickle_read_name = rf"PickleJar\{year}_CFD_netload_df_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.pickle"
        pickle_dump_name = rf"PickleJar\{year}_CFD_netload_df_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.pickle"

        # df_netload = df_netload.reset_index()[["net load", "count1", "count2"]]
        try:
            if not read_pickle: raise ImportError
            df_out_tot = pickle.load(open(pickle_read_name, "rb"))
        except Exception as e:
            if read_pickle: print_red(f"Failed to read {pickle_read_name} due to {type(e)}")
            data = pickle.load(open(f"PickleJar\\netload_components_{year}.pickle", "rb"))
            VRE_profiles = data["VRE_profiles"]
            load = data["load"]
            cap = data["cap"]
            if type(load) == dict:
                load_list = []
                for _year, load in load.items():
                    load_list += list(load)
                load = np.array(load_list)
            if load.ndim > 1:
                load = load.sum(axis=1)
            net_load = -(VRE_profiles * cap).sum(axis=1) + load
            # print(VRE_profiles.shape, net_load.shape, cap.shape)
            # d = {'net load': net_load,'count1':0,'count2':0}
            # df_netload = fast_rolling_average(pd.DataFrame(data=d),1)
            array_netload = fast_rolling_average(net_load, rolling_hours)
            df_netload = pd.DataFrame(data={'net load': array_netload, 'count1': 0, 'count2': 0})
            xmax = max(xmax, int(math.ceil(df_netload["net load"].max())))
            xmin = min(xmin, int(math.floor(df_netload["net load"].min())))
            start_time = timer()
            df_out_tot = fast_cfd(df_netload, xmin, xmax, amp_length=amp_length, area_method=area_mode_in_cfd)
            # 248s at 1 year then more changes and now 156-157s at 1 year
            end_time = timer()
            print(f"elapsed time to build CFD in thread {thread_nr[threading.get_ident()]} = {round(end_time - start_time, 1)}")
            if write_pickle: pickle.dump(df_out_tot, open(pickle_dump_name, 'wb'))
        #print(df_out_tot.iloc[:40])
        #print(df_out_tot)
        df_reset = df_out_tot.reset_index()
        df_reset.columns = ['Amplitude', 'Duration', 'Occurrence']
        xmax = max(xmax, int(math.ceil(df_reset["Amplitude"].max())))
        xmin = min(xmin, int(math.floor(df_reset["Amplitude"].min())))
        df_pivot = df_reset.pivot(index='Amplitude', columns='Duration')
        filtered_df = df_reset[df_reset['Amplitude'].round(1) == 25.5]
        #print("Filtered df =", filtered_df)
        # df_reset["Energy"] = df_reset["Amplitude"]*df_reset["Duration"]*np.sign(df_reset["Amplitude"])
        # unique_amps, unique_amps_index = np.unique(df_reset["Amplitude"],return_index=True)
        # print(df_pivot[df_pivot.columns[df_pivot.columns.get_level_values(1) > 375]].to_string())
        # print(df_pivot[df_pivot.columns[df_pivot.columns.get_level_values(1) > 1300]].fillna(0)[df_pivot != 0])
        # print(df_pivot[df_pivot["Duration"] >1300].fillna(0).sum())
        Y = df_pivot.columns.levels[1].values/24
        ymin = min(ymin, Y.min())
        ymax = max(ymax, Y.max())
        X = df_pivot.index.values
        Z = df_pivot.values
        #print_cyan("Y =", Y, Y.shape)
        # print_green("X =", X, X.shape)
        #print_red("Z =", Z)
        Ynetload, Xnetload = np.meshgrid(Y, X)
        scipy.io.savemat(f"output\\heatmap_values_{year}_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.mat",
                         {"amplitude": Ynetload, "duration": Xnetload, "recurrance": Z})
    else:
        if len(year) != len(weights):
            raise ValueError("year and weights must have the same length")
        m = {}
        for y in year:
            m[y] = scipy.io.loadmat(f"output\\heatmap_values_{y}_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.mat")
        # construct Y_netload, Xnetload and Z using m and the weights
        Ynetload = sum([m[y]["amplitude"] * w for y, w in zip(year, weights)])
        Xnetload = sum([m[y]["duration"] * w for y, w in zip(year, weights)])
        Z = sum([m[y]["recurrance"] * w for y, w in zip(year, weights)])

    Znetload = np.where(Z > 75, 75, Z)
    # print({"amplitude":Xnetload, "duration":Ynetload, "recurrance":Znetload})
    #Z_testing = np.nan_to_num(Znetload)
    #print(Z_testing.sum(axis=0), Z_testing.sum(axis=0).shape)
    # import matplotlib as mpl
    # mpl.rcParams["patch.force_edgecolor"]=True
    fig, ax = plt.subplots()
    ax.pcolormesh(Xnetload, Ynetload, Znetload, alpha=1, linewidth=0, shading='nearest',
                   cmap=plt.cm.turbo)  # , alpha=0.7)
    ax.set_xlim([xmin, xmax])
    ax.set_ylim([ymin, ymax])
    from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.grid(visible=True, color="black", lw=1, axis="both", alpha=0.15, which="both")
    ax.set_xlabel("Amplitude [GW]")
    ax.set_ylabel("Duration [days]")
    ax.set_title(f"Amplitude-Duration-Recurrence for {year}, {rolling_hours}h window")
    fig.tight_layout()
    fig.savefig(f"figures\\profile_analysis\\cfd_{year}_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.png", dpi=500)
    plt.close(fig)
    #plt.show()
    return xmin, xmax, ymin, ymax


def crawler():
    thread_nr[threading.get_ident()] = len(thread_nr) + 1
    while not queue_years.empty():
        year = queue_years.get()  # fetch new work from the Queue
        weights = False
        if type(year) == list:
            year, weights = year
        print_green(f"Starting Year {year} in thread {thread_nr[threading.get_ident()]}. Remaining years: {queue_years.qsize()}")
        start_time_thread = timer()
        main(year,amp_length=amp_length,rolling_hours=rolling_hours,area_mode_in_cfd=area_mode_in_cfd,write_pickle=write_pickle,
             read_pickle=read_pickle,xmin=xmin,xmax=xmax,ymin=ymin,ymax=ymax,weights=weights)
        print_green(f"   Finished Year {year} after {round(timer() - start_time_thread, 1)} seconds")
        queue_years.task_done()
    return None


amp_length = 1
rolling_hours = 12
test_mode = False
write_pickle = not test_mode
area_mode_in_cfd = True
read_pickle = True
years = range(1980, 1983)
years_iter2 = [f"{years[i]}-{years[i+1]}" for i in range(len(years)-1)]
trio_combinations = [("2010-2011", "1982-1983", "1984-1985")]
trio_weights = [(0.5, 0.25, 0.25)]
long_period = f"1980-2019"
xmax= 0
xmin, xmax, ymin, ymax = main(long_period, amp_length=amp_length, rolling_hours=rolling_hours, area_mode_in_cfd=area_mode_in_cfd,
                              write_pickle=True, read_pickle=True)
print("Xmin =", xmin, "Xmax =", xmax, "Ymin =", ymin, "Ymax =", ymax)
queue_years = Queue(maxsize=0)
for i in range(len(trio_combinations)):
    queue_years.put([trio_combinations[i], trio_weights[i]])
for year in years_iter2:
    queue_years.put(year)
print("Queue contains", queue_years.qsize(), "years")
threads = {}
thread_nr = {}
num_threads = min(max(cpu_count() - 2, 4), len(years))

for i in range(num_threads):
    print_cyan(f'Starting thread {i + 1}')
    worker = threading.Thread(target=crawler, args=(), daemon=False)
    # setting threads as "daemon" allows main program to exit eventually even if these dont finish correctly
    worker.start()
    tm.sleep(1)  # staggering gdx threads shouldnt matter as long as the excel process has something to work on

