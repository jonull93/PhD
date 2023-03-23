#=
fingerprintmatching:
- Julia version: 
- Author: Jonathan
- Date: 2023-01-18
=#
import Combinatorics: combinations
using MAT
using Optim
using BlackBoxOptim
using DataStructures
using Dates
using Printf
using LinearAlgebra
using Plots

#make it clear in the command prompt that the code is running
timestamp = Dates.format(now(), "u_dd_HH.MM.SS")
printstyled("\n ############# -- Starting fingerprintmatching.jl at $(timestamp) -- ############# \n"; color=:yellow)
const print_lock = ReentrantLock()

#set parameters
amplitude_resolution = 1
window = 12
years = 1980:1985#:2018
most_interesting_years = ["2010-2011","2002-2003",]
maxtime = 300
algs_size = "small" # "small" or "large" or "single"

years_list = map(x -> string(x, "-", x+1), years)
years_list = vcat(years_list,[i for i in most_interesting_years if !(i in years_list)])
println("Years: $(years_list)")
println("Number of years: $(length(years_list))")

# Load mat data
total_year = "1980-2019"
ref_full = matread("input\\heatmap_values_$(total_year)_amp$(amplitude_resolution)_area.mat")
ref_mat = ref_full["recurrance"]
ref_y = ref_full["duration"][:,1]
ref_x = ref_full["amplitude"][1,:]
printstyled("Imported total matrix $(size(ref_mat)) for $(total_year) \n"; color=:green)

ref_mat[isnan.(ref_mat)].= 0
cfd_data = Dict()
y_data = Dict()
x_data = Dict()
for year in years_list
    filename = "output\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area_padded.mat"
    filename2 = "output\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area.mat"
    filename3 = "input\\heatmap_values_$(year)_amp$(amplitude_resolution)_area.mat"
    try
        global temp = matread(filename)
    catch e
        try
            global temp = matread(filename2)
        catch e
            try
                global temp = matread(filename3)
            catch e
                error("Could not find file for $(year)")
            end
        end
    end
    #=try
        global temp = matread(filename)
    catch e
        filename = "output\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area.mat"
        global temp = matread(filename)
    end=#
    cfd_data[year] = replace(temp["recurrance"], NaN => 0)
    #take [:,1]or [1,:]if ndims==2 otherwise just take the whole thing
    y_data[year] = getindex(temp["duration"], :, 1)
    x_data[year] = getindex(temp["amplitude"], 1, :)
    if size(cfd_data[year]) == size(ref_mat)
        #println("Matrix for $(year) is already the same size as the reference matrix")
        continue
    end
    if length(findall(in(x_data[year]),ref_x))<length(x_data[year]); error("Non-matching x-axes"); end
    printstyled("Padding the matrix $(size(cfd_data[year])) for $(year) ..\n"; color=:green)
    columns_to_add = count(x -> x > maximum(x_data[year]), ref_x)
    println("Adding $(columns_to_add) columns")
    #end_columns = count(x -> x > maximum(x_data[year]), ref_x)
    xpad = zeros((size(cfd_data[year])[1],columns_to_add))
    #xpad2 = zeros((size(cfd_data[year])[2],end_columns))
    cfd_data[year] = hcat(cfd_data[year],xpad)
    #println("Added columns - new size is $(size(cfd_data[year]))")
    start_rows = count(y -> y < minimum(y_data[year]), ref_y)
    end_columns = count(y -> y > maximum(y_data[year]), ref_y)
    println("Adding $(start_rows) rows at the top and $(end_columns) rows at the bottom")
    ypad1 = zeros((start_rows,size(cfd_data[year])[2]))
    ypad2 = zeros((end_columns,size(cfd_data[year])[2]))
    cfd_data[year] = vcat(ypad1,cfd_data[year],ypad2)
    # doublecheck that the dims of cfd_data[year] are the same as ref_mat
    if size(cfd_data[year]) != size(ref_mat)
        error("The dimensions of the matrix for $(year) are not the same as the reference matrix")
    end
    # save padded mat to filename but replace .mat with _padded.mat
    matwrite("output\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area_padded.mat",
        Dict("recurrance" => cfd_data[year], "duration" => ref_y, "amplitude" => ref_x),
        compress=true)
