baseload = ['U', "Nuclear", 'B', 'H', 'W']
baseload = baseload + [i.lower() for i in baseload]
CCS = ['BCCS', 'HCCS', 'GCCS', 'BWCCS', 'BECCS', 'HWCCS', 'WGCCS', 'GWGCCS', ]
CHP = ['WA_CHP', 'B_CHP', 'W_CHP', 'H_CHP', 'G_CHP', 'WG_CHP', "CHP"]
midload = ['G', ]
peak = ['G_peak', 'WG', 'WG_PS', 'WG_peak']
thermals = baseload + CCS + CHP + midload + peak + ["Fossil thermals", "Bio thermals", "Thermals"]
wind = ["Wind", 'WOFF', 'WON', 'wind_onshore', 'wind_offshore', ] + ["WON" + ab + str(dig) for ab in ["A", "B"] for dig
                                                                     in range(5, 0, -1)]
PV = ["PVPA1", "PVPB1", "PVR1", "PV", "Solar PV"]
VRE = wind + PV + ["RR"]
H2 = ['electrolyser', 'H2store', 'FC', "H2"]
PtH = ['HP', 'EB', 'PtH']
bat = ['bat', 'bat_cap', "Battery"]
PS = ["flywheel", "sync_cond", "super_cap"]

order_cap = ['RO', "Hydro"] + thermals + VRE + H2 + bat + PS + PtH
