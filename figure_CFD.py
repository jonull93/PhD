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


def fast_cfd(df_netload, minval, maxval, amp_length=0.1):
    df_freq = pd.DataFrame()
    output = {}
    dfrows = df_netload.index
    #print("index = ", dfrows)
    net_loads_array = np.array(df_netload["net load"].values)
    #print("vals = ", net_loads_array)
    #print("len of vals = ", len(net_loads_array))
    amps = np.arange(minval, maxval, amp_length).tolist()
    #print("length of amps:", len(amps))
    start_time = timer()
    for amp in amps:
        # initiate variables before row loop
        d = {'net load': net_load, 'count1': 0, 'count2': 0}
        df_netload = pd.DataFrame(data=d)
        previous_row = dfrows[0]
        previous_net_load_val = net_loads_array[0]
        amp_positive = amp >= 0
        amp_negative = not amp_positive
        for i_r, row in enumerate(dfrows):
            # net_load_val = df_netload.at[row,'net load']
            net_load_val = net_loads_array[i_r]
            netload_greater_than_amp = net_load_val >= amp
            netload_smaller_than_amp = not netload_greater_than_amp
            previous_netload_greater_than_amp = previous_net_load_val >= amp
            previous_netload_smaller_than_amp = not previous_netload_greater_than_amp
            # both count1 and count2 are related to the duration of events
            if amp_positive and netload_greater_than_amp:
                #            df_netload.set_value(row, 'count1', df_netload.at[previous_row,'count1']+1)
                try:
                    df_netload.at[row, 'count1'] = df_netload.at[previous_row, 'count1'] + 1
                except KeyError as e:
                    print(row, amp)
                    print(df_netload.at[row, 'count1'])
                    print(df_netload.at[previous_row, 'count1'])
                    raise e
            elif amp_negative and netload_smaller_than_amp:
                #            df_netload.set_value(row, 'count1', df_netload.at[previous_row,'count1']+1)
                try:
                    df_netload.at[row, 'count1'] = df_netload.at[previous_row, 'count1'] + 1
                except KeyError as e:
                    print(row, amp)
                    print(df_netload.at[row, 'count1'])
                    print(df_netload.at[previous_row, 'count1'])
                    raise e
            # spara sedan varje periods längd vid sluttillfället
            if amp_positive and previous_netload_greater_than_amp and netload_smaller_than_amp:
                #            df_netload.set_value(previous_row, 'count2', df_netload.at[previous_row,'count1'])
                df_netload.at[previous_row, 'count2'] = df_netload.at[previous_row, 'count1']
            elif amp_negative and previous_netload_smaller_than_amp and netload_greater_than_amp:
                #            df_netload.set_value(previous_row, 'count2', df_netload.at[previous_row,'count1'])
                df_netload.at[previous_row, 'count2'] = df_netload.at[previous_row, 'count1']
            previous_row = row
            previous_net_load_val = net_load_val
        # this sets the recurrence by counting the durations for each amplitude
        s = df_netload.count2.value_counts()
        df_freq = pd.DataFrame(data=s)
        #    s_form=list(s)
        output[amp] = df_freq
    # df_out=pd.DataFrame(data=output, index=[amp])
    # df_out = pd.DataFrame()
    print(f"time to build df_freq for all amps = {round(timer() - start_time, 1)}")
    start_time = timer()
    df_out_tot = pd.DataFrame()
    # output2 = {}
    for amp in amps:
        df_out = output[amp]
        df_out = df_out.iloc[1:]
        df_out.index.name = 'Duration'
        df_out = pd.concat([df_out], keys=[amp], names=['Amplitude'])
        df_out.rename(columns={'count2': 'Occurences'}, inplace=True)
        df_out_tot = df_out_tot.append(df_out)
    #    output2[amp] = df_out
    # df_out[0]
    print(f"time to build df_out_tot = {round(timer() - start_time, 1)}")
    return df_out_tot


