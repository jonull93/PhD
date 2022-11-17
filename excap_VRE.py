from my_utils import write_inc, print_red, print_cyan, print_green

# To run this file, edit the paths below and make sure you have the GIS capacity_Windonshore.inc in the inc_path
# And to import from my_utils.py, just make sure it exists in the same folder as this script

destination_path = "C:\\Users\\jonull\\Downloads\\"
inc_path = "C:\\Users\\jonull\\git\\multinode\\Include\\"

gdp = {  # EPODreg: GDPs, from some model include file I found
    'AT': 283085, 'BE': 345005, 'BO': 1, 'BG': 35431, 'CR': 1, 'CY': 17287, 'CZ': 147878, 'DE1': 805132, 'DE2': 136621,
    'DE3': 923361, 'DE4': 485858, 'DE5': 130229, 'DK1': 112874, 'DK2': 120608, 'EE': 16107, 'ES1': 93906, 'ES2': 492731,
    'ES3': 288218, 'ES4': 167198, 'FI': 184649, 'FR1': 209333, 'FR2': 182809, 'FR3': 224019, 'FR4': 138602,
    'FR5': 1.1587e+06, 'GR': 236919, 'HU': 106374, 'IE': 179989, 'IS': 1, 'IT1': 860650, 'IT2': 376894, 'IT3': 330309,
    'LT': 32288, 'LU': 39640, 'LV': 23037, 'MC': 1, 'MT': 5797, 'NL': 596227, 'NO1': 997461, 'NO2': 89424, 'NO3': 93939,
    'PO1': 112648, 'PO2': 146775, 'PO3': 103729, 'PT': 172022, 'RO': 139766, 'SE1': 42792, 'SE2': 260420, 'SE3': 12373,
    'SE4': 17672, 'SI': 37305, 'SK': 64572, 'CH': 1, 'UK1': 1.62489e+06, 'UK2': 149033, 'UK3': 41495
}

EPODreg_to_country = {  # dictionary for going between EPODreg to country
    'AT': 'Austria', 'BE': 'Belgium', 'BO': 'Bosnia', 'BG': 'Bulgaria', 'CR': 'Croatia', 'CY': 'Cyprus',
    'CZ': 'Czech', 'DK1': 'Denmark', 'DK2': 'Denmark', 'EE': 'Estonia', 'FI': 'Finland', 'FR1': 'France',
    'FR2': 'France', 'FR3': 'France', 'FR4': 'France', 'FR5': 'France', 'DE1': 'Germany', 'DE2': 'Germany',
    'DE3': 'Germany', 'DE4': 'Germany', 'DE5': 'Germany', 'GR': 'Greece', 'HU': 'Hungary', 'IS': 'Iceland',
    'IE': 'Ireland', 'IT1': 'Italy', 'IT2': 'Italy', 'IT3': 'Italy', 'LV': 'Latvia', 'LT': 'Lithuania',
    'LU': 'Luxembourg', 'MC': 'Macedonia', 'MT': 'Malta', 'NL': 'Netherlands', 'NO_S': 'Norway', 'NO_N': 'Norway',
    'NO1': 'Norway', 'NO2': 'Norway', 'NO3': 'Norway', 'PO1': 'Poland', 'PO2': 'Poland', 'PO3': 'Poland',
    'PT': 'Portugal', 'RO': 'Romania', 'SK': 'Slovakia', 'SI': 'Slovenia', 'ES_N': 'Spain', 'ES_S': 'Spain',
    'ES1': 'Spain', 'ES2': 'Spain', 'ES3': 'Spain', 'ES4': 'Spain', 'SE_N': 'Sweden', 'SE_S': 'Sweden', 'SE1': 'Sweden',
    'SE2': 'Sweden', 'SE3': 'Sweden', 'SE4': 'Sweden', 'CH': 'Switzerland', 'UK1': 'UK', 'UK2': 'UK', 'UK3': 'UK'
}

