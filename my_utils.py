import datetime as dt
import itertools
import os
import string
from enum import Enum

import numpy as np
import pandas

from order_cap import order_cap
from order_gen import order_gen

os.system('color')

class TECH(str, Enum):
    ELECTROLYZER = 'efuel'
    NUCLEAR = 'U'
    LIGNITE = 'B'
    COAL = 'H'
    BIOMASS = 'W'
    LIGNITE_CCS = 'BCCS'
    COAL_CCS = 'HCCS'
    GAS_CCS = 'GCCS'
    LIGNITE_BIOMASS_CCS = 'BWCCS'
    BIOMASS_CCS = 'BECCS'
    COAL_BIOMASS_CCS = 'HWCCS'
    COAL_CCS_FLEXIBLE = 'HCCS_flex'
    LIGNITE_BIOMASS_CCS_FLEXIBLE = 'HWCCS_flex'
    BIOGAS_CCS = 'WGCCS'
    GAS_BIOGAS_CCS = 'GWGCCS'
    GAS = 'G'
    BIOGAS = 'WG'
    BIOGAS_PEAK = 'WG_peak'
    GAS_PEAK = 'G_peak'
    FUEL_CELL = 'FC'
    HYDRO = 'RO'
    HYDRO_IMPORT = 'RO_imp'
    WIND_OFFSHORE_1 = 'WOFF1'
    WIND_OFFSHORE_2 = 'WOFF2'
    WIND_OFFSHORE_3 = 'WOFF3'
    WIND_OFFSHORE_4 = 'WOFF4'
    WIND_OFFSHORE_5 = 'WOFF5'
    WIND_ONSHORE_12 = 'WON12'
    WIND_ONSHORE_11 = 'WON11'
    WIND_ONSHORE_10 = 'WON10'
    WIND_ONSHORE_9 = 'WON9'
    WIND_ONSHORE_8 = 'WON8'
    WIND_ONSHORE_7 = 'WON7'
    WIND_ONSHORE_6 = 'WON6'
    WIND_ONSHORE_5 = 'WONA5'
    WIND_ONSHORE_4 = 'WONA4'
    WIND_ONSHORE_3 = 'WONA3'
    WIND_ONSHORE_2 = 'WONA2'
    WIND_ONSHORE_1 = 'WONA1'
    SOLAR_OPT = 'PV_cSiOPT'
    SOLAR_TRACKING = 'PV_cSiTWO'
    PV_A1 = 'PVPA1'
    PV_A2 = 'PVPA2'
    PV_A3 = 'PVPA3'
    PV_A4 = 'PVPA4'
    PV_A5 = 'PVPA5'
    PV_R1 = 'PVR1'
    PV_R2 = 'PVR2'
    PV_R3 = 'PVR3'
    PV_R4 = 'PVR4'
    PV_R5 = 'PVR5'
    BATTERY = 'bat'
    BATTERY_CAP = 'bat_cap'
    FLYWHEEL = 'flywheel'
    SYNCHRONOUS_CONDENSER = 'sync_cond'
    H2_STORAGE = 'H2store'
    ELECTRIC_BOILER = 'EB'
    HEAT_PUMP = 'HP'


thermals = [
    "B",
    "H",
    "G",
    "G_peak",
    "W",
    "U",
    "BCCS",
    "HCCS",
    "GCCS",
    "BECCS",
    "WG",
    "WG_peak",
    "WGCCS",
    "B_CHP",
    "H_CHP",
    "W_CHP",
    "G_CHP",
    "WG_CHP",
    "WA_CHP"
]

