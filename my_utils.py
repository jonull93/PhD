import pickle  # for dumping and loading variable to/from file
from enum import Enum
import itertools
import string


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


order = [
    'bat_discharge',
    'efuel',
    'PTES_L',
    'PTES_L_HX',
    'TTES',
    'PTES_M',
    'PTES_M_HX',
    'TTES_HX',
    'BTES',
    'U',
    'B',
    'H',
    'W',
    'CHP_wa',
    'CHP_wa_L',
    'CHP_wa_M',
    'CHP_bio',
    'CHP_bio_L',
    'CHP_bio_M',
    'CHP_bio_S',
    'CHP_H_L',
    'CHP_H_M',
    'CHP_H_S',
    'CHP_G_L',
    'CHP_oil',
    'BCCS',
    'HCCS',
    'GCCS',
    'BWCCS',
    'BECCS',
    'HWCCS',
    'HCCS_flex',
    'HWCCS_flex',
    'HWCCS_flex_PS',
    'WGCCS',
    'GWGCCS',
    'GWGCCS_PS',
    'CHP_WG_M',
    'CHP_WG_L',
    'G',
    'WG',
    'WG_PS',
    'WG_peak',
    'WG_peak_PS',
    'G_peak',
    'FC',
    'RO',
    'RO_imp',
    'wind_offshore',
    'WOFF',
    'wind_onshore',
    'WON12',
    'WON11',
    'WON10',
    'WON9',
    'WON8',
    'WON7',
    'WON6',
    'WON5',
    'WON4',
    'WON3',
    'WON2',
    'WON1',
    'RR',
    'PS',
    'PV',
    'PV_cSiOPT',
    'PV_cSiTWO',
    'Small_hydro',
    'backstop',
    'bat',
    'bat_cap',
    'bat_PS',
    'bat_cap_PS',
    'flywheel',
    'sync_cond',
    'curtailment',
    # 'bat_LiIon',
    # 'bat_LiIon_PS',
    # 'bat_flow',
    # 'bat_flow_PS',
    # 'bat_flow_cap',
    # 'bat_flow_cap_PS',
    'dsm',
    'H2store',
    'H2tank',
    'H2LRC',
    'RO_imp',
    'TTES_HP',
    'PTES_M_HP',
    'PTES_L_HP',
    'BTES_HP',
    'HP',
    'HP_S',
    'HP_M',
    'HP_L',
    'EB',
    'HOB_wa_L',
    'HOB_wa_M',
    'HOB_bio',
    'HOB_bio_S',
    'HOB_bio_M',
    'HOB_bio_L',
    'HOB_H_S',
    'HOB_H_M',
    'HOB_H_L',
    'HOB_G',
    'HOB_WG',
    'HOB_oil',
    'GF',
    'GF_H2',
    'GF_el',
    'GF_H2el',
    'H2heat',
    'solarheat',
    'PTES_L_EB',
    'PTES_M_EB',
    'TTES_HX_EB',
    'TTES_EB']
tech_names = {'RO': 'Hydro', 'U': 'Nuclear', 'CHP_wa': 'Waste CHP', 'CHP_bio': 'Woodchip CHP', 'CHP_WG_L': 'Biogas CHP',
              "bat_discharge": "Battery (dis)charge",
              'GWGCCS': 'Gas-mix CCS', 'WG': 'Biogas CCGT', 'WG_peak': 'Biogas GT', 'wind_offshore': 'Offshore wind',
              "flywheel": "Flywheel", "bat": "Battery", "sync_cond": "Sync. Cond.",
              'wind_onshore': 'Onshore wind', 'PV_cSiOPT': 'Solar PV', 'EB': 'EB', 'HP': 'HP', 'HOB_WG': 'Biogas HOB',
              'HOB_bio': 'Woodchip HOB', 'solarheat': 'Solar heating', "curtailment": "Curtailment",
              'Load': 'Load', 'bat_PS': "Battery (PS)", 'bat_cap_PS': "Battery cap (PS)"}
scen_names = {"_pre": "Base case", "_leanOR": "Lean OR", "_OR": "OR", "_OR_fixed": "OR", "_OR_inertia": "OR + Inertia",
              "_OR+inertia_fixed": "OR + Inertia", "_inertia": "Inertia", "_inertia_2x": "2x Inertia",
              "_inertia_noSyn": "Inertia (noSyn)", "_OR_inertia_3xCost": "OR + Inertia (3x)",
              "_inertia_3xCost": "Inertia (3x)", "_inertia_noSyn_3xCost": "Inertia (noSyn) (3x)"}
color_dict = {'wind_onshore': '#B9B9B9', 'wind_offshore': '#DADADA', 'RO': 'xkcd:ocean blue', 'U': 'xkcd:grape',
              'GWGCCS': 'xkcd:dark peach', 'CHP_wa': 'xkcd:deep lavender', 'CHP_bio': 'xkcd:tree green',
              'WG': 'xkcd:pea', 'WG_peak': 'xkcd:red', 'PV_cSiOPT': 'xkcd:mustard', 'CHP_WG_L': 'xkcd:mid green',
              'HP': (255 / 255, 192 / 255, 0), 'EB': (91 / 255, 155 / 255, 213 / 255),
              'CHP_WG': (0, 176 / 255, 80 / 255),
              'HOB_WG': (128 / 255, 128 / 255, 0), 'solarheat': (204 / 255, 51 / 255, 0), 'HOB_bio': 'green',
              'Load': 'Black', "bat_discharge": "xkcd:amber", 'bat': "xkcd:deep lavender",
              'bat_PS': "xkcd:deep lavender",
              'bat_cap_PS': "xkcd:deep lavender", "sync_cond": 'xkcd:aqua', "curtailment": "xkcd:slate"}


# print(order[2])
# pickle.dump( order, open( "tech_order.pickle", "wb" ) )
# pickle.dump( TECH, open( "TECH.pickle", "wb" ) )
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
    return None
