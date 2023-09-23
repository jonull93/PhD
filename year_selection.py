import pandas as pd
import os
from my_utils import completion_sound, print_magenta
import time 
import winsound
import multiprocessing
from halfstepped_ref_sheet import load_data, calculate_mean_cap, append_to_capref, ask_for_refname

if __name__ == "__main__":

    sheets = pd.ExcelFile("input\\cap_ref.xlsx").sheet_names
    # make sheet_name the name of the left-most sheet that starts with "ref"
    sheet_name = [sheet for sheet in sheets if sheet.startswith("ref")][0]
    ref_folder = sheet_name
    print("The latest ref in ref_cap.xlsx is: " + ref_folder)

    ref_folders = []
    for folder in os.listdir("PickleJar"):
        if folder.startswith("ref"):
            ref_folders.append(folder)
    # pick the ref_folder that was most recently modified
    ref_folders.sort(key=lambda x: os.path.getmtime(os.path.join("PickleJar", x)))
    ref_folder = ref_folders[-1]
    print("The latest ref in the PickleJar is: " + ref_folder)
    
    #ask the user whether to use halfstepped (avg of two latest) or fullstepped (only most recent) capacities
    while True:
        halfstepped = input("Use halfstepped capacities? (y/n): ")
        if halfstepped.lower() == "y" or halfstepped.lower() == "yes":
            ref1, ref2, ref3, my_sheetname = ask_for_refname()
            data = load_data(ref1, ref2, ref3)
            avg_capacity = calculate_mean_cap(data)
            append_to_capref(avg_capacity, my_sheetname)
            print("Added sheet " + my_sheetname + " to cap_ref.xlsx")
            #else: use the most recent ref_folder
            ref_folder = my_sheetname
            print("Setting ref_folder to: " + ref_folder)
            break
        elif halfstepped.lower() == "n" or halfstepped.lower() == "no":
            # ask the user for the ref_folder to use
            ref_folder_input = input("Enter the ref_folder to use: ")
            if ref_folder_input == "":
                ref_folder = ref_folder
                print("Using ref_folder from PickleJar: " + ref_folder)
                #elif numerical
            elif ref_folder_input.isnumeric():
                ref_folder = "ref" + ref_folder_input
                print("Setting ref_folder to: " + ref_folder)
            else:
                ref_folder = ref_folder_input
                print("Setting ref_folder to: " + ref_folder)
            break
        else:
            #print a description of what halfstepped means
            print_magenta("\nHalfstepped capacities means that the capacities are averaged from the two (or three) latest refs in cap_ref.xlsx")
            print_magenta(" This should make the convergence more likely to succeed, but it MIGHT require more interations.\n\n")

    #Step 1
    import profile_analysis
    all_cap, VRE_groups, VRE_tech, VRE_tech_dict, VRE_tech_name_dict, years, reseamed_years, sites, region_name, \
        regions, non_traditional_load, filenames, profile_keys, capacity_keys, fig_path, pickle_path, electrified_heat_demand \
        = profile_analysis.initiate_parameters(ref_folder)
    profile_analysis.separate_years(years, VRE_tech, VRE_tech_name_dict, filenames, profile_keys, capacity_keys,
                                    fig_path, regions, VRE_groups, sites, non_traditional_load, electrified_heat_demand,
                                    pickle_path, make_profiles=False, make_figure=True)
    profile_analysis.combined_years(years, VRE_tech, VRE_tech_name_dict, filenames, profile_keys, regions,
                VRE_groups, sites, non_traditional_load, electrified_heat_demand, pickle_path,)
    #combined_years(range(1980,1982))
    profile_analysis.remake_profile_seam(pickle_path, electrified_heat_demand, non_traditional_load, make_profiles=False)
    #plot_reseamed_years(range(1980,2020))

    #Step 2
    import figure_CFD
    multiprocessing.freeze_support()
    #profile_analysis.initiate()
    figure_CFD.initiate(ref_folder)
    completion_sound()
    time.sleep(3)