order_map_cap = {j: i for i, j in enumerate(order_cap)}
order_map_gen = {j: i for i, j in enumerate(order_gen)}
tech_names = {'RO': 'Hydro', 'RR': 'Run-of-river', 'U': 'Nuclear', "b": "Lignite ST",
              'CHP_wa': 'Waste CHP', 'CHP_bio': 'Woodchip CHP', "G_CHP": "N. Gas CHP", "W_CHP": "Biomass CHP",
              "WA_CHP": "Waste CHP", "B_CHP": "Lignite CCS", "H_CHP": "Coal CHP", "WG_CHP": "Biogas CHP",
              'GWGCCS': 'Gas-mix CCS', "BCCS": "Lignite CCS", "HCCS": "Coal CCS", "GCCS": "N. Gas CCS",
              "BWCCS": "Lignite-biomass mix CCS", "BECCS": "Biomass CCS", "HWCCS": "Coal-biomass mix CCS",
              "WGCCS": "Biogas CCS",  "Bat. storage": "Bat. storage",
              "bat_discharge": "Battery (dis)charge", 'WOFF': 'Offshore wind', 'WON': 'Onshore wind',
              'WG': 'Biogas CCGT', 'WG_peak': 'Biogas GT', 'wind_offshore': 'Offshore wind',
              "flywheel": "Flywheel", "bat": "Bat. storage", "sync_cond": "Sync. Cond.",
              'wind_onshore': 'Onshore wind', 'PV_cSiOPT': 'Solar PV', 'EB': 'EB', 'HP': 'HP', 'HOB_WG': 'Biogas HOB',
              'HOB_bio': 'Woodchip HOB', 'solarheat': 'Solar heating', "curtailment": "Curtailment",
              'Load': 'Load', 'bat_PS': "Battery (PS)", 'bat_cap_PS': "Battery cap (PS)", 'bat_cap': "Bat. power",
              "electrolyser": "Electrolyser", "H": "Coal ST", "W": "Biomass ST",
              "G": "N. Gas CCGT", "G_peak": "N. Gas GT", "PV": "Solar PV", "FC": "Fuel cell",
              "H2store": "H2 storage", "PtH":"Power-to-Heat", "thermals":"Thermal power", "Hydro":"Hydro power",
              "biogas": "Biogas", "Export south": "Exp. south", "Export north": "Exp. north",
              }
scen_names = {"_pre": "Base case", "_leanOR": "Lean OR", "_OR": "OR", "_OR_fixed": "OR", "_OR_inertia": "OR + Inertia",
              "_OR+inertia_fixed": "OR + Inertia", "_inertia": "Inertia", "_inertia_2x": "2x Inertia",
              "_inertia_noSyn": "Inertia (noSyn)", "_OR_inertia_3xCost": "OR + Inertia (3x)",
              "_inertia_3xCost": "Inertia (3x)", "_inertia_noSyn_3xCost": "Inertia (noSyn) (3x)", "noFC": "No FC",
              "fullFC": "Full FC", "OR": "FR", "inertia": "Inertia", "lowFlex":"LowFlex", "highFlex":"HighFlex"}
color_dict = {'B_CHP': "#23343A", 'Base': '#2b2d42', 'Bat. In': "#8d5eb7", 'Bat. Out': "#8d5eb7",
              'bat': "#714b92", 'bat_PS': "xkcd:deep lavender", 'bat_cap': "#8d5eb7",
              'bat_cap_PS': "xkcd:deep lavender", 'bat_discharge': "xkcd:amber", 'BECCS': "#5b9aa0",
              'Bio thermals': "#2a9d8f", 'b': "#172226", 'CHP': "#5BB0F6",
              'CHP_WG': (0, 176 / 255, 80 / 255), 'CHP_WG_L': 'xkcd:mid green', 'CHP_bio': 'xkcd:tree green',
              'curtailment': "xkcd:slate", 'EB': "#E85D04", 'electrolyser': "#68032e", 'FC': "#c65082",
              'Fossil thermals': "#2b2d42", 'G': "#5B90F6", 'G_CHP': "#5BB0F6", 'G_peak': "#7209b7",
              'GWGCCS': 'xkcd:dark peach', 'H': "#172226", 'H2store': "#ad054d",
              'HOB_WG': (128 / 255, 128 / 255, 0), 'HOB_bio': 'green', 'H_CHP': "#172618", 'HP': "#F48C06",
              'Hydro': 'xkcd:ocean blue', 'Load': 'Black', 'offset': "white", "Other thermals": "Peru",
              'Peak': "crimson", 'PV': 'xkcd:mustard', 'PtH': "#59A5B1", 'RO': 'xkcd:ocean blue', 'RR': 'xkcd:ocean blue',
              'solarheat': (204 / 255, 51 / 255, 0), 'sync_cond': 'xkcd:aqua', 'Thermals': "#5BB0F6", 'U': 'mediumturquoise',
              'WA_CHP': 'xkcd:deep lavender', 'W': "#014421", 'WOFF': '#DADADA', 'WON': '#B9B9B9',
              'Wind': '#B9B9B9', 'wind_offshore': '#DADADA', 'wind_onshore': '#B9B9B9', 'WG': '#a4be20',
              'WG_CHP': "#83981a", 'WG_peak': '#d00000', 'W_CHP': "#016421"}

