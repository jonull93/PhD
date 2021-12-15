import datetime as dt
import itertools
import os
import string
from enum import Enum

import pandas

from order_cap import order_cap
from order_gen import order_gen


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
    WIND_OFFSHORE = 'WOFF'
    WIND_ONSHORE_12 = 'WON12'
    WIND_ONSHORE_11 = 'WON11'
    WIND_ONSHORE_10 = 'WON10'
    WIND_ONSHORE_9 = 'WON9'
    WIND_ONSHORE_8 = 'WON8'
    WIND_ONSHORE_7 = 'WON7'
    WIND_ONSHORE_6 = 'WON6'
    WIND_ONSHORE_5 = 'WON5'
    WIND_ONSHORE_4 = 'WON4'
    WIND_ONSHORE_3 = 'WON3'
    WIND_ONSHORE_2 = 'WON2'
    WIND_ONSHORE_1 = 'WON1'
    SOLAR_OPT = 'PV_cSiOPT'
    SOLAR_TRACKING = 'PV_cSiTWO'
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
tech_names = {'RO': 'Hydro', 'U': 'Nuclear',
              'CHP_wa': 'Waste CHP', 'CHP_bio': 'Woodchip CHP', "G_CHP": "N. Gas CHP", "W_CHP": "Biomass CHP",
              "WA_CHP": "Waste CHP", "B_CHP": "Lignite CCS", "H_CHP": "Coal CHP", "WG_CHP": "Biogas CHP",
              'GWGCCS': 'Gas-mix CCS', "BCCS": "Lignite CCS", "HCCS": "Coal CCS", "GCCS": "N. Gas CCS",
              "BWCCS": "Lignite-biomass mix CCS", "BECCS": "Biomass CCS", "HWCCS": "Coal-biomass mix CCS",
              "WGCCS": "Biogas CCS",
              "bat_discharge": "Battery (dis)charge", 'WOFF': 'Offshore wind', 'WON': 'Onshore wind',
              'WG': 'Biogas CCGT', 'WG_peak': 'Biogas GT', 'wind_offshore': 'Offshore wind',
              "flywheel": "Flywheel", "bat": "Battery", "sync_cond": "Sync. Cond.",
              'wind_onshore': 'Onshore wind', 'PV_cSiOPT': 'Solar PV', 'EB': 'EB', 'HP': 'HP', 'HOB_WG': 'Biogas HOB',
              'HOB_bio': 'Woodchip HOB', 'solarheat': 'Solar heating', "curtailment": "Curtailment",
              'Load': 'Load', 'bat_PS': "Battery (PS)", 'bat_cap_PS': "Battery cap (PS)", 'bat_cap': "Battery cap",
              "electrolyser": "Electrolyser", "H": "Coal ST", "W": "Biomass ST",
              "G": "N. Gas CCGT", "G_peak": "N. Gas GT", "PV": "Solar PV", "FC": "Fuel cell",
              "H2store": "H2 storage",
              }
scen_names = {"_pre": "Base case", "_leanOR": "Lean OR", "_OR": "OR", "_OR_fixed": "OR", "_OR_inertia": "OR + Inertia",
              "_OR+inertia_fixed": "OR + Inertia", "_inertia": "Inertia", "_inertia_2x": "2x Inertia",
              "_inertia_noSyn": "Inertia (noSyn)", "_OR_inertia_3xCost": "OR + Inertia (3x)",
              "_inertia_3xCost": "Inertia (3x)", "_inertia_noSyn_3xCost": "Inertia (noSyn) (3x)", "noFC": "Base",
              "fullFC": "Inertia+FR", "OR": "FR", "inertia": "Inertia"}
