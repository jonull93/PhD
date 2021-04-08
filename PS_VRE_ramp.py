import pickle
import time
import re

from copy import deepcopy
from my_utils import write_inc
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
WOFF = ["WOFF"]
PV = ['PVPA1', 'PVPB1', 'PVR1']
WON_profiles = {reg: {tech: {} for tech in WON} for reg in regions}  # {reg: {tech: {timestep: value}}}
WOFF_profiles = {reg: {tech: {} for tech in WOFF} for reg in regions}
PV_profiles = {reg: {tech: {} for tech in PV} for reg in regions}  # {reg: {tech: {timestep: value}}}
path = "C:\\models\\multinode\\Include\\"


def read_file(filename, profiles):
    with open(path+filename, "r") as reader:
        for line in reader:
            data = list(filter(None, re.split('\s\.\s|\s', line)))
            try: reg = data[0]
            except:
                print("Ran into error at",line)
                exit()
            tech = data[1]
            timestep = data[2]
            value = float(data[3])
            profiles[reg][tech][timestep] = value
    return profiles


def build_ramp(profiles):
    ramp = {}
    for reg in profiles:
        ramp[reg] = {}
        for tech, data in profiles[reg].items():
            ramp[reg][tech] = {}
            timesteps = list(data.keys())
            for nr, timestep in enumerate(timesteps):
                if nr < len(timesteps) - 1:
                    forward = abs(data[timesteps[nr]] - data[timesteps[nr + 1]])
                else:
                    forward = 0
                if nr == 0:
                    backward = 0
                else:
                    backward = abs(data[timesteps[nr]] - data[timesteps[nr - 1]])
                ramp[reg][tech][timestep] = np.round(max(forward, backward), decimals=5)
    return ramp


WON_profiles = read_file("cf_Windonshore.INC", WON_profiles)
print("-- Built WON_profiles --")
WON_ramp = build_ramp(WON_profiles)

WOFF_profiles = read_file("cf_Windoffshore.INC", WOFF_profiles)
print("-- Built WOFF_profiles --")
WOFF_ramp = build_ramp(WOFF_profiles)

PV_profiles = read_file("cf_PV.INC", PV_profiles)
print("-- Built PV_profiles --")
PV_ramp = build_ramp(PV_profiles)

VRE_ramp = {reg: {tech: {} for tech in WON+WOFF+PV} for reg in regions}
for reg in regions:
    for tech in WON:
        VRE_ramp[reg][tech] = WON_ramp[reg][tech]
    for tech in WOFF:
        VRE_ramp[reg][tech] = WOFF_ramp[reg][tech]
    for tech in PV:
        VRE_ramp[reg][tech] = PV_ramp[reg][tech]

print("-- Combined ramps --")
write_inc(path, "VRE_ramp.inc", VRE_ramp)
print("-- Wrote ramps to .inc file --")
