
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
    if type(profile[0]) == list:
        FLH = [sum(tech) for tech in profile]
        if not weights:
            weights = [1 for i in profile]
        return sum([FLH[i]*weights[i] for i in range(len(weights))])/sum(weights)
    else:
        FLH = sum(profile)
        return FLH


def get_sorted(profile):
    _profile = profile.copy()
    return _profile.sort(reverse=True)


def get_accumulated_deficiency(profile):
    """

    Parameters
    ----------
    profile

    Returns
    -------
    accumulated deficiency
    """

    mean = sum(profile)/[1 for i in profile]
    diff = [mean-i for i in profile]
    accumulated = [diff[0]]
    for val in diff:
        accumulated.append(accumulated[-1]+val)
    return accumulated