color_dict = {'wind_onshore': '#B9B9B9', 'wind_offshore': '#DADADA', 'RO': 'xkcd:ocean blue', 'U': 'xkcd:grape',
              'GWGCCS': 'xkcd:dark peach', 'WA_CHP': 'xkcd:deep lavender', 'CHP_bio': 'xkcd:tree green',
              'WG': '#a4be20', 'WG_peak': '#b6cb4d', "WG_CHP": "#83981a",
              'PV_cSiOPT': 'xkcd:mustard', 'CHP_WG_L': 'xkcd:mid green',
              'HP': "#e85d04", 'EB': "#f48c06",
              'CHP_WG': (0, 176 / 255, 80 / 255),
              'HOB_WG': (128 / 255, 128 / 255, 0), 'solarheat': (204 / 255, 51 / 255, 0), 'HOB_bio': 'green',
              'Load': 'Black', "bat_discharge": "xkcd:amber", 'bat': "#714b92",
              'bat_cap': "#8d5eb7", 'Bat. In': "#8d5eb7", 'Bat. Out': "#8d5eb7", 'bat_PS': "xkcd:deep lavender",
              'bat_cap_PS': "xkcd:deep lavender", "sync_cond": 'xkcd:aqua', "curtailment": "xkcd:slate",
              'WOFF': '#DADADA', 'WON': '#B9B9B9', "H": "#172226", "W": "#014421",
              "W_CHP": "#016421", "G": "#5B90F6", "G_peak": "#7209b7", "G_CHP": "#5BB0F6", "PV": "#FDC12A",
              "FC": "#c65082", "H2store": "#ad054d", "electrolyser": "#68032e", "BECCS": "#5b9aa0"}

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
EPODs = EPODreg_to_country.keys()

scenario_shortening = {"iberia": "IB", "brit": "BR", "nordic": "NE",
                       "CO2price": "CO2p", "fullFC": "FC", }

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


def write_inc(path, filename, var, flip=True):
    """

    Parameters
    ----------
    path
    filename
    var
    flip

    Returns
    -------
    nothing, but creates path/filename.inc containing a variable with 2 or 3 sets, e.g. tech + reg (+ opt. timestep)
    """
    with open(path + filename, "w") as writer:
        for reg in var:
            if type(var[reg]) == dict:
                for tech in var[reg]:
                    try:
                        for timestep, value in var[reg][tech].items():
                            if flip:
                                writer.write(f"{tech} . {reg} . {timestep}  {value}\n")
                            else:
                                writer.write(f"{reg} . {tech} . {timestep}  {value}\n")
                    except:
                        value = var[reg][tech]
                        if flip:
                            writer.write(f"{tech} . {reg}  {value}\n")
                        else:
                            writer.write(f"{reg} . {tech}  {value}\n")
            elif type(var[reg]) == list:
                for i, value in enumerate(var[reg]):
                    writer.write(f"{reg} . {'h' + str(i + 1).zfill(4)}  {value}\n")
    return None


def write_inc_from_df_columns(path, filename, var: pandas.DataFrame):
    """

    Parameters
    ----------
    path
    filename
    var

    Returns
    -------
    nothing, but creates path/filename.inc containing a variable with 2 or 3 sets, e.g. tech + reg (+ opt. timestep)
    """
    try:
        os.mkdir(path)
    except:
        None

    with open(path + filename, "w") as writer:
        dim = len(var.columns)
        for ind, row in var.iterrows():
            line = " . ".join(row[:-1]) + f"  {row[-1]}\n"
            writer.write(line)
    return None


def append_to_file(filename, scenario, time_to_solve):
    "adds 'to_add' to a new line at the top of originalfile"
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


def print_red(to_print: str, **argv):
    from termcolor import colored
    for arg in argv:
        to_print += str(arg)
    print(colored(to_print, "red"))


def print_green(to_print: str, **argv):
    from termcolor import colored
    for arg in argv:
        to_print += str(arg)
    print(colored(to_print, "green"))


def print_cyan(to_print: str, **argv):
    from termcolor import colored
    for arg in argv:
        to_print += " "+str(arg)
    print(colored(to_print, "cyan"))
