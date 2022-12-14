import mat73
import matplotlib.pyplot as plt
import pickle
import pandas as pd

"""

- VRE profile analysis -

- INPUT
profiles per cluster region

- OUTPUT
FLHs
generation duration curves
accumulated deficiency
    deficiency = mean generation - hourly generation

"""


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
        return profile.sum(axis=0)*weights
    else:
        return profile.sum(axis=0)


def get_sorted(profile):
    _profile = profile.copy()
    return _profile.sort(reverse=True)


def get_accumulated_deficiency(wind_profiles,wind_cap,solar_profiles,solar_cap,demand_profile,extra_demand):
    solar_prod = wind_profiles
    mean = profile.mean(axis=0)
    print(f"mean is {mean}")
    diff = mean-profile
    accumulated = diff.cumsum(axis=0)
    return accumulated


pickle_file = "PickleJar\\data_results_3h.pickle"
initial_results = pickle.load(open(pickle_file,"rb"))
scenario_name = "nordic_lowFlex_noFC_2040_3h"
print(initial_results[scenario_name].keys())
cap = initial_results[scenario_name]["tot_cap"]
print(cap)
exit()
years = range(1987,1988)
sites = range(1,6)
region_name = "nordic_L"
VRE = ["wind", "solar"]
regions = ["SE_NO_N", "SE_S", "NO_S", "FI", "DE_N", "DE_S"]
profile_keys= {"wind": 'CFtime_windonshoreA', 'solar': 'CFtime_pvplantA'}
capacity_keys = {"wind": 'capacity_onshoreA', 'solar': 'capacity_pvplantA'}
for year in years:
    print(f"Year {year}")
    VRE_profiles = pd.DataFrame(columns=pd.MultiIndex.from_product([sites, regions],names=["site","region"]))
    for VRE in ["wind", "solar"]:
        print(f"- {VRE} -")
        filename = f"D:\GISdata\output\GISdata_{VRE}{year}_{region_name}.mat"
        # [site,region]
        # if there is a time dimension, the dimensions are [time,region,site]
        mat = mat73.loadmat(filename)
        profiles = mat[profile_keys[VRE]]
        capacities = mat[capacity_keys[VRE]]
        print(capacities)
        for site in sites:
            caps = capacities[:,-site-1]
            caps.sort()
            print(f"Testing site {5-site} where cap is {caps}")  # testing the sites backwards to stop at the first feasible critera
            if caps[0]>1:
                viable_site = 5-site
                break
        for site in sites:  # need another loop which wont break
            VRE_profiles[:,site] = profiles[:,:,site-1]
        print(f"first viable site is {viable_site}")
        FLHs = get_FLH(profiles[:,:,:])
        print(FLHs[:,viable_site-1])
        print(profiles[:,:,viable_site-1])
        accumulated = get_accumulated_deficiency(profiles[:,:,viable_site-1])
        print(accumulated)
        plt.plot(accumulated)
        plt.title(f"Deficiency of {VRE} in Year {year}")
        plt.legend(labels=regions)
        plt.tight_layout()
        plt.show()

# accumulated * potential cap
# accumulated * "cost-optimal" cap mix
# - one line per subregion
# - one line for wind and one for solar
# - one total per year
