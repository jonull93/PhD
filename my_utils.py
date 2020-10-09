import pickle  # for dumping and loading variable to/from file
from enum import Enum


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
# print(order[2])
# pickle.dump( order, open( "tech_order.pickle", "wb" ) )
# pickle.dump( TECH, open( "TECH.pickle", "wb" ) )