end

# Generate combinations of years to optimize match for
year_combinations = Dict()
final_SSE = Dict()
weights = Dict()
queue = Queue{Any}()
cores = Threads.nthreads()
all_combinations = []
for interesting_year in most_interesting_years
    #printstyled("Starting optimization that include year $(interesting_year)\n"; color=:cyan)
    year_combinations[interesting_year] = combinations(filter(!=(interesting_year),years_list), 2)  # a generator instead of a list until collect() is used
    for combination in year_combinations[interesting_year]
        case = [interesting_year,combination[1],combination[2]]
        enqueue!(queue,case)
        push!(all_combinations,case)
    end
end
#dequeue!(queue)  # remove the first element
#dequeue!(queue)  # remove the second element
#print number of all_combinations
println("Number of combinations: $(length(queue))")
printstyled("At around 1 min per combination, this will take $(round(length(queue)/60)) hours\n"; color=:green)
printstyled("At around 8 min per combination and $(cores) cores this will take $(round(length(queue)*8/60/min(length(queue),cores),sigdigits=2)) hours with multi-threading\n"; color=:green)
#printstyled("At around 25 s per combination, this will take $(round(length(queue)*25/60)) minutes\n"; color=:green)
#printstyled("At around 25 s per combination and $(cores) cores, this will take $(round(length(queue)*25/60/min(length(queue),cores),sigdigits=2)) minutes with multi-threading\n"; color=:green)
scaled_ref_mat = ref_mat ./ 40
function sigmoid(x)
    return 1 / (1 + exp(-x))
end

function diff_sum_weighted_mats(matrices,weights)
    m_sum = sum(wi * mi for (wi, mi) in zip(weights, matrices))
    diff = m_sum - scaled_ref_mat
    return diff
end

function diff_sum_weighted_mats_boxed(matrices,weights)
    m_sum = sum(wi * mi for (wi, mi) in zip(weights, matrices))
    diff = m_sum - scaled_ref_mat
    # if any weight is lower than 0, return a large diff
    if any(weights .< 0)
        diff = diff .+ 1000
    end
    #if any(weights .> 1)
    #    diff = diff .+ 1000
    #end
    #if the sum of weights are larger than 1 or smaller than 0.99, return a large diff
    if sum(weights) < 0.999 || sum(weights) > 1
        diff = diff .+ 1000
        nothing
    end
    return diff
end
printstyled("Starting test sum_weighted_mats\n"; color=:cyan)
# pick any three years, 1/3 weights and plot a heatmap of diff_sum_weighted_mats
test_weights = [1,1/3,1/3]
x = length(queue)
test_years = collect(Iterators.take(queue, 1))[1]
if length(queue) != x
    error("Queue was modified")
end
#print test_years and each element in test_years
println("test_years: $(test_years)")
for year in test_years
    println("$(year): $(size(cfd_data[year]))")
end
test_matrices = [cfd_data[year] for year in test_years]
test_diff = diff_sum_weighted_mats(test_matrices,test_weights)'
test_diff = replace(test_diff, 0 => NaN)
# transpose test_diff to get the correct orientation
#test_diff = test_diff'
#print size of test_diff
println("test_diff: $(size(test_diff))")
#println(test_diff[1500,:])
#print sum of error
println("sum of error (ignoring NaN): $(round(sum(abs.(test_diff[.!isnan.(test_diff)]))))")
println("sum of log10(error) (ignoring NaN): $(round(sum(log10.(abs.(test_diff[.!isnan.(test_diff)])))))")
println("sum of square root error (ignoring NaN): $(round(sum(sqrt.(abs.(test_diff[.!isnan.(test_diff)])))))")
println("sum of squared error (ignoring NaN): $(round(sum(abs.(test_diff[.!isnan.(test_diff)]).^2)))")

function apply_error_func(m)
    m = replace(m, 0 => NaN)
    m = abs.(m)
    m = log10.(m)
    return m
