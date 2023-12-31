import pickle
import time
import re

from copy import deepcopy
from my_utils import write_inc, print_cyan
import numpy as np

# This file defines three functions which are used in the following order:
# read_file reads tech profiles from .inc files
# build_ramp uses the profiles from read_file to build a hour-to-hour-variations profile (ramping profile)
# write_inc takes the ramping profile and writes a new .inc from it

regions = ['AT', 'BE', 'BO', 'BG', 'CR', 'CY', 'CZ', 'DE1', 'DE2', 'DE3', 'DE4', 'DE5', 'DK1', 'DK2', 'EE', 'ES1',
           'ES2', 'ES3', 'ES4', 'FI', 'FR1', 'FR2', 'FR3', 'FR4', 'FR5', 'GR', 'HU', 'IE', 'IS', 'IT1', 'IT2', 'IT3',
           'LT', 'LU', 'LV', 'MC', 'MT', 'NL', 'NO1', 'NO2', 'NO3', 'PO1', 'PO2', 'PO3', 'PT', 'RO', 'SE1', 'SE2',
           'SE3', 'SE4', 'SI', 'SK', 'CH', 'UK1', 'UK2', 'UK3']
WON = ['WONA1', 'WONA2', 'WONA3', 'WONA4', 'WONA5', 'WONB1', 'WONB2', 'WONB3', 'WONB4', 'WONB5']
WOFF = ["WOFF1", "WOFF2", "WOFF3"]
PV = ['PVPA1', 'PVPB1', 'PVR1']
allhours = [f"h{str(i).rjust(4, '0')}" for i in range(1, 8785)]
WON_profiles = {reg: {tech: {hour: 0 for hour in allhours} for tech in WON} for reg in regions}
WOFF_profiles = {reg: {tech: {hour: 0 for hour in allhours} for tech in WOFF} for reg in regions}
PV_profiles = {reg: {tech: {hour: 0 for hour in allhours} for tech in PV} for reg in regions}
# {reg: {tech: {timestep: value}}}
path = "C:\\git\\multinode_uncertainties\\Include\\weather_data\\"
out_path = "C:\\git\\multinode_uncertainties\\Add-ons\\PS\\include\\"


def clean_file(filename, new_filename):
    with open(filename, 'r') as r, open(new_filename, 'w') as o:
        for line in r:
            # strip() function
            if line.strip():
                o.write(line)


def read_file(filename, profiles):
    with open(path + filename, "r") as reader:
        for i_l, line in enumerate(reader):
            data = list(filter(None, re.split('\s\.\s|\s', line)))
            try:
                reg = data[0]
            except:
                print("Ran into error at", i_l, line)
                exit()
            tech = data[1]
            timestep = data[2]
            value = float(data[3])
            profiles[reg][tech][timestep] = value
    return profiles


def build_ramp(profiles):
    # This function now considers the coming hour when profile decreases, and the previous hour when profile increases
    # Furthermore, the reserve demand from ramping VRE is limited to the hourly VRE prod (i.e. no expected prod means no
    # reserve demand)
    # This means that incoming VRE next hour will NOT trigger a reserve demand this hour, to avoid reserve demand before
    # the VRE is actually thought to "arrive"
    ramp = {}
    for reg in profiles:
        ramp[reg] = {}
        for tech, data in profiles[reg].items():
            ramp[reg][tech] = {}
            timesteps = list(data.keys())
            for nr, timestep in enumerate(timesteps):
                if nr < len(timesteps) - 1:
                    downwards = max(0, data[timesteps[nr]] - data[timesteps[nr + 1]])
                else:
                    downwards = 0
                if nr == 0:
                    upwards = 0
                else:
                    upwards = abs(data[timesteps[nr]] - data[timesteps[nr - 1]])
                limited_by_prod = min(data[timesteps[nr]], max(downwards, upwards))
                ramp[reg][tech][timestep] = np.round(limited_by_prod, decimals=5)
    return ramp


# for year in range(2010,2020):
#    filename = f"_profile_PV_{year}.inc"
#    clean_file(path + filename, path + filename.replace("_profile", "profile"))
#    filename = f"_profile_WONA_{year}.inc"
#    clean_file(path + filename, path + filename.replace("_profile", "profile"))
#    filename = f"_profile_WOFF_{year}.inc"
#    clean_file(path + filename, path + filename.replace("_profile", "profile"))
# cf_Windonshore.INC


for year in range(2010, 2020):
    print_cyan(year)
    WON_profiles = read_file(f"Profile_WONA_{year}.inc", WON_profiles)
    print("-- Read WON_profiles --")
    WON_ramp = build_ramp(WON_profiles)
    print("-- Built WON ramps --")
    WOFF_profiles = read_file(f"Profile_WOFF_{year}.inc", WOFF_profiles)
    print("-- Built WOFF_profiles --")
    WOFF_ramp = build_ramp(WOFF_profiles)
    PV_profiles = read_file(f"Profile_PV_{year}.inc", PV_profiles)
    print("-- Built PV_profiles --")
    PV_ramp = build_ramp(PV_profiles)
    VRE_ramp = {reg: {tech: {year: {}} for tech in WON + WOFF + PV} for reg in regions}
    for reg in regions:
        for tech in WON:
            VRE_ramp[reg][tech][year] = WON_ramp[reg][tech]
        for tech in WOFF:
            VRE_ramp[reg][tech][year] = WOFF_ramp[reg][tech]
        for tech in PV:
            VRE_ramp[reg][tech][year] = PV_ramp[reg][tech]

    print("-- Combined ramps --")
    write_inc(out_path, f"VRE_ramp_{year}.inc", VRE_ramp, fliplast=True)
    print("-- Wrote ramps to .inc file --")
