import pandas as pd
import os
if __name__ == "__main__":
    import multiprocessing
    import time

    # profile_analysis is now a lot faster, so skipping it is not necessary anymore
    #ask user whether to start from the beginning or from a specific step
    #print("Press enter to start from the beginning")
    #print("Enter a number between 1-3 to start at that step:")
    #print("1. Start at profile analysis")
    #print("2. Start at figure generation")
    #print("3. Start at fingerprint matching")
    #choice = input("Enter your choice: ")
    choice = 1

    sheets = pd.ExcelFile("input\\cap_ref.xlsx").sheet_names
    # make sheet_name the name of the sheet that starts with "ref" and has the highest number after it
    sheet_name = "ref" + str(max([int(i[3:]) for i in sheets if i.startswith("ref")]))
    ref_folder = sheet_name
    # This is the latest ref_folder from the cap_ref.xlsx file
    print("The latest ref  in ref_cap.xlsx is: " + ref_folder)

    ref_folders = []
    for folder in os.listdir("PickleJar"):
        if folder.startswith("ref"):
            ref_folders.append(folder)
    ref_folders.sort(key=lambda x: int(x[3:]))
    ref_folder = ref_folders[-1]
    print("The latest ref in the PickleJar is: " + ref_folder)
    # ask the user for the ref_folder to use
    ref_folder_input = input("Enter the ref_folder to use: ")
    if ref_folder_input == "":
        ref_folder = ref_folder
        #elif numerical
    elif ref_folder_input.isnumeric():
        ref_folder = "ref" + ref_folder_input
    else:
        ref_folder = ref_folder_input


    if choice == "":
        choice = 1
    else:
        choice = int(choice)
    if choice == 1:
        print("Starting at profile analysis")
    elif choice == 2:
        print("Starting at figure generation")
    elif choice == 3:
        print("Starting at fingerprint matching")
    else:
        print("Invalid choice")
        exit()

    #Step 1
    if choice==1: 
        import profile_analysis
        all_cap, VRE_groups, VRE_tech, VRE_tech_dict, VRE_tech_name_dict, years, reseamed_years, sites, region_name, \
            regions, non_traditional_load, filenames, profile_keys, capacity_keys, fig_path, pickle_path, electrified_heat_demand \
            = profile_analysis.initiate_parameters(sheet_name)
        profile_analysis.separate_years(years, VRE_tech, VRE_tech_name_dict, filenames, profile_keys, capacity_keys,
                                        fig_path, regions, VRE_groups, sites, non_traditional_load, electrified_heat_demand,
                                        pickle_path, make_profiles=False, make_figure=True)
        profile_analysis.combined_years(years, VRE_tech, VRE_tech_name_dict, filenames, profile_keys, regions,
                   VRE_groups, sites, non_traditional_load, electrified_heat_demand, pickle_path,)
        #combined_years(range(1980,1982))
        profile_analysis.remake_profile_seam(make_profiles=False)
        #plot_reseamed_years(range(1980,2020))


    #Step 2
    if choice<=2:
        import figure_CFD
        multiprocessing.freeze_support()
        #profile_analysis.initiate()
        figure_CFD.initiate(ref_folder)
        time.sleep(3)
    # run the julia script by using the following powershell command: julia --threads 60 fingerprintmatching.jl
    #Step 3
    if choice<=3:
        print("Better to run confirm the CFD plots and then run julia from the terminal..")
        exit()
        import subprocess
        script_path = "fingerprintmatching.jl"
        command = ["julia", "--threads", "60", script_path]

        try:
            subprocess.run(command, check=True)
            print("Julia script executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running the Julia script: {e}")