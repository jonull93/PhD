function print_results(optresults, combos, params)
    (; start_time, ref_folder, maxtime, years, years_to_optimize, years_per_set, sum_func, BBO_algs, extreme_years) = params
    (; all_combinations) = combos
    (; global_best, global_midpoint_tracker, best_errors, best_weights, best_alg, opt_func_str, average_time_to_solve_per_thread) = optresults

    println('\a') #beep
    sleep(1)
    #if global_midpoint_tracker is larger than 0, print it and say how many % higher it is than the global best
    if global_midpoint_tracker > 0
        printstyled("global_midpoint_tracker = $(round(global_midpoint_tracker,digits=2)) ($(round(global_midpoint_tracker/global_best*100-100))% higher than global_best)\n"; color=:yellow)
        printstyled("This indicates that the threshold for skipping non-midpoints should be a bit higher than $(round(global_midpoint_tracker/global_best*100))% for $years_to_optimize years and $sum_func\n"; color=:yellow)
    end
    println('\a') #beep

    for comb in all_combinations
        #if comb not in best_errors
        if !(comb in keys(best_errors))
            best_errors[comb] = Inf
            best_weights[comb] = zeros(length(comb))
            best_alg[comb] = "none"
        end
        #if the length of comb is longer than best_weights[comb], add 1/40 to the start of best_weights[comb]
        if length(comb) > length(best_weights[comb])
            best_weights[comb] = vcat([1/40 for i in 1:length(comb)-length(best_weights[comb])],best_weights[comb])
        end
    end
    # sum finc should be the text in opt_func_str before the first +
    sum_func = split(opt_func_str, "(")[1]

    # Find the 3 best combinations (lowest SSE), print their SSE and weights

    #format elapsed time as HH:MM:SS
    elapsed_milliseconds = Dates.value(now()-start_time)
    # Convert to HH:MM:SS
    hours, rem = divrem(elapsed_milliseconds, 3600000)   # Milliseconds in an hour
    minutes, rem = divrem(rem, 60000)                    # Milliseconds in a minute
    seconds = rem ÷ 1000                                 # Milliseconds in a second
    # Format as string
    formatted_time = string(lpad(hours, 2, '0'), ":", lpad(minutes, 2, '0'), ":", lpad(seconds, 2, '0'))

    println("Done optimizing all combinations for $ref_folder at $(Dates.format(now(), "HH:MM:SS")) after $(formatted_time), spending $(round(mean(average_time_to_solve_per_thread),digits=2)) s per case on average")
    printstyled("The 3 best combinations are ($(years[1])-$(years[end])) [sum_func=$(sum_func)()]:\n", color=:cyan)
    println("$(length(best_errors)) items evaluated, $(length(all_combinations)-length(best_errors)) items skipped (should be 0)")
    sorted_cases = sort(collect(best_errors), by=x->x[2])
    all_combinations = sort(collect(all_combinations), by=x->best_errors[x])
    try
        for (case, error) in sorted_cases[1:3]
            printstyled("$(case) with $sum_func error $(round(error,digits=1))\n", color=:green)
            println("weights: $(round.(best_weights[case],digits=3)) (sum: $(round(sum(best_weights[case]),digits=3)))")
            # print each item in the case and its respective weight
        end
        #sort all_combinations by its value in the dictionary best_errors
    catch e
        printstyled("!Error: $(e)\n", color=:red)
    end
    # Save the results as a .json file
    timestamp = Dates.format(start_time, "udd HH.MM.SS")
    folder_name = "results\\$ref_folder/FP $sum_func $timestamp $(years_per_set)yr $(length(extreme_years))eyrs"
    mkpath(folder_name)

    results = Dict("combinations" => all_combinations, "best_weights" => best_weights,
        "best_errors" => best_errors, "opt_func" => opt_func_str, "sum_func" => sum_func,
        "maxtime" => maxtime, "best_alg" => best_alg)

    #Create a file named after the range years
    years_filename = joinpath(folder_name, "$(minimum(years)) to $(maximum(years))")
    open(years_filename, "w") do f
        write(f, "")# You can write any content related to the years range here if needed
    end
    #Create a file named after the best case
    best_case_filename = joinpath(folder_name, "Best= $(join(sorted_cases[1][1], ","))")
    open(best_case_filename, "w") do f
        write(f, "")# You can write any content related to the best case here if needed
    end
    #Create a file named after the maxtime
    maxtime_filename = joinpath(folder_name, "Maxtime= $maxtime")
    open(maxtime_filename, "w") do f
        write(f, "")# You can write any content related to the maxtime here if needed
    end

    open(joinpath(folder_name, "results.json"), "w") do f
        write(f, JSON.json(results))
    end

    parameters = Dict("maxtime" => maxtime, "opt_func" => opt_func_str, "BBO_algs" => BBO_algs)
    parameters_json = JSON.json(parameters)

    open(joinpath(folder_name, "parameters.txt"), "w") do f
        write(f, parameters_json)
    end

    #make three jsons containing the best 5, 25 and 50 combinations as an array of array of strings [ ["1980-1981", "1981-1982", "1982-1983"], ["1980-1981", "1981-1982", "1982-1983"]  ..]
    best_5 = best_25 = best_50 = []
    if length(sorted_cases) >= 5
        best_5 = [sorted_cases[i][1] for i in 1:5]
        open(joinpath(folder_name, "best_5.json"), "w") do f
            write(f, JSON.json(best_5))
        end
    end
    if length(sorted_cases) >= 25
        best_25 = [sorted_cases[i][1] for i in 1:25]
        open(joinpath(folder_name, "best_25.json"), "w") do f
            write(f, JSON.json(best_25))
        end
    end
    if length(sorted_cases) >= 50
        best_50 = [sorted_cases[i][1] for i in 1:50]
        open(joinpath(folder_name, "best_50.json"), "w") do f
            write(f, JSON.json(best_50))
        end
    end
    
    #=using XLSX
    XLSX.openxlsx(joinpath(folder_name, "results $sum_func $timestamp.xlsx"), mode="w") do xf
        sheet = xf[1] # Add sheet
        XLSX.rename!(sheet, "Results $maxtime s") # Rename sheet

        # Step 6.3: Write the headers for the columns
        headers = ["Error", "Year 1", "Year 2", "Year 3", "W1", "W2", "W3", "Algorithm"]
        sheet["A1",dim=2] = headers

        # Step 6.4: Iterate through the combinations and write the results to the worksheet
        for i in 1:length(all_combinations)
            combination = all_combinations[i]
            error = best_errors[combination]
            weight = best_weights[combination]
            alg = best_alg[combination]
            row = i + 1
            sheet["A$row"] = error
            sheet["B$row"] = combination[1]
            sheet["C$row"] = combination[2]
            sheet["D$row"] = combination[3]
            sheet["E$row"] = weight[1]
            sheet["F$row"] = weight[2]
            sheet["G$row"] = weight[3]
            sheet["H$row"] = string(alg)
        end
    end=#
    XLSX.openxlsx(joinpath(folder_name, "results $sum_func $timestamp.xlsx"), mode="w") do xf
        sheet = xf[1] # Add sheet
        XLSX.rename!(sheet, "Results $maxtime s") # Rename sheet

        # Step 6.3: Write the headers for the columns
        n = years_per_set # Assuming all_combinations is non-empty
        year_headers = ["Year $i" for i in 1:n]
        weight_headers = ["W$i" for i in 1:n]
        headers = vcat(["Error"], year_headers, weight_headers, ["Algorithm"])
        sheet["A1", dim=2] = headers

        # Step 6.4: Iterate through the combinations and write the results to the worksheet
        for i in 1:length(all_combinations)
            if i>1e6
                break # excel can't handle too many rows " LoadError: AssertionError: A1048577 is not a valid CellRef."
            end
            combination = all_combinations[i]
            error = best_errors[combination]
            weight = best_weights[combination]
            #if combination is longer than weight, add 0.025 to the start of weight until it is the same length as combination
            while length(weight) < length(combination)
                weight = vcat([0.025], weight)
            end
            alg = best_alg[combination]
            row = i + 1
            sheet["A$row"] = error
            for j in 1:n
                sheet["$(Char('A' + j))$row"] = combination[j]
            end
            for j in 1:n
                sheet["$(Char('A' + n + j))$row"] = weight[j]
            end
            sheet["$(Char('A' + 2 * n + 1))$row"] = string(alg)
        end
    end



    #=using XLSX
    XLSX.openxlsx(joinpath(folder_name, "results $timestamp.xlsx"), mode="w") do xf
        sheet = xf[1] # Add sheet
        XLSX.rename!(sheet, "Results $maxtime s") # Rename sheet

        # Step 6.3: Write the headers for the columns
        headers = ["Combination", "Error", "Weights", "Algorithm"]
        sheet["A1", dim=2] = headers

        # Step 6.4: Iterate through the combinations and write the results to the worksheet
        for i in 1:length(all_combinations)
            combination = all_combinations[i]
            error = best_errors[combination]
            weight = best_weights[combination]
            alg = best_alg[combination]
            row = i + 1
            sheet["A$row"] = join(combination, ", ")
            sheet["B$row"] = error
            sheet["C$row"] = join(round.(weight,digits=3), ", ")
            sheet["D$row"] = string(alg)
        end
    end
    =#

    # Update the most recent results file
    open("results\\$ref_folder/most_recent_results.txt", "w") do f
        write(f, folder_name)
    end

    # Call Script 1 from Script 2
    #see if any one the following files exist:
    #C:/Users/jonathan/.conda/envs/py311/python.exe
    #C:/Users/jonull/.conda/envs/py311/python.exe
    for path in ["C:/Users/jonathan/.conda/envs/py311/python.exe", "C:/Users/jonull/.conda/envs/py311/python.exe"]
        if isfile(path)
            println("To make figures of these results, run `$(path) figure_cfd.py`")
            break
        end
    end

end