# Additional entries for clarity and consistency
color_dict["Battery"] = color_dict["bat"]
color_dict["Bat. storage"] = color_dict["bat"]
color_dict["Bat."] = color_dict["bat"]
color_dict["Bat. power"] = color_dict["bat_cap"]

color_dict["Solar PV"] = color_dict["PV"]
color_dict["PV_cSiOPT"] = color_dict["PV"]

color_dict["Hydro power"] = color_dict["Hydro"]
color_dict["Baseload"] = color_dict["Base"]
color_dict["Nulear"] = color_dict["U"]
# If a value from tech_names is in color_dict, add the value from tech_names to color_dict with the same color
for key, value in tech_names.items():
    if key in color_dict:
        color_dict[value] = color_dict[key]


EPODreg_to_country = {  # dictionary for going between EPODreg to country
    'AT': 'Austria', 'BE': 'Belgium', 'BO': 'Bosnia', 'BG': 'Bulgaria', 'CR': 'Croatia', 'CY': 'Cyprus',
    'CZ': 'Czech_Republic', 'DK1': 'Denmark', 'DK2': 'Denmark', 'EE': 'Estonia', 'FI': 'Finland', 'FR1': 'France',
    'FR2': 'France', 'FR3': 'France', 'FR4': 'France', 'FR5': 'France', 'DE1': 'Germany', 'DE2': 'Germany',
    'DE3': 'Germany', 'DE4': 'Germany', 'DE5': 'Germany', 'GR': 'Greece', 'HU': 'Hungary', 'IS': 'Iceland',
    'IE': 'Ireland', 'IT1': 'Italy', 'IT2': 'Italy', 'IT3': 'Italy', 'LV': 'Latvia', 'LT': 'Lithuania',
    'LU': 'Luxembourg', 'MC': 'Macedonia', 'MT': 'Malta', 'NL': 'Netherlands', 'NO_S': 'Norway', 'NO_N': 'Norway',
    'NO1': 'Norway', 'NO2': 'Norway', 'NO3': 'Norway', 'PO1': 'Poland', 'PO2': 'Poland', 'PO3': 'Poland',
    'PT': 'Portugal', 'RO': 'Romania', 'SK': 'Slovakia', 'SI': 'Slovenia', 'ES_N': 'Spain', 'ES_S': 'Spain',
    'ES1': 'Spain', 'ES2': 'Spain', 'ES3': 'Spain', 'ES4': 'Spain', 'SE_N': 'Sweden', 'SE_S': 'Sweden', 'SE1': 'Sweden',
    'SE2': 'Sweden', 'SE3': 'Sweden', 'SE4': 'Sweden', 'CH': 'Switzerland', 'UK1': 'UK', 'UK2': 'UK', 'UK3': 'UK'
}
EPODs = list(EPODreg_to_country.keys())

scenario_shortening = {"iberia": "IB", "brit": "BR", "nordic": "NE",
                       "CO2price": "CO2p", "fullFC": "FC", }
regions_corrected = {"brit": "Brit", "nordic": "Nordic+", "iberia": "Iberia"}
year_names = {2020: "ref. 2020", 2025: "near-term", 2030: "mid-term", 2040: "long-term"}
year_names_twolines = {2020: "ref.\nyear", 2025: "near-\nterm", 2030: "mid-\nterm", 2040: "long-\nterm"}

