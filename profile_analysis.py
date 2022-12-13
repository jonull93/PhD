import mat73
import matplotlib.pyplot as plt

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


def get_accumulated_deficiency(profile):
    """
    takes a single profile and returns an accumulated deficiency profile
    Parameters
    ----------
    profile

    Returns
    -------
    accumulated deficiency
    """

    mean = profile.mean(axis=0)
    print(f"mean is {mean}")
    diff = mean-profile
    accumulated = diff.cumsum(axis=0)
    return accumulated


years = range(1987,1988)
region = "nordic_L"
VRE = ["wind", "solar"]
profile_keys= {"wind": 'CFtime_windonshoreA', 'solar': 'CFtime_pvplantA'}
capacity_keys = {"wind": 'capacity_onshoreA', 'solar': 'capacity_pvplantA'}
for year in years:
    print(f"Year {year}")
    for VRE in ["wind", "solar"]:
        print(f"- {VRE} -")
        filename = f"D:\GISdata\output\GISdata_{VRE}{year}_{region}.mat"
        # [site,region]
        # if there is a time dimension, the dimensions are [time,region,site]
        mat = mat73.loadmat(filename)
        profiles = mat[profile_keys[VRE]]
        capacities = mat[capacity_keys[VRE]]
        print(capacities)
        for site in range(len(capacities[0,:])):
            caps = capacities[:,-site-1]
            caps.sort()
            print(f"Testing site {5-site} where cap is {caps}")
            if caps[0]>1:
                viable_site = 5-site
                break
        print(f"first viable site is {viable_site}")
        FLHs = get_FLH(profiles[:,:,:])
        print(FLHs[:,viable_site-1])
        print(profiles[:,:,viable_site-1])
        accumulated = get_accumulated_deficiency(profiles[:,:,viable_site-1])
        print(accumulated)
        plt.plot(accumulated)
        plt.title(f"Deficiency of {VRE} in Year {year}")
        plt.legend(labels=["SE_NO_N", "SE_S", "NO_S", "FI", "DE_N", "DE_S"])
        plt.tight_layout()
        plt.show()

# accumulated * potential cap
# accumulated * "cost-optimal" cap mix
# - one line per subregion
# - one line for wind and one for solar
# - one total per year