end
#h = heatmap(apply_error_func(test_diff), title="Difference between weighted sum of matrices and reference matrix", xlabel="Amplitude", ylabel="Duration", color=:viridis, colorbar=true)
#gui(h)
#readline()
printstyled("Finished test sum_weighted_mats\n"; color=:cyan)
println("Starting $(min(length(queue),cores)) threads (use ´julia --threads $(Sys.CPU_THREADS) script_name.jl´ to use max cores)") # returns "Starting 63 threads"

best_weights = Dict()
best_errors = Dict()
best_alg = Dict()
BBO_algs_large = [:generating_set_search,
:adaptive_de_rand_1_bin_radiuslimited,
:simulated_annealing,
:probabilistic_descent,
:pso,
:adaptive_de_rand_1_bin,
:dxnes,
]
BBO_algs_small = [:pso,
:adaptive_de_rand_1_bin,
:probabilistic_descent,]
BBO_algs_single = [:pso]
BBO_algs = eval(Meta.parse("BBO_algs_$(algs_size)"))
longest_alg_name = maximum([length(string(alg)) for alg in BBO_algs])
#print, in yellow and with ######-separation, the maxtime and algs that the loop is ran with
global_best = 9e9
printstyled("############# -- Starting optimization loop with maxtime=$(maxtime)s and algs_size '$(algs_size)' -- #############\n"; color=:yellow)
Threads.@threads for thread = 1:min(length(queue),cores)
    #sleep for 250 ms to stagger thread starts
    sleep(0.1)
    global global_best
    while true
        if length(queue) == 0
            #println("Nothing to do")
            break
        end
        case = dequeue!(queue)
        start_time = Dates.now()
        printstyled("Thread $(thread) started working on $(case) at $(Dates.format(now(), "HH:MM:SS") )\n"; color=:cyan)
        matrices = [cfd_data[year] for year in case]
        # Use an optimization algorithm to find the best weights
        function sse(x)
           diff = diff_sum_weighted_mats(matrices,x)
           return dot(diff,diff)
        end
        function abs_sum(x)
           diff = diff_sum_weighted_mats(matrices,x)
           return sum(abs.(diff))
        end
        function sqrt_sum(x)
           diff = diff_sum_weighted_mats(matrices,x)
           return sum(sqrt.(abs.(diff)))
        end
        function log_sum(x)
           diff = diff_sum_weighted_mats(matrices,x)
           diff = replace(diff, 0 => NaN)
           e = abs.(log10.(abs.(diff)))
           # return sum of e but ignoring NaN
           #penalty = sigmoid((sum(x)-1.011)*1000)+sigmoid((0.989-sum(x))*1000)
           return sum(e[.!isnan.(e)])#+penalty*100000
        end
        function log_sum2(x)
           diff = diff_sum_weighted_mats_boxed(matrices,x)
           diff = replace(diff, 0 => NaN)
           e = abs.(log10.(abs.(diff)))
           # return sum of e but ignoring NaN
           return sum(e[.!isnan.(e)])
        end
        # a vector w that is the same length as the number of matrices and equals 1/number of matrices
        w = ones(length(matrices)) ./ length(matrices)
        upper = ones(length(matrices))
        lower = zeros(length(matrices))
        ###----------------------------
        ### SET THE ERROR FUNCTION TO OPTIMIZE WITH HERE
        ###----------------------------
        global opt_func_str = "sqrt_sum(x) + (sigmoid((sum(x)-1.011)*1000) + sigmoid((0.989-sum(x))*1000))*100000"
        opt_func(x) = sqrt_sum(x) + (sigmoid((sum(x)-1.011)*1000) + sigmoid((0.989-sum(x))*1000))*100000
        extreme_guesses = [[1,0,0], [0,1,0], [0,0,1]]
        extreme_guesses_one_normal = [
            [1-1/40, 1/40, 0], [1-1/40, 0, 1/40],
            [0, 1-1/40, 1/40], [1/40, 1-1/40, 0],
            [1/40, 0, 1-1/40], [0, 1/40, 1-1/40]]
        local guesses = [w, [0.4194, 0, 0.5806]]
        for guess in extreme_guesses
            push!(guesses, guess)
        end
        for guess in extreme_guesses_one_normal
            push!(guesses, guess)
        end
        local alg_solutions = Dict()
        for alg in BBO_algs
            #print the next line only tif thread==1
            if thread == 1
                printstyled("Trying $(alg)..\n"; color=:cyan)
            end
            local res = bboptimize(opt_func, guesses; method=alg, NumDimensions=length(w),
                                    SearchRange=(0,1), MaxTime=maxtime, TraceInterval=2, TraceMode=:silent) #TargetFitness=88355.583298,FitnessTolerance=0.0001
            local weights_list = best_candidate(res)
            local e = opt_func(weights_list)
            #PRINT THE ERROR AND WEIGHTS
            #printstyled("years: $(case)\n"; color=:green)
            #printstyled("alg: $(alg)\n"; color=:green)
            #printstyled("error: $(round.(e,digits=5)), weights: $(round.(weights_list,digits=3))\n"; color=:green)
            alg_solutions[alg] = (e, weights_list)
        end
        _best_alg = BBO_algs[argmin([alg_solutions[alg][1] for alg in BBO_algs])]
        best_errors[case] = alg_solutions[_best_alg][1]
        best_weights[case] = alg_solutions[_best_alg][2]
        best_alg[case] = _best_alg

        #print each alg's solution
        lock(print_lock) do
            if alg_solutions[_best_alg][1] < global_best
                printstyled("years: $(case)"; color=:green)
                printstyled("       <-- best so far\n"; color=:red)
                global_best = best_errors[case]
            else
                printstyled("years: $(case)\n"; color=:green)
            end
            # find for which alg the error is the lowest
            for alg in BBO_algs
                #change the following line so that the printed length of algs of different lengths is the same
                #printstyled("$(rpad(string(alg),longest_alg_name+1)) error: $(round.(alg_solutions[alg][1],digits=3)), weights: $(round.(alg_solutions[alg][2],digits=3))\n"; color=:white)
                print("$(round(alg_solutions[alg][1],digits=3)) $(round.(alg_solutions[alg][2],digits=3)) $(alg)")
                if alg == _best_alg
                    printstyled(" <-\n"; color=:green)
                else
                    print("\n")
                end
                #@sprintf("%20i-30s error: %10.5f, weights: %s\n", rpad(string(alg)), alg_solutions[alg][1], round.(alg_solutions[alg][2],digits=3))

            end
        end
        #if case not in best_errors
        if !(case in keys(best_errors))
            best_errors[case] = alg_solutions[_best_alg][1]
            best_weights[case] = alg_solutions[_best_alg][2]
            best_alg[case] = _best_alg
        end
    end