def country_to_reg(dictionary, country):
    """

    Parameters
    ----------
    dictionary
    country

    Returns
    -------
    takes a dictionary with reg keys, and a country key, then uses EPODreg_to_country to return a dictionary with only
    the keys that correspond to that country
    """
    return {reg: dictionary[reg] for reg in dictionary if country in EPODreg_to_country[reg]}


def label_axes(fig, labels=None, loc=None, **kwargs):
    """
    Walks through axes and labels each.

    kwargs are collected and passed to `annotate`

    Parameters
    ----------
    fig : Figure
         Figure object to work on

    labels : iterable or None
        iterable of strings to use to label the axes.
        If None, lower case letters are used.

    loc : len=2 tuple of floats
        Where to put the label in axes-fraction units
    """
    if labels is None:
        labels = string.ascii_lowercase

    # re-use labels rather than stop labeling
    labels = itertools.cycle(labels)
    if loc is None:
        loc = (.9, .9)
    for ax, lab in zip(fig.axes, labels):
        ax.annotate(lab, xy=loc,
                    xycoords='axes fraction',
                    **kwargs)


def write_inc(path, filename, data: dict, flip=True, fliplast=False, comment=False):
    """

    Parameters
    ----------
    path
    filename
    data
    flip

    Returns
    -------
    nothing, but creates path/filename.inc containing a variable with 2 or 3 sets, e.g. tech + reg (+ opt. timestep)
    """
    with open(path + filename, "w") as writer:
        if comment:
           writer.write(f"* ---\n")
           if type(comment) == list:
               for c in comment: writer.write(f"* {c}\n")
           else:
               writer.write(f"* ---\n* {comment}\n* ---")
           writer.write(f"* ---\n")
        if type(data) not in [list, dict]:
            print("! Wrong data type given to write_inc()")
            return
        elif type(data)==list:
            for i, val in enumerate(data):
                writer.write(f"{'h' + str(i + 1).zfill(4)}  {val}\n")
        for key1, val1 in data.items():
            if type(val1) == dict:  # key1: {..}
                for key2, val2 in val1.items():
                    if type(val2) == dict:  # key1: {key2: {}}
                        for key3, val3 in val2.items():
                            if type(val3) == dict:  # key1: {key2: {key3: {}}}
                                for key4, val4 in val3.items():
                                    if flip:
                                        if fliplast:
                                            writer.write(f"{key2:4} . {key1:6} . {key4:6} . {key3:6} {val4}\n")
                                        else:
                                            writer.write(f"{key2:4} . {key1:6} . {key3:6} . {key4:6} {val4}\n")
                                    else:
                                        writer.write(f"{key1:4} . {key2:6} . {key3:6} . {key4:6} {val4}\n")
                            elif type(val3) == list:  # key1: {key2: {key3: [values]}}
                                for i, val4 in enumerate(val3):
                                    writer.write(f"{key1:4} . {key2:4} . {key3:4} . {'h' + str(i + 1).zfill(4)}  {val4}\n")
                            else:  # key1: {key2: {key3:val3}}
                                if flip:
                                    writer.write(f"{key2:4} . {key1:6} . {key3:4}  {val3}\n")
                                else:
                                    writer.write(f"{key1:4} . {key2:6} . {key3:4}  {val3}\n")
                    elif type(val2) == list:  # key1: {key2: [values]}
                            for i, val3 in enumerate(val2):
                                writer.write(f"{key1:4} . {key2:4} . {'h' + str(i + 1).zfill(4)}  {val3}\n")
                    else:  # key1: {key2:val2}
                        if flip:
                            writer.write(f"{key2:4} . {key1:6} {val2}\n")
                        else:
                            writer.write(f"{key1:4} . {key2:6} {val2}\n")
            elif type(val1) == list:   # key1: [values]
                for i, val2 in enumerate(val1):
                    writer.write(f"{key1:4} . {'h' + str(i + 1).zfill(4)}  {val2}\n")
                    if val1 == "":
                        writer.write(f"{'h' + str(i + 1).zfill(4)}  {val2}\n")
            else:  # key1: val1
                writer.write(f"{key1:6} {val1}\n")
    return None


