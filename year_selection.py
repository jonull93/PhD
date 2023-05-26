if __name__ == "__main__":
    import multiprocessing
    import time

    #ask user whether to start from the beginning or from a specific step
    print("Press enter to start from the beginning")
    print("Enter a number between 1-3 to start at that step:")
    print("1. Start at profile analysis")
    print("2. Start at figure generation")
    print("3. Start at fingerprint matching")
    choice = input("Enter your choice: ")
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
    if choice==1: import profile_analysis

    #Step 2
    if choice<=2:
        import figure_CFD
        multiprocessing.freeze_support()
        #profile_analysis.initiate()
        figure_CFD.initiate()
        time.sleep(3)
    # run the julia script by using the following powershell command: julia --threads 60 fingerprintmatching.jl
    #Step 3
    if choice<=3:
        import subprocess
        script_path = "fingerprintmatching.jl"
        command = ["julia", "--threads", "60", script_path]

        try:
            subprocess.run(command, check=True)
            print("Julia script executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running the Julia script: {e}")