year = "1980-2019"  # 1981
amp_length = 1
rolling_hours = 12
years = range(1980, 2020)
years_iter = [f"{years[0]}-{years[-1]}"] + list(years)
minval = maxval = 0
for year in years_iter:
    print_cyan(f"\nStarting loop for year -- {year} --")
    pickle_read_name = ""
    pickle_dump_name = rf"PickleJar\1980-2019_CFD_netload_df_amp{amp_length}.pickle"
    data = pickle.load(open(f"PickleJar\\netload_components_{year}.pickle", "rb"))
    VRE_profiles = data["VRE_profiles"]
    load = data["load"]
    cap = data["cap"]

    if type(load) == dict:
        load_list = []
        for year, load in load.items():
            load_list += list(load)
        load = np.array(load_list)
    if load.ndim > 1:
        load = load.sum(axis=1)

    net_load = -(VRE_profiles * cap).sum(axis=1) + load
    #print(VRE_profiles.shape, net_load.shape, cap.shape)

    # d = {'net load': net_load,'count1':0,'count2':0}
    # df_netload = fast_rolling_average(pd.DataFrame(data=d),1)
    array_netload = fast_rolling_average(net_load, rolling_hours)
    df_netload = pd.DataFrame(data={'net load': array_netload, 'count1': 0, 'count2': 0})
    # maxind, maxval = max(net_load, key=lambda item: item[1])
    maxval = max(maxval,int(math.ceil(df_netload["net load"].max())))
    minval = max(minval,int(math.floor(df_netload["net load"].min())))
    #print(df_netload, minval, maxval)

    # df_netload is a pandas dataframe with multiindex and 3 columns
    # i want to collapse the multiindex and replace it with just a number range
    # df_netload = df_netload.reset_index()[["net load", "count1", "count2"]]
    # df_netload.at[2632,"count1"]

    if pickle_read_name:
        df_out_tot = pickle.load(open(pickle_read_name, "rb"))
    else:
        start_time = timer()
        df_out_tot = fast_cfd(df_netload, minval, maxval, amp_length=amp_length)
        # 248s at 1 year then more changes and now 156-157s at 1 year
        end_time = timer()
        print(f"elapsed time = {round(end_time - start_time, 1)}")
    #print(df_out_tot)

    if pickle_dump_name: pickle.dump(df_out_tot, open(pickle_dump_name, 'wb'))

    df_reset = df_out_tot.reset_index()
    df_reset.columns = ['Amplitude', 'Duration', 'Occurrence']
    df_pivot = df_reset.pivot('Amplitude', 'Duration')
    filtered_df = df_reset[df_reset['Amplitude'].round(1) == 25.5]
    #print("Filtered df =", filtered_df)
    # df_reset["Energy"] = df_reset["Amplitude"]*df_reset["Duration"]*np.sign(df_reset["Amplitude"])
    # unique_amps, unique_amps_index = np.unique(df_reset["Amplitude"],return_index=True)
    # print(df_pivot[df_pivot.columns[df_pivot.columns.get_level_values(1) > 375]].to_string())
    # print(df_pivot[df_pivot.columns[df_pivot.columns.get_level_values(1) > 1300]].fillna(0)[df_pivot != 0])
    # print(df_pivot[df_pivot["Duration"] >1300].fillna(0).sum())
    Y = df_pivot.columns.levels[1].values
    X = df_pivot.index.values
    Z = df_pivot.values
    print_cyan("Y =", Y, Y.shape)
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

    # plt.contourf(Xnetload, Ynetload, Znetload, alpha=0.7, cmap=plt.cm.jet,antialiased=False)
    # plt.savefig(f"figures\\cfd_{year}_fastfunc.png",dpi=800)

    # import matplotlib as mpl
    # mpl.rcParams["patch.force_edgecolor"]=True
    plt.pcolormesh(Xnetload, Ynetload, Znetload, alpha=1, linewidth=0, shading='nearest',
                   cmap=plt.cm.jet)  # , alpha=0.7)
    plt.savefig(f"figures\\profile_analysis\\cfd_{year}_amp{amp_length}_window{rolling_hours}.png", dpi=300)