def write_inc_from_df_columns(path, filename, df: pandas.DataFrame, comment=False, first_day=1):
    """

    Parameters
    ----------
    path
    filename
    df, where index layers are the parameter sets, and the only column is the values
    comment, text to be put in the top of the inc file (commented out with *..)

    Returns
    -------
    nothing, but creates path/filename.inc
    """
    try:
        os.mkdir(path)
    except:
        None
    if "timestep" in df.index.names and first_day > 1:
        if df.index.get_level_values(level="timestep")[0] in ["d001a", "h0001"]:
            import re
            def shift_time_index(df, start_hour):
                # Identify the index level containing the desired values
                target_level = None
                for level, name in enumerate(df.index.names):
                    if any(re.match(r'(h|d)\d+', value) for value in df.index.get_level_values(name)):
                        target_level = level
                        break
                if target_level is None:
                    print("No matching index level found.")
                    return df
                # Modify the index level with the given start_hour
                def update_time_index(value):
                    prefix, num = value[0], int(value[1:])
                    new_num = (num + start_hour - 1) % len(df) + 1
                    return f'{prefix}{new_num:04d}'
                new_index_level = df.index.get_level_values(target_level).map(update_time_index)
                new_index = df.index.set_levels(new_index_level, level=target_level)
                # Set the modified index back to the DataFrame
                df.index = new_index
            shift_time_index(df, (first_day-1)*24)
        else:
            print("First day is not 1, but the first timestep index is not 'd001a' or 'h0001'.")

    with open(path + filename, "w") as writer:
        if comment:
           writer.write(f"* ---\n")
           if type(comment) == list:
               for c in comment: writer.write(f"* {c}\n")
           else:
               writer.write(f"* ---\n* {comment}\n* ---")
           writer.write(f"* ---\n")
        #dim = len(df.columns)
        for index, value in df.iterrows():
            if type(index) == tuple:
                line = " . ".join(index) + f"  {value[0]}\n"
            else:
                value = [str(i) for i in value[:-1]] + [value[-1]]
                line = " . ".join(value[:-1]) + f"  {value[-1]}\n"
            writer.write(line)
    return None


def append_to_file(filename, scenario, time_to_solve):
    "adds 'to_add' to a new line at the bottom of originalfile"
    to_add = f"{dt.datetime.now().strftime('%D - %H:%M:%S')} : {scenario:<40} : " \
             f"{time_to_solve} min\n"
    with open(filename + ".txt", 'a') as f2:
        f2.write(to_add)


def add_in_dict(d, key, val, group_vre=False, tech_position=0):
    is_touple = type(key) == tuple
    if is_touple:
        tech = key[tech_position]
    else:
        tech = key
    if group_vre:  # group WONA1, WONA2, ... to "WON"
        if "WON" in tech:
            tech = "WON"
        elif "PV" in tech:
            tech = "PV"
        if is_touple:
            key = (tech, key[1])
        else:
            key = tech

    if key in d:
        d[key] += val
    else:
        d[key] = val


def crawl_resource_usage(timer=5):
    import time
    import psutil
    from termcolor import colored
    print(f"Resource usage crawler started. Will print memory and CPU usage (%) every {timer} minutes.")
    while True:
        color = "red" if psutil.virtual_memory().percent > 80 or psutil.cpu_percent(2) > 80 else "white"
        print(colored(
            f"~~ Resource crawler, {dt.datetime.now().strftime('%H:%M:%S')} ~~, RAM: {psutil.virtual_memory().percent} %, CPU: {psutil.cpu_percent(2)} %",
            color))
        time.sleep(timer * 60)


def print_red(to_print, *argv, replace_this_line=False, **kwargs):
    from termcolor import colored
    if type(to_print) != str:
        to_print = str(to_print)
    if len(argv) > 0:
        for arg in argv:
            to_print += "\n"+str(arg)
    if replace_this_line:
        end = '\r'
    else:
        end = kwargs.pop('end', '\n')
    print(colored(to_print, "red"), end=end, **kwargs)