national_cap_WON = {  # data for 2021 from https://web.archive.org/web/20221019142356/https://proceedings.windeurope.org/biplatform/rails/active_storage/disk/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9JYTJWNVNTSWhORFJ0ZDJJMWVUbG9OMll6TVRaaGEza3lkamgxZG1aM056WnZZZ1k2QmtWVU9oQmthWE53YjNOcGRHbHZia2tpQVk1cGJteHBibVU3SUdacGJHVnVZVzFsUFNKWGFXNWtaWFZ5YjNCbExWZHBibVF0Wlc1bGNtZDVMV2x1TFVWMWNtOXdaUzB5TURJeExYTjBZWFJwYzNScFkzTXVjR1JtSWpzZ1ptbHNaVzVoYldVcVBWVlVSaTA0SnlkWGFXNWtaWFZ5YjNCbExWZHBibVF0Wlc1bGNtZDVMV2x1TFVWMWNtOXdaUzB5TURJeExYTjBZWFJwYzNScFkzTXVjR1JtQmpzR1ZEb1JZMjl1ZEdWdWRGOTBlWEJsU1NJVVlYQndiR2xqWVhScGIyNHZjR1JtQmpzR1ZBPT0iLCJleHAiOiIyMDIyLTEwLTE5VDE0OjI4OjQ5LjM0NFoiLCJwdXIiOiJibG9iX2tleSJ9fQ==--44e68980d582b9078ca3e9467c9f891971a042aa/Windeurope-Wind-energy-in-Europe-2021-statistics.pdf?content_type=application%2Fpdf&disposition=inline%3B+filename%3D%22Windeurope-Wind-energy-in-Europe-2021-statistics.pdf%22%3B+filename%2A%3DUTF-8%27%27Windeurope-Wind-energy-in-Europe-2021-statistics.pdf
    'Austria': 3300, 'Belgium': 2741, 'Bulgaria': 707, 'Croatia': 990, 'Cyprus': 158, 'Czech': 337, 'Denmark': 4870,
    'Estonia': 320, 'Finland': 3257, 'France': 19079, 'Germany': 56130, 'Greece': 4452, 'Hungary': 329, 'Ireland': 4380,
    'Italy': 11108, 'Latvia': 66, 'Lithuania': 668, 'Luxembourg': 168, 'Malta': 0, 'Netherlands': 5179, 'Poland': 6347,
    'Portugal': 5587, 'Romania': 3029, 'Slovakia': 3, 'Slovenia': 3, 'Spain': 28191, 'Sweden': 11905, 'UK': 14073,
    'Norway': 4649, 'Switzerland': 87
}

national_cap_WOFF = {  # data emailed from Jan on 2021-03-23
    'Austria': 0, 'Belgium': 2261, 'Bulgaria': 0, 'Croatia': 0, 'Cyprus': 0, 'Czech': 0, 'Denmark': 2308,
    'Estonia': 0, 'Finland': 71, 'France': 2, 'Germany': 7713, 'Greece': 0, 'Hungary': 0, 'Ireland': 25, 'Italy': 0,
    'Latvia': 0, 'Lithuania': 0, 'Luxembourg': 0, 'Malta': 0, 'Netherlands': 2986, 'Poland': 0, 'Portugal': 25, 'Romania': 0,
    'Slovakia': 0, 'Slovenia': 0, 'Spain': 5, 'Sweden': 192, 'UK': 12739, 'Norway': 6, 'Switzerland': 0

}
ratio_gdp = {reg: 1 for reg in gdp}  # EPODreg: ratio, such that sum of ratios for each subregion equals 1
for reg, reg_gdp in gdp.items():
    try:
        int(reg[-1])  # this would throw an error if the last character isn't a number
        national_gdp = sum([gdp[reg2] for reg2 in gdp if reg[:-1] in reg2])
        ratio_gdp[reg] = reg_gdp / national_gdp
    except:
        None

WON_techs = ["WON" + ab + str(dig) for dig in range(5, 0, -1) for ab in ["A"]]
WOFF_techs = ['WOFF'+str(d) for d in range(3,0,-1)]
WON_pot = {reg: {tech: 0 for tech in WON_techs} for reg in gdp}
WOFF_pot = {reg: {tech: 0 for tech in WOFF_techs} for reg in gdp}
cap_density_WON = 0.1  # area utility factor, almost completely arbitrary numbers ¯\_(ツ)_/¯
cap_density_WOFF = 0.33

with open(inc_path+"weather_data\\Capacity_WONA.inc") as reader:
    for line in reader:
        reg, other = line.split(" . ")
        reg = reg.split()[0]
        tech, pot = other.split()
        WON_pot[reg][tech] = float(pot) * cap_density_WON

with open(inc_path+"weather_data\\Capacity_WOFF.inc") as reader:  # "capacity_Windoffshore.inc"
    for line in reader:
        reg, other = line.split(" .")
        reg = reg.split()[0]
        tech, pot = other.split()
        WOFF_pot[reg][tech] = float(pot) * cap_density_WOFF


def newWeights(numbers):
    """

    Parameters
    ----------
    numbers

    Returns
    -------
    takes a list of numbers and returns normalized weights: 15, 3, 2 -> 0.75, 0.15, 0.10
    """
    return {key: val / sum(numbers.values()) for key, val in numbers.items()}


