import os
import pickle
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from timeit import default_timer as timer
from my_utils import print_red, print_cyan, print_green, fast_rolling_average

"""
Inputs:
df of net load

Outputs:
CFD plot and VRE event df for fingerprint matching
"""


def sign(num):
    if num==0: return 1
    return np.sign(num)


def fast_cfd(df_netload, xmin, xmax, amp_length=0.1, area_method=False):
    df_freq = pd.DataFrame()
    output = {}
    hours = df_netload.index
    # print("index = ", hours)
    net_loads_array = np.array(df_netload["net load"].values)
    # print("vals = ", net_loads_array)
    # print("len of vals = ", len(net_loads_array))
    amps = np.arange(xmin, xmax, amp_length).tolist()
    # print("length of amps:", len(amps))
    start_time = timer()
    for amp in amps:
        # initiate variables before hour loop
        d = {'net load': net_load, 'count1': 0, 'count2': 0}
        df_netload = pd.DataFrame(data=d)
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
        #    s_form=list(s)
        output[amp] = df_freq
    #print(output[10].to_string())
    if area_method and False:
        for amp in amps:  # smidge and add all edges towards the vertical middle
            my_range = range(0, amp, amp_length*sign(amp))
            for amp2 in my_range:
                output[amp2] = output[amp2].add(output[amp], fill_value=0)
        for amp in amps:  # smidge and add all areas downwards
            None
    #print(output[10].to_string())

    # df_out=pd.DataFrame(data=output, index=[amp])
    # df_out = pd.DataFrame()
    print(f"time to build df_freq for all amps = {round(timer() - start_time, 1)}")
    start_time = timer()
    df_out_tot = pd.DataFrame()
    for amp in amps:
        df_out = output[amp]
        df_out = df_out.iloc[1:]
        df_out.index.name = 'Duration'
        df_out = pd.concat([df_out], keys=[amp], names=['Amplitude'])
        df_out.rename(columns={'count2': 'Occurences'}, inplace=True)
        df_out_tot = df_out_tot.append(df_out)
    print(f"time to build df_out_tot = {round(timer() - start_time, 1)}")
    if area_method:
        start_time = timer()
        print_red(df_out_tot.index.get_level_values(0).unique())
        # df_out_tot hold a single column and a few multiindexed rows
        # please make this code more efficient
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
        print(f"time to remake lines into areas = {round(timer() - start_time, 1)}")

        """for amp in amps:
            df_out = output[amp]
            df_out = df_out.iloc[1:]
            df_out.index.name = 'Duration'
            df_out = pd.concat([df_out], keys=[amp], names=['Amplitude'])
            df_out.rename(columns={'count2': 'Occurences'}, inplace=True)
            df_out_tot = df_out_tot.append(df_out)
        print(f"time to build df_out_tot = {round(timer() - start_time, 1)}")
        start_time = timer()
        if area_method:
            df_out_tot = df_out_tot.groupby(level=0).apply(lambda x: x.reindex(range(0, x.index.max() + 1), fill_value=0).sort_index(ascending=False))
            df_out_tot['Occurences'] = df_out_tot.groupby(level=0).apply(lambda x: x['Occurences'].cumsum())
            print(f"time to remake lines into areas = {round(timer() - start_time, 1)}")"""
    return df_out_tot


#year = "1980-2019"  # 1981
amp_length = 5
rolling_hours = 12
test_mode = True
write_pickle = not test_mode
area_mode_in_cfd = True
read_pickle = False
years = range(1980, 2020)
years_iter = [f"{years[0]}-{years[-1]}"] * (len(years) is 40) + list(years)
years_iter2 = [f"{years[0]}-{years[-1]}"] + [f"{years[i]}-{years[i+1]}" for i in range(len(years)-1)]
#years_iter = [f"1980-2019"]
xmin = xmax = ymin = ymax = 0
for year in range(1980,1981):
    print_cyan(f"\nStarting loop for year -- {year} --")
    pickle_read_name = rf"PickleJar\{year}_CFD_netload_df_amp{amp_length}{'_area'*area_mode_in_cfd}.pickle"
    pickle_dump_name = rf"PickleJar\{year}_CFD_netload_df_amp{amp_length}{'_area'*area_mode_in_cfd}.pickle"

    # df_netload = df_netload.reset_index()[["net load", "count1", "count2"]]
    try:
        if not read_pickle: raise ImportError
        df_out_tot = pickle.load(open(pickle_read_name, "rb"))
    except Exception as e:
        print_red(f"Failed to read {pickle_read_name} due to {type(e)}")
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
        print(f"elapsed time = {round(end_time - start_time, 1)}")
        if pickle_dump_name: pickle.dump(df_out_tot, open(pickle_dump_name, 'wb'))
    print(df_out_tot.iloc[:40])
    #print(df_out_tot)
    df_reset = df_out_tot.reset_index()
    df_reset.columns = ['Amplitude', 'Duration', 'Occurrence']
    xmax = max(xmax, int(math.ceil(df_reset["Amplitude"].max())))
    xmin = min(xmin, int(math.floor(df_reset["Amplitude"].min())))
    df_pivot = df_reset.pivot('Amplitude', 'Duration')
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
    print_red("Z =", Z)
    Znetload = np.where(Z > 50, 50, Z)
    Ynetload, Xnetload = np.meshgrid(Y, X)
    import scipy.io

    scipy.io.savemat(f"output\\heatmap_values_{year}",
                     {"amplitude": Ynetload, "duration": Xnetload, "recurrance": Znetload})
    # print({"amplitude":Xnetload, "duration":Ynetload, "recurrance":Znetload})
    #Z_testing = np.nan_to_num(Znetload)
    #print(Z_testing.sum(axis=0), Z_testing.sum(axis=0).shape)
    # import matplotlib as mpl
    # mpl.rcParams["patch.force_edgecolor"]=True
    plt.clf()
    plt.pcolormesh(Xnetload, Ynetload, Znetload, alpha=1, linewidth=0, shading='nearest',
                   cmap=plt.cm.jet)  # , alpha=0.7)
    plt.xlim([xmin, xmax])
    plt.ylim([ymin, ymax])
    from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
    ax = plt.gca()
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    plt.grid(visible=True, color="black", lw=1, axis="both", alpha=0.15, which="both")
    plt.xlabel("Amplitude [GW]")
    plt.ylabel("Duration [days]")
    plt.title(f"Amplitude-Duration-Recurrence for {year}")
    plt.tight_layout()
    plt.savefig(f"figures\\profile_analysis\\cfd_{year}_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.png", dpi=500)
    plt.show()