def print_green(to_print, *argv, replace_this_line=False, **kwargs):
    from termcolor import colored
    if type(to_print) != str:
        to_print = str(to_print)
    if len(argv) > 0:
        for arg in argv:
            to_print += " "+str(arg)
    if replace_this_line:
        end = '\r'
    else:
        end = kwargs.pop('end', '\n')
    print(colored(to_print, "green"), end=end, **kwargs)


def print_cyan(to_print, *argv, replace_this_line=False, **kwargs):
    from termcolor import colored
    if type(to_print) != str:
        to_print = str(to_print)
    if len(argv) > 0:
        for arg in argv:
            to_print += " "+str(arg)
    if replace_this_line:
        end = '\r'
    else:
        end = kwargs.pop('end', '\n')
    print(colored(to_print, "cyan"), end=end, **kwargs)


def print_yellow(to_print, *argv, replace_this_line=False, **kwargs):
    from termcolor import colored
    if type(to_print) != str:
        to_print = str(to_print)
    if len(argv) > 0:
        for arg in argv:
            to_print += " "+str(arg)
    if replace_this_line:
        end = '\r'
    else:
        end = kwargs.pop('end', '\n')
    print(colored(to_print, "yellow"), end=end, **kwargs)


def print_blue(to_print, *argv, replace_this_line=False, **kwargs):
    from termcolor import colored
    if type(to_print) != str:
        to_print = str(to_print)
    if len(argv) > 0:
        for arg in argv:
            to_print += " "+str(arg)
    if replace_this_line:
        end = '\r'
    else:
        end = kwargs.pop('end', '\n')
    print(colored(to_print, "blue"), end=end, **kwargs)


def print_magenta(to_print, *argv, replace_this_line=False, **kwargs):
    from termcolor import colored
    if type(to_print) != str:
        to_print = str(to_print)
    if len(argv) > 0:
        for arg in argv:
            to_print += " "+str(arg)
    if replace_this_line:
        end = '\r'
    else:
        end = kwargs.pop('end', '\n')
    print(colored(to_print, "magenta"), end=end, **kwargs)


def fast_rolling_average(my_list, window_size, wraparound=True, **kwargs):
    import pandas as pd
    if window_size == 0:
        if type(my_list) in [list, np.ndarray]:
            return pd.DataFrame(my_list)
        return my_list
    elif type(window_size) == float:
        window_size = round(window_size)
    if type(my_list) == np.ndarray:
        my_list = list(my_list)
    if wraparound:
        wraparound = int(window_size/2+2)
        final_index = slice(wraparound,-wraparound)
    else: final_index = slice(None)
    if type(my_list) == list:
        df = pd.DataFrame(my_list)
    else:
        df = my_list
    if wraparound: df = pd.concat([df.iloc[-wraparound:], df, df.iloc[:wraparound]])
    return df.rolling(window_size, **kwargs).mean().fillna(method="bfill").iloc[final_index]


def completion_sound():
    from winsound import Beep
    notes = [(440, 300), (494, 300), (523, 300), (587, 300), (659, 300)]  # Pairs of (frequency, duration)
    for note, duration in notes:
        Beep(note, duration)


