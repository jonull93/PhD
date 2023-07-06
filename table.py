import os
import pickle
import order_cap
import pandas as pd
import re
from my_utils import print_red, print_green, print_yellow, print_blue, print_cyan, print_magenta

def get_pickle_file(default_options=True):
# Ask the user which pickle file from PickleJar to load. Default option is file that was created last.
    directory = "PickleJar"
    pickle_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".pickle")]
    pickle_files.sort(key=os.path.getmtime)
    if not default_options:
        print_yellow("Choose a pickle file to load:\n")
        for i, f in enumerate(pickle_files, start=1):
            print(f"{i}: {f}")
        while True:
            choice = input(f"Enter a number between 1 and {len(pickle_files)}: ")
            if choice == "":
                choice = len(pickle_files)
                return pickle_files[choice-1]
            elif int(choice) < 1 or int(choice) > len(pickle_files):
                print_red("Invalid choice")
            else:
                choice = int(choice)
                return pickle_files[choice-1]
    else:
        #default option is to pick the latest file
        print_yellow(f"Loading {pickle_files[-1]}")
        return pickle_files[-1]

def load_pickle_file(pickle_file, default_options=True):
    # Load the pickle file
    data = pickle.load(open(os.path.relpath(pickle_file), "rb"))
    # list the scenaraios in Data and ask the user whether some should be removed
    print_yellow("The following scenarios were loaded:")
    for i, scen in enumerate(data.keys(), start=1):
        print(f"{i}: {scen}")
    if not default_options:
        scen_to_remove = []
        while True:
            choice = input(f"Enter a number between 1 and {len(data.keys())} to remove a scenario, or press enter to continue: ")
            if choice == "":
                break
            elif int(choice) < 1 or int(choice) > len(data.keys()):
                print_red("Invalid choice")
            else:
                choice = int(choice)
                scen = list(data.keys())[choice-1]
                print_yellow(f"Removing {scen} from data")
                scen_to_remove.append(scen)
        for scen in scen_to_remove:
            data.pop(scen)
    return data

def select_indicators(data, default_options=True):
    # list the indicators in Data and ask the user whether some should be removed
    default_indicators = ["stochastic_probability","cost_tot", "cost_variable", "cost_newinv", "cost_OMfix", "bio_use"]
    if not default_options:
        print_yellow("Which indicators should be included in the table? ('all' / 'item1, item2..' /'none')")
        print_yellow("[Default option (''): Total cost as well as each year's variable cost and bio use]")
        indicators = []
        while True:
            choice = input("..: ")
            print_yellow("The following indicators are used:")
            if choice == "":
                indicators = default_indicators
                break
            elif choice == "all":
                indicators = list(data[list(data.keys())[0]].keys())
                break
            elif choice == "none":
                indicators = []
                break
            else:
                try:
                    indicators = choice.replace("[", "").replace("]", "").replace(" ", "").split(",")
                    break
                except:
                    print_red("Invalid choice")
    else:
        indicators = default_indicators

    return indicators

