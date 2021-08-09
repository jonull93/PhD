order_gen = [
            'Bat. In',
            'bat_charge',
            'efuel',
            'electrolyser',
            'EB',
            'PTES_L',
            'PTES_L_HX',
            'TTES',
            'PTES_M',
            'PTES_M_HX',
            'TTES_HX',
            'BTES',
            'U',
            'B',
            'b',
            'H',
            'W',
            'WA_CHP',
            'B_CHP',
            'W_CHP',
            'H_CHP',
            'G_CHP',
            'BCCS',
            'HCCS',
            'GCCS',
            'BWCCS',
            'BECCS',
            'HWCCS',
            'HCCS_flex',
            'HWCCS_flex',
            'WGCCS',
            'GWGCCS',
            'WG_CHP',
            'G',
            'WG',
            'WG_PS',
            'WG_peak',
            'G_peak',
            'FC',
            'RO',
            'RO_imp',
            'RR',
            'WOFF',
            'WON',
            'wind_onshore',
            'wind_offshore',
            'WON12', 'WON11', 'WON10', 'WON9', 'WON8', 'WON7', 'WON6', 'WON5', 'WON4', 'WON3', 'WON2', 'WON1'] + \
        ["WON" + ab + str(dig) for ab in ["A", "B"] for dig in range(5, 0, -1)] + \
        ["PVPA1",
         "PVPB1",
         "PVR1",
         'PS',
         'PV',
         'backstop',
         'bat',
         'bat_PS',
         'bat_cap_PS',
         'flywheel',
         'sync_cond',
         'curtailment',
         'H2store',
         'RO_imp',
         'bat_discharge',
         'bat_cap',
         'Bat. Out'
         ]