end

# Find the 3 best combinations (lowest SSE), print their SSE and weights
println("Done optimizing all combinations! :)")
printstyled("The 3 best combinations are:\n", color=:cyan)
sorted_cases = sort(collect(best_errors), by=x->x[2])
for (case, error) in sorted_cases[1:3]
    printstyled("$(case) with error $(round(error,digits=1))\n", color=:green)
    println("weights: $(round.(best_weights[case],digits=3))")
    # print each item in the case and its respective weight
end
#sort all_combinations by its value in the dictionary best_errors
all_combinations = sort(collect(all_combinations), by=x->best_errors[x])

# Save the results as a .json file
using JSON

results = Dict("combinations" => all_combinations, "best_weights" => best_weights,
    "best_errors" => best_errors, "opt_func" => opt_func_str,
    maxtime => maxtime, "best_alg" => best_alg)
# sum finc should be the text in opt_func_str before the first +
sum_func = split(opt_func_str, "(")[1]
folder_name = "results/FP $sum_func $timestamp"
mkpath(folder_name)

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

open(joinpath(folder_name, "results.json"), "w") do f
    write(f, JSON.json(results))
end

parameters = Dict("maxtime" => maxtime, "opt_func" => opt_func_str, "BBO_algs" => BBO_algs)
parameters_json = JSON.json(parameters)

open(joinpath(folder_name, "parameters.txt"), "w") do f
    write(f, parameters_json)
end

using XLSX
XLSX.openxlsx(joinpath(folder_name, "results$timestamp.xlsx"), mode="w") do xf
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


# Update the most recent results file
open("results/most_recent_results.txt", "w") do f
    write(f, folder_name)
end

# Call Script 1 from Script 2
#run(`python figure_cfd.py`)