def select_pickle(predetermined_choice=False, pickle_folder="PickleJar\\"):
    import glob
    pickle_files = glob.glob(os.path.join(pickle_folder, "data_results_*"))
    if not pickle_files:
        print_red("No data_results_* files found in PickleJar folder.")
        return None

    if predetermined_choice==True:
        predetermined_choice = 1
    pickle_files.sort(key=os.path.getmtime, reverse=True)
    print_blue(f"Found {len(pickle_files)} data_results_* files.")
    print_blue(f"Most recent file: {pickle_files[0]}")

    if predetermined_choice == 1 or len(pickle_files) == 1 or predetermined_choice == "most_recent":
        # Either use defaults or no appropriate pickle files were found, so just use the most recent file
        # most_recent_file = max(pickle_files, key=lambda x: os.path.getctime(pickle_folder + x))
        return pickle_files[0]
    elif type(predetermined_choice) == int:
        user_input = str(predetermined_choice)
    elif predetermined_choice == "combine":
        user_input = '5'
    else:
        print_yellow("Select the pickle file to load:")
        print_yellow("1. Most recent file")
        print_yellow("2. Largest file")
        print_yellow("3. Pick among the 10 most recent files")
        print_yellow("4. Enter the filename manually")
        print_yellow("5. A combination of the most recent allyears and allopt pickle files")
        user_input = input("Please enter the option number: ")

    if user_input == '1':
        # Most recent file
        return pickle_files[0]  # The list is already sorted by modification time
    elif user_input == '2':
        # Largest file
        pickle_files.sort(key=os.path.getsize, reverse=True)
        return pickle_files[0]
    elif user_input == '3':
        # Pick among the 10 most recent files
        print_yellow("Pick among the 10 most recent files:")
        for i, f in enumerate(pickle_files[:10]):
            print(f"{i + 1}. " + f.split("\\")[-1])
        user_input = input("Please enter the option number: ")
        try:
            return pickle_files[int(user_input) - 1]
        except:
            print_red("Invalid input. Falling back to the most recent file.")
            return pickle_files[0]
    elif user_input == '4':
        # Enter the filename manually
        user_input = input("Please enter the filename: ")
        if user_input in pickle_files or "PickleJar\\" + user_input in pickle_files or "PickleJar\\" + user_input + ".pickle" in pickle_files or "PickleJar\\" + user_input + ".blosc" in pickle_files:
            if "PickleJar\\" not in user_input:
                user_input = "PickleJar\\" + user_input
            return user_input
        else:
            print_red("The file was not found in the directory. Falling back to the most recent file.")
            return pickle_files[0]
    elif user_input == '5':
        # A combination of the most recent allyears and allopt pickle files
        allyears_pickle = max([f for f in pickle_files if "allyears" in f], key=os.path.getmtime)
        allopt_pickle = max([f for f in pickle_files if "allopt" in f or "trueref" in f], key=os.path.getmtime)
        return [allyears_pickle, allopt_pickle]


def shorten_year(scenario):
    import re
    # define a function to be used in re.sub
    def replacer(match):
        return "'" + match.group()[-2:]

    # use re.sub to replace all occurrences of 4-digit years
    return re.sub(r'(19|20)\d{2}', replacer, scenario)


def prettify_scenario_name(name,return_single_as_year=False):
    #print_yellow(f"Prettifying scenario name: {name}")
    if "set1" in name:
        #print_yellow("Set 1 scenario detected")
        # turn set1_4opt into Set 1 (4 opt.)
        nr = name.split("_")[1].replace("opt", "")
        alt = " alt."*('alt' in name)
        even = ", eq. w."*('even' in name)
        if "even" in name: nr = 4
        return f"2 HP + {nr}{alt} opt." + even # 2 opt., 2 HP
    if "HP" in name and "opt" in name:
        parts = name.split("_")
        opt = parts[1][0]
        extra = f" ({parts[-1]})" if len(parts) == 3 and parts[-1]!="mean" else "" 
        if "2012" in extra:
            return f"{name[0]} HP + {opt} opt. (2012)" 
        elif "evenweights" in extra:
            extra = ", eq. w."
        return f"{name[0]} HP + {opt} opt.{extra}" 
    if "allyears" in name:
        return "All years"
    if "allopt" in name:
        # turn allopt2_final into All opt. (2 yr), and allopt2_final_a into All opt. (2 yr) a
        nr = name.split("_")[0].replace("allopt", "")
        if len(name.split("_")) == 3:
            abc = name.split("_")[2]
            abc = f" ({abc})"
        else:
            abc = ""
        return f"{nr} opt.{abc}"
    if "iter2_3" in name:
        return "Set (1 opt.)"
    elif "iter3_16start" in name:
        return "Set (2 opt.)"
    if "singleyear" in name:
        # turn 'singleyear_1989to1990_1h' into "'89-'90" using regex
        if return_single_as_year: return shorten_year(name)
        return "Single year"
    # remove 'base' and 'extreme' and split into a list
    parts = name.replace('base', '').replace('extreme', ' ').split()
    if "v2" in name or "_5_" in name:
        return f'Alt. set ({parts[0]} opt.)'
    elif "even" in name:
        return f'6 yr, eq. weights'
    # join the parts with appropriate labels
    return f'Set ({parts[0]} opt.)'

