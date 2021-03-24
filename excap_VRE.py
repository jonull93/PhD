from my_utils import write_inc

gdp = {
    'AT': 283085, 'BE': 345005, 'BO': 1, 'BG': 35431, 'CR': 1, 'CY': 17287, 'CZ': 147878, 'DE1': 805132, 'DE2': 136621,
    'DE3': 923361, 'DE4': 485858, 'DE5': 130229, 'DK1': 112874, 'DK2': 120608, 'EE': 16107, 'ES1': 93906, 'ES2': 492731,
    'ES3': 288218, 'ES4': 167198, 'FI': 184649, 'FR1': 209333, 'FR2': 182809, 'FR3': 224019, 'FR4': 138602,
    'FR5': 1.1587e+06, 'GR': 236919, 'HU': 106374, 'IE': 179989, 'IS': 1, 'IT1': 860650, 'IT2': 376894, 'IT3': 330309,
    'LT': 32288, 'LU': 39640, 'LV': 23037, 'MC': 1, 'MT': 5797, 'NL': 596227, 'NO1': 997461, 'NO2': 89424, 'NO3': 93939,
    'PO1': 112648, 'PO2': 146775, 'PO3': 103729, 'PT': 172022, 'RO': 139766, 'SE1': 42792, 'SE2': 260420, 'SE3': 12373,
    'SE4': 17672, 'SI': 37305, 'SK': 64572, 'CH': 1, 'UK1': 1.62489e+06, 'UK2': 149033, 'UK3': 41495
}  # EPODreg: value --- from parameter gdx file

EPODreg_to_country = {
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

national_cap_WON = {
    'Austria': 3159, 'Belgium': 2323, 'Bulgaria': 691, 'Croatia': 652, 'Cyprus': 158, 'Czech': 337, 'Denmark': 4426,
    'Estonia': 320, 'Finland': 2213, 'France': 16644, 'Germany': 53912, 'Greece': 3576, 'Hungary': 329, 'Ireland': 4130,
    'Italy': 10512, 'Latvia': 66, 'Lithuania': 548, 'Luxemb': 136, 'Malta': 0, 'Netherlands': 3482, 'Poland': 5917,
    'Portugal': 5429, 'Romania': 3029, 'Slovakia': 3, 'Slovenia': 3, 'Spain': 25803, 'Sweden': 8794, 'UK': 13570,
    'Norway': 2442, 'Switzerland': 75
}

national_cap_WOFF = {
    'Austria': 0, 'Belgium': 1556, 'Bulgaria': 0, 'Croatia': 0, 'Cyprus': 0, 'Czech Rep': 0, 'Denmark': 1703,
    'Estonia': 0, 'Finland': 71, 'France': 2, 'Germany': 7445, 'Greece': 0, 'Hungary': 0, 'Ireland': 25, 'Italy': 0,
    'Latvia': 0, 'Lithuania': 0, 'Luxemb': 0, 'Malta': 0, 'Netherlands': 1118, 'Poland': 0, 'Portugal': 8, 'Romania': 0,
    'Slovakia': 0, 'Slovenia': 0, 'Spain': 5, 'Sweden': 192, 'UK': 9945, 'Norway': 2, 'Switzerland': 0

}
ratio_gdp = {reg: 1 for reg in gdp}  # EPODreg: ratio (such that sum of ratios for each subregion equals 1
for reg, val in gdp.items():
    try:
        int(reg[-1])  # this would throw an error if the last character isn't a number
        national_gdp = sum([gdp[reg2] for reg2 in gdp if reg[:-1] in reg2])
        ratio_gdp[reg] = val / national_gdp
    except:
        None

techs = ["WON" + ab + str(dig) for dig in range(1, 6) for ab in ["A", "B"]]
WON_pot = {reg: {tech: 0 for tech in techs} for reg in gdp}
WOFF_pot = {reg: {'WOFF': 0} for reg in gdp}
cap_density_WON = 0.1
cap_density_WOFF = 0.33

with open(r"C:\git\multinode\Include\capacity_Windonshore.inc") as reader:
    for line in reader:
        reg, foobar = line.split(" .")
        reg = reg.split()[0]
        tech, pot = foobar.split()
        WON_pot[reg][tech] = float(pot)*cap_density_WON

with open(r"C:\git\multinode\Include\capacity_Windoffshore.inc") as reader:
    for line in reader:
        reg, foobar = line.split(" .")
        reg = reg.split()[0]
        tech, pot = foobar.split()
        WOFF_pot[reg][tech] = float(pot)*cap_density_WOFF


def newWeights(numbers):
    return {key:val/sum(numbers.values()) for key,val in numbers.items()}


def filler(amount, destinations, weights, limits):
    """
    Takes a number 'amount' and fills it in a 2-layered 'destinations' where the first layer has 'weights' and the second layer has 'limits'
    """
    from time import sleep
    regs = list(limits.keys())
    print(f"Starting to fill {regs}")
    techs = list(limits[regs[0]].keys())
    spareRoomTech = {reg: {tech: limits[reg][tech] for tech in techs} for reg in regs}
    while amount > 0:  # while there still is amount left to allocate
        for tech in techs:  # first, prioritize filling the first tech in each region before moving on to next tech
            if amount <= 0: continue  # no need to do anything if we've already used up 'amount' in previous tech
            loopRegs = regs
            print(f"-- Starting to fill {tech} with {amount} and spare room {round(sum([spareRoomTech[reg][tech] for reg in loopRegs]),ndigits=3)}")
            while sum([spareRoomTech[reg][tech] for reg in loopRegs]) > 0 and amount > 0:
                # we use another while-loop since we allocate according to gdp ratios (weights)
                # this may result in some regs hitting their lim while others didnt
                # so we loop until all regs are full for this tech, or we used all the amount to allocate
                filled = 0
                loopRegs = [reg for reg in regs if spareRoomTech[reg][tech] > 0]
                loopWeights = newWeights({reg: weights[reg] for reg in loopRegs})
                #print(f"Amount left: {amount}, with weights: {loopWeights}")
                #print(f"Spare room: {spareRoomTech}")
                for reg in loopRegs:
                    lim = spareRoomTech[reg][tech]
                    regFill = amount*loopWeights[reg]
                    #print(f"At {reg} with {lim} room left and {regFill} to put in it")
                    if regFill < lim:
                        destinations[reg][tech] = regFill
                        filled += regFill
                        spareRoomTech[reg][tech] = lim - regFill
                    else:
                        destinations[reg][tech] = lim
                        filled += lim
                        spareRoomTech[reg][tech] = 0
                amount -= filled
    print(f"Finished {regs}")
    return destinations


def country_to_reg(dictionary, country):
    return {reg: dictionary[reg] for reg in dictionary if country in EPODreg_to_country[reg]}


existingCapacity = {reg: {tech: 0 for tech in techs+['WOFF']} for reg in gdp}
for country, cap in national_cap_WON.items():
    if cap <= 0: continue
    else:
        filler(cap/1000, existingCapacity, country_to_reg(ratio_gdp, country), country_to_reg(WON_pot, country))

for country, cap in national_cap_WOFF.items():
    if cap <= 0: continue
    else:
        filler(cap/1000, existingCapacity, country_to_reg(ratio_gdp, country), country_to_reg(WOFF_pot, country))

write_inc("C:\\git\\multinode\\Include\\", "existingCap_VRE.inc", existingCapacity)