def make_df(data, indicators, default_options=True):
    # make a dataframe from the data
    # the index should have two levels: scenario (keys from the data dictionary) and profile_year (index level name found in some indicators)
    # the columns should be the indicators
    
    def prettify_scenario_name(name,year):
        if "singleyear" not in name:
            # change labels from "base#extreme#" (where # is a number) to "#b #e"
            temp_label = f"{name.replace(year,'').replace('_tight','').replace('_1h','')}"
            if "base" in temp_label and "extreme" in temp_label:
                # remove 'base' and 'extreme' and split into a list
                parts = name.replace('base', '').replace('extreme', ' ').split()
                print_magenta(f"Renaming {name}")
                # join the parts with appropriate labels
                if "v2" in name or "_5_" in name:
                    return f'Alt. set ({parts[0]} opt.)'
                return f'Set ({parts[0]} opt.)'
            elif "iter2_3" in temp_label:
                return "Set (1 opt.)"
            elif "iter3_16start" in temp_label:
                return "Set (2 opt.)"
        else:
            return "Single year"


    scenarios = list(data.keys())
    all_dfs = {}
    for scen in scenarios:
        # check that all indicators are in the data
        for ind in indicators:
            if ind not in data[scen].keys():
                print_red(f"Indicator {ind} not found in {scen}")
        # gather the data for each indicator
        ind_data = {ind: data[scen][ind] if ind in data[scen] else None for ind in indicators}
        for ind in ind_data.keys():
            if ind in ["cost_newinv","cost_OMfix"]:
                ind_data[ind] = ind_data[ind].sum(axis=None)
        print_blue(ind_data["cost_newinv"])
        print_green(ind_data["cost_variable"])
        # find the profile_years
        profile_years = "ba"
        for ind in ind_data.keys():
            # see if profile_years is one of the index levels
            if type(ind_data[ind]) in [pd.DataFrame, pd.Series]:
                if "profile_years" in ind_data[ind].index.names:
                    # if so, make a new index level for scenario
                    profile_years = ind_data[ind].index.get_level_values("profile_years")
                elif "stochastic_scenarios" in ind_data[ind].index.names:
                    profile_years = ind_data[ind].index.get_level_values("stochastic_scenarios")
        if type(profile_years) != pd.Index and profile_years == "ba":
            print_red(f"Could not find profile_year in {scen}")
            try: print_red(ind_data["bio_use"])
            except: print_red(ind_data)
            # extract the profile_year from the scenario name
            # The exact location in the scenario name is unknown, but it is written in the form "2001to2002" or "1980to1981" and should be saved as "2001-2002" or "1980-1981"
            profile_years = re.findall(r"\d{4}to\d{4}", scen)
            profile_years = [f"{year[:4]}-{year[-4:]}" if year else '' for year in profile_years]
            print_green(f"Extracted profile_year from scenario name: {profile_years}")
        # if there are indicators that are not dataframes or series, make them into Series
        for ind in ind_data.keys():
            if type(ind_data[ind]) not in [pd.DataFrame, pd.Series]:
                ind_data[ind] = pd.Series(ind_data[ind], index=profile_years, dtype=float)
        # make a dataframe from the data
        scen_df = pd.concat(ind_data, axis=1)
        # if any of the following indicators are in the dataframe, divide them by 1000
        divide_by_1000 = ["bio_use", ]
        for ind in divide_by_1000:
            if ind in scen_df.columns:
                scen_df[ind] = scen_df[ind] / 1000
        all_dfs[scen] = scen_df
    df = pd.concat(all_dfs, axis=0, names=["scenario", "profile_year"])
    # flip the order of the multiindex levels and sort the index
    df = df.swaplevel(0, 1, axis=0).sort_index()
    # rename the scenarios using the prettify_scenario_name function
    print_yellow(df)
    new_scenario_names = [prettify_scenario_name(name,year) for year,name in df.index]
    map_dict = {old:new for old,new in zip(df.index.get_level_values("scenario"), new_scenario_names)}
    df = df.rename(index=map_dict, level="scenario")

    # Reorder the index: alphabetically for the first year, and according to the scenario_order list for the scenario level
    scenario_order = ["Single year", "Set (1 opt.)", "Set (2 opt.)", "Set (3 opt.)", "Set (4 opt.)", "Alt. set (4 opt.)"]

    # Sort the 'profile_year' level
    df.sort_index(level='profile_year', inplace=True)

    # Define scenario order as a dictionary for mapping
    scenario_order = {"Single year": 0, "Set (1 opt.)": 1, "Set (2 opt.)": 2, "Set (3 opt.)": 3, "Set (4 opt.)": 4, "Alt. set (4 opt.)": 5}

    # Reset index to work with scenario as a column
    df_reset = df.reset_index()

    # Add a 'sort_order' column based on scenario order
    df_reset['sort_order'] = df_reset['scenario'].map(scenario_order)

    # Sort by 'sort_order' and 'profile_year', and drop the 'sort_order' column
    df_reset.sort_values(['profile_year', 'sort_order'], inplace=True)
    df_reset.drop(columns='sort_order', inplace=True)

    # Set the index back to ['profile_year', 'scenario']
    df = df_reset.set_index(['profile_year', 'scenario'])

    print_magenta(df.round(3))
    return df