def load_from_file(filepath):
    """
    Read the data from the specified filepath. The following file formats are supported: .pickle, .csv, .blosc.
    If no file extension is specified, the function will first look for a .blosc file, then a .pickle file. This is recommended as it lends more flexibility to the function.
    """
    import os
    # if the file is a pickle file, load it as a pickle file
    expected_filetypes = [".pickle", ".csv", ".blosc"]
    if not any([filepath.endswith(ft) for ft in expected_filetypes]):
        filepath += ".blosc"
    #if the file is not found, look for a .pickle file instead
    if not os.path.isfile(filepath):
        filepath = filepath.replace(".blosc", ".pickle")
    if filepath.endswith(".pickle"):
        import pickle
        with open(filepath, "rb") as f:
            return pickle.load(f)
    elif filepath.endswith(".csv"):
        import pandas as pd
        return pd.read_csv(filepath)
    elif filepath.endswith(".blosc"):
        import blosc2 as blosc
        import pickle
        blosc.set_nthreads(4)
        with open(filepath, "rb") as f:
            data = blosc.decompress(f.read())
        return pickle.loads(data)
    
def save_to_file(data, filepath, clever=5, nthreads=4, max_compression=True, **kwargs):
    """
    Save the data to the specified filepath. The following file formats are supported:
    1 .pickle (NOT RECOMMENDED): A standard, uncompressed way of storing python objects in binary files. Fast to save and load, but takes up a lot of space. If you want to prioritize speed, consider using .blosc with max_compression=False instead.
    2 .csv: Available only to pandas objects with a .to_csv() method.
    3 .blosc (default): A compressed binary file format. Might take another second to load/save a ~1GB file, but instead it takes up only a fraction of the space of a pickle file.
    If no file extension is specified, it defaults to .blosc. This is recommended as it lends more flexibility to the function.

    Parameters:
    -----------
    data: the data to be saved
    filepath: the path to the file to be saved. If no file extension is specified, it defaults to .blosc
    clever: the compression level to use. 0 is fastest, 9 is slowest. 5 is the default and recommended value as no big gains are made by going higher.
    nthreads: the number of threads to use for compression. Large diminishing returns after 4 threads.
    max_compression: if False, use LZ4 compression instead of ZSTD. LZ4 is a lot faster, but ZSTD is a lot more efficient.
    **kwargs: additional arguments to be passed to blosc.compress2()

    Notes on speed:
    ---------------
    With max_compression=False, about 90% of the time to save a file is spent on serializing the data which must be regardless of compression or not.
    With max_compression=True, the time spent compressing the data can become a significant portion of the total time to save a file. Still, the time spent is not enough to make you bored.
    """
    # if the file is a pickle file, save it as a pickle file
    supported_filetypes = [".pickle", ".csv", ".blosc"]
    if not any([filepath.endswith(ft) for ft in supported_filetypes]):
        filepath += ".blosc" #default to blosc
    if filepath.endswith(".pickle"):
        import pickle
        with open(filepath, "wb") as f:
            pickle.dump(data, f, protocol=pickle.DEFAULT_PROTOCOL) # HIGHEST_PROTOCOL is faster but only available in Python 3.8+
        if max_compression:
            print_red("Max compression not supported for pickle files. Save as .blosc instead.")
    elif filepath.endswith(".csv"):
        import pandas as pd
        data.to_csv(filepath)
    elif filepath.endswith(".blosc"):
        import blosc2 as blosc
        import pickle
        blosc.set_nthreads(nthreads)
        if not max_compression:
            codec_to_use = blosc.Codec.LZ4
        else:
            codec_to_use = blosc.Codec.ZSTD
        bytes_data = pickle.dumps(data, protocol=pickle.DEFAULT_PROTOCOL)
        with open(filepath, "wb") as f:
            f.write(blosc.compress2(bytes_data, codec=codec_to_use, clevel=clever, filter=blosc.Filter.SHUFFLE, **kwargs))
    else:
        print_red(f"File extension not recognized: {filepath}")
        return None
    #print_green(f"Data saved to {filepath}")
    return None