def filler(amount, destinations, weights, limits, vocal=False):
    """
    Takes a number 'amount' and fills it in a 2-layered 'destinations' where the first layer has 'weights' and the
    second layer has 'limits'. For wind capacity allocation, it spreads out investments in the best available wind sites
    in a country while taking gdp into account for subregions
    """
    regs = list(limits.keys())
    print_cyan(f" - Starting to allocate {amount} in {regs} - ")
    old_cap = sum(x for counter in destinations.values() for x in counter.values())
    to_fill = amount
    techs = list(limits[regs[0]].keys())
    return_dict = {reg:{tech:0 for tech in techs} for reg in regs}
    spareRoomTech = {reg: {tech: limits[reg][tech] for tech in techs} for reg in regs}
    if vocal: print_green(f"{techs=}", f"{amount=}",  f"{weights=}", f"{limits=}",)

    while to_fill > 0:  # while there still is to_fill left to allocate
        for tech in techs:  # first, prioritize filling the first tech in each region before moving on to next tech
            if to_fill <= 0: continue  # no need to do anything if we've already used up 'to_fill' in previous tech
            loopRegs = regs
            print(
                f"Starting to fill {tech} with {to_fill} and spare room {round(sum([spareRoomTech[reg][tech] for reg in loopRegs]), ndigits=3)}")
            while sum([spareRoomTech[reg][tech] for reg in loopRegs]) > 0 and to_fill > 0:
                # we use another while-loop since we allocate according to gdp ratios (weights)
                # this may result in some regs hitting their lim while others didnt
                # so we loop until all regs are full for this tech, or we used all the to_fill to allocate
                filled = 0
                loopRegs = [reg for reg in regs if spareRoomTech[reg][tech] > 0]
                loopWeights = newWeights({reg: weights[reg] for reg in loopRegs})
                # print(f"to_fill left: {to_fill}, with weights: {loopWeights}")
                # print(f"Spare room: {spareRoomTech}")
                for reg in loopRegs:
                    lim = spareRoomTech[reg][tech]
                    regFill = to_fill * loopWeights[reg]
                    # print(f"At {reg} with {lim} room left and {regFill} to put in it")
                    if regFill < lim:
                        destinations[reg][tech] = regFill
                        filled += regFill
                        spareRoomTech[reg][tech] = lim - regFill
                    else:
                        destinations[reg][tech] = lim
                        filled += lim
                        spareRoomTech[reg][tech] = 0
                to_fill -= filled
        if sum([spareRoomTech[reg][tech] for reg in loopRegs]) == 0 and to_fill > 0:
            print(f"!! ran out of space in {loopRegs} for {tech}")
            raise ArithmeticError
    diff = round(sum(x for counter in destinations.values() for x in counter.values()) - old_cap,4)
    error = diff-amount > 0.01
    if error:
        print(old_cap,sum(x for counter in destinations.values() for x in counter.values()),amount)
        raise ArithmeticError
    #print(f"Finished {regs}")
    return destinations


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


existingCapacity = {reg: {tech: 0 for tech in WON_techs + WOFF_techs} for reg in gdp}
for country, cap in national_cap_WON.items():
    if cap <= 0:
        continue
    else:
        filler(cap / 1000, existingCapacity, country_to_reg(ratio_gdp, country), country_to_reg(WON_pot, country))

for country, cap in national_cap_WOFF.items():
    if cap <= 0:
        continue
    else:
        filler(cap / 1000, existingCapacity, country_to_reg(ratio_gdp, country), country_to_reg(WOFF_pot, country), vocal=True)

existingCapacity2 = {reg: {tech: 0 for tech in WON_techs + WOFF_techs} for reg in gdp}
if list(national_cap_WON.keys()).sort() != list(national_cap_WON.keys()).sort():
    print_red("! The countries for WON and for WOFF are different !")
"""existingCapacity2 = {}
for country in national_cap_WON:
    regs = [reg for reg,_country in EPODreg_to_country.items() if _country==country]
    {reg: {tech: 0 for tech in WON_techs + WOFF_techs} for reg in regs}
#    print_cyan(f" - Starting {country}: {regs}")
    WON_cap = national_cap_WON[country]
    WOFF_cap = national_cap_WOFF[country]
    if WON_cap > 0:
        filler(WON_cap / 1000, existingCapacity2, country_to_reg(ratio_gdp, country), country_to_reg(WON_pot, country))
    if WOFF_cap > 0:
        filler(WOFF_cap / 1000, existingCapacity2, country_to_reg(ratio_gdp, country), country_to_reg(WOFF_pot, country),
               vocal=True)

print(existingCapacity2)
if existingCapacity!=existingCapacity2: print_red(f"Mismatch between\n{existingCapacity=}\nand\n{existingCapacity2=}")"""

write_inc(destination_path, "existingCap_VRE_3.inc", existingCapacity)