def write_to_excel(df, pickle_file, default_options=True):
    sheet_name = pickle_file.split("\\")[-1].split(".")[0].replace("data_results_","")
    # see if the file "results/indicator_data.xlsx" exists
    file_exists = os.path.isfile(r"results/indicator_data.xlsx")
    # check if the file is open
    file_open = False
    if file_exists:
        try:
            with open(r"results/indicator_data.xlsx", "a") as f:
                f.close()
        except PermissionError:
            print_red("Could not write to file 'results/indicator_data.xlsx' because it is open")
            file_open = True
    if file_open:
        while True:
            print_yellow("Please close the file and press enter to continue")
            choice = input("..: ")
            if choice == "":
                try:
                    with open(r"results/indicator_data.xlsx", "a") as f:
                        f.close()
                    break
                except PermissionError:
                    print_red("Could not write to file 'results/indicator_data.xlsx' because it is open")
                    file_open = True    
    # if the file does not exist, create it
    if not file_exists:
        df.to_excel(r"results/indicator_data.xlsx", sheet_name=sheet_name, engine="openpyxl")
    else:
        # if the file exists, check if the sheet exists
        with pd.ExcelFile(r"results/indicator_data.xlsx") as reader:
            sheets = reader.sheet_names
        i=2
        while True:
            if sheet_name in sheets:
                # if the sheet exists, add a number to the end of the sheet name
                sheet_name = f"{sheet_name} ({i})"
                i+=1
            else:
                break
        # write the dataframe to excel in the sheet with the name of the pickle file, preserving any existing sheets
        with pd.ExcelWriter(r"results/indicator_data.xlsx", engine="openpyxl", mode="a") as writer:
            df.to_excel(writer, sheet_name=sheet_name)
    return None

if __name__ == "__main__":
    # Ask the user if default options should be used
    print_yellow("Use default options? (y/n)")
    while True:
        choice = input("..: ")
        if choice == "y" or choice == "":
            default_options = True
            break
        elif choice == "n":
            default_options = False
            break
        else:
            print_red("Invalid choice")
    # get pickle file
    print_cyan("1. Loading pickle file")
    pickle_file = get_pickle_file(default_options)
    # load pickle file
    print_cyan("2. Loading data")
    data = load_pickle_file(pickle_file, default_options)
    # select indicators to show
    print_cyan("3. Selecting indicators")
    indicators = select_indicators(data, default_options)
    # present the data in a table
    print_cyan("4. Making dataframe")
    df = make_df(data, indicators, default_options)
    # write the dataframe to an excel file
    print_cyan("5. Writing dataframe to excel")
    write_to_excel(df, pickle_file, default_options)



"""
file_suffix = "appended"
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 3
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))
regions = ["brit", "iberia", "nordic"]
flexes = ["lowFlex"]
baseFC = "noFC"
compare = ("FC", "fullFC")#("suffix", "correct_IE_Nminus1")  # ("FC", "fullFC")
years = [2020, 2025, 2030, 2040]
indicators = {"cost_tot": [], "VRE_share_total": [], "thermal_share_total": [], "curtailment": [], "bat": [],
              "cost_flexlim": [], "FR_binding_hours": 0., "FR_hard_binding_hours": 0., "base_mid_thermal_FLHs": [],
              "peak_thermal_FLHs": [], "FR_share_ESS": [], "FR_share_thermal": [], "FR_share_hydro": [], "FR_share_VRE": [], "FR_share_PtH": []}
base_scenarios = [f"{reg}_{flex}_{baseFC}_{year}{scen_suffix}_{timestep}h" for reg in regions for flex in flexes for year in
                  years]
print_green(f"- Comparing {baseFC} to {compare[0]}:{compare[1]} -")
print(","+",".join(indicators))
for scen in base_scenarios:
    if compare[0] == "FC": compscen = scen.replace(baseFC, compare[1])
    elif compare[0] == "suffix":
        _ = scen.split("_")
        _.insert(-1, compare[1])
        compscen = "_".join(_)
    if scen not in data:
        print(scen, "was not found in data")
        continue
    if compscen not in data:
        print(compscen,"was not found in data")
        continue
    for ind in indicators:
        if "flexlim" in ind:
            indicators[ind] = [data[scen][ind].sum(), data[compscen][ind].sum()]
        elif "bat" in ind:
            try:
                indicators[ind] = [data[scen]["tot_cap"].loc[ind].sum(), data[compscen]["tot_cap"].loc[ind].sum(),
                                   data[scen]["tot_cap"].loc[ind+"_cap"].sum(),
                                   data[compscen]["tot_cap"].loc[ind+"_cap"].sum()]
            except KeyError:
                indicators[ind] = [0, 0, 0, 0]
        elif ind in ["curtailment", "VRE_share_total", "thermal_share_total"]:
            indicators[ind] = [data[scen][ind] * 100, data[compscen][ind] * 100]
        elif ind == "FR_binding_hours":
            indicators[ind] = sum([1 for i in data[compscen]["FR_cost"].sum() if i > 0.5])
        elif ind == "FR_hard_binding_hours":
            indicators[ind] = sum([1 for i in data[compscen]["FR_cost"].sum() if i > 10])
        elif "thermal_FLH" in ind:
            techs = []
            if "mid" in ind:
                techs += order_cap.midload
                techs += order_cap.CCS
                techs += order_cap.CHP
            if "base" in ind:
                techs += order_cap.baseload
            if "peak" in ind:
                techs += order_cap.peak
            noFC_techs = [tech for tech in data[scen]["tot_cap"].groupby(level=0).sum().index if tech in techs]
            fullFC_techs = [tech for tech in data[compscen]["tot_cap"].groupby(level=0).sum().index if tech in techs]
            try:
                noFC_totalgen = sum([data[scen]["gen_per_eltech"].loc[tech] for tech in noFC_techs if
                                     tech in data[scen]["gen_per_eltech"].index])
            except TypeError:
                noFC_totalgen = data[scen]["gen_per_eltech"].loc[noFC_techs[0]]
            noFC_totalcap = sum([data[scen]["tot_cap"].groupby(level=0).sum().loc[tech] for tech in noFC_techs])
            fullFC_totalgen = sum(
                [data[compscen]["gen_per_eltech"].loc[tech] for tech in fullFC_techs if
                 tech in data[compscen]["gen_per_eltech"].index])
            fullFC_totalcap = sum(
                [data[compscen]["tot_cap"].groupby(level=0).sum().loc[tech] for tech in fullFC_techs])

            try:
                indicators[ind] = [round(noFC_totalgen / noFC_totalcap), round(fullFC_totalgen / fullFC_totalcap)]
            except ZeroDivisionError:
                print_red(scen, techs, noFC_totalcap, fullFC_totalcap, )
                print(noFC_techs, data[scen]["gen_per_eltech"].index)
                print_red(data[scen]["tot_cap"].groupby(level=0).sum())
                print_red(data[compscen]["tot_cap"].groupby(level=0).sum())
                raise
        elif "FR_share" in ind:
            indicators[ind] = [round(data[scen][ind]*100), round(data[compscen][ind]*100)]
        else:
            indicators[ind] = [data[scen][ind], data[compscen][ind]]
    # print(colored(scen, "cyan"))
    to_print = [f"{scen.replace('_noFC', '').replace(scen_suffix, '')}"]
    for ind, val in indicators.items():
        if "bat" in ind:
            to_print.append(
                f"{round(val[0], 2)} / {round(val[2], 2)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 2)} / {'+' if val[3] - val[2] >= 0 else ''}{round(val[3] - val[2], 2)})")
        elif ind in ["curtailment", "VRE_share_total", "thermal_share_total"]:
            to_print.append(f"{round(val[0], 1)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 1)})")
        elif ind in ["FR_binding_hours", "FR_hard_binding_hours"]:
            to_print.append(f"{val*timestep}")
        else:
            to_print.append(f"{round(val[0], 2)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 2)})")
    print(",".join(to_print))

for scen in base_scenarios:
    comp_scen = scen.replace(baseFC, compare[1])
    try: bat = data[comp_scen]["tot_cap"]["bat_PS"].sum()
    except KeyError: bat = 0
    try: bat_cap = data[comp_scen]["tot_cap"]["bat_cap_PS"].sum()
    except KeyError: bat_cap = 0
    print(f"0 / 0 (+{round(bat, 2)} / +{round(bat_cap, 2)})")
# data["iberia_lowFlex_fullFC_slimSpain_2025_3h"]["gen_per_eltech"]
"""
