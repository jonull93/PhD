#=
fingerprintmatching:
- Julia version: 
- Author: Jonathan Ullmark
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
using JSON

#make it clear in the command prompt that the code is running
timestamp = Dates.format(now(), "u_dd_HH.MM.SS")
printstyled("\n ############# -- Starting fingerprintmatching.jl at $(timestamp) -- ############# \n"; color=:yellow)
const print_lock = ReentrantLock()

#set parameters
amplitude_resolution = 1
window = 12
years = 1980:2018 # cannot include 2019
# from years, remove 1985, 1993,1994,1995,1996,1998,2001,2005,2017
if false
    to_remove = [1985, 1993,1994,1995,1996,1998,2001,2005,2017]
    years = [i for i in years if !(i in to_remove)]
    println("Removed years: $(to_remove)")
end
most_interesting_years = ["2005-2006","1989-1990"]#["1989-1990","2005-2006"]#["1984-1985", "1995-1996"]#["2010-2011","2002-2003",]

maxtime = 60*0.5 # 60*30=30 minutes
algs_size = "adaptive" # "small" or "large" or "single" or "adaptive"
years_per_combination = 3
years_to_add = years_per_combination - 1 # number of years to add to the most interesting year for each combination
all_interesting_years_at_once = false
import_combinations = false
optimize_all = false
# ask the user whether to import the 100 best combinations from the previous run
printstyled("
Run is set up with the following parameters:
maxtime = $(maxtime/60) minutes,
algs_size = $(algs_size),
years_per_combination = $(years_per_combination),
most_interesting_years = $(most_interesting_years)
    - Enter 'i' to attempt to import (100 best) combinations from previous run
    - Enter 'a' to make only combinations that include all interesting_years at once
    - Enter 'o' to optimize the weights also for the most interesting years
    - Enter a number to set the max number of minutes for each optimization
    - Enter anything else to skip..\n"; color=:yellow)
input = readline()
if input == "y"
    import_combinations = true
    printstyled("Importing combinations from previous run \n"; color=:green)
elseif input == "a"
    all_interesting_years_at_once = true # if true, use all years in most_interesting_years, if false, use only one at a time
    years_to_add = years_per_combination - length(most_interesting_years)
    printstyled("Using all interesting years at once \n"; color=:green)
elseif tryparse(Float32,input) != nothing
    maxtime = parse(Float32,input)*60
    printstyled("Max time set to $(maxtime/60) minutes \n"; color=:green)
elseif input == "o"
    optimize_all = true
    printstyled("Optimizing weights for all years \n"; color=:green)
else
    printstyled("Skipping\n"; color=:red)
end

years_not_optimized = 0
if !optimize_all
    years_not_optimized = years_per_combination - years_to_add
    printstyled("-- Only optimizing for $years_to_add year(s) -- \n"; color=:red, bold=true)
end

if !optimize_all && years_to_add == 1
    printstyled("There is only one year to optimize, so maxtime will be reduced to 5s and alg set to 'single'\n"; color=:red)
    maxtime = 5
    algs_size = "single"
end


# years_to_add scales insanely with the number of years, so it is not recommended to use more than 2

years_list = map(x -> string(x, "-", x+1), years)
years_list = vcat(years_list,[i for i in most_interesting_years if !(i in years_list)])

# Load mat data
function find_max_ref_folder(parent_directory)
    ref_folders = filter(x -> occursin(r"^ref\d+$", x), readdir(parent_directory))
    isempty(ref_folders) ? nothing : "ref" * string(maximum(parse(Int, replace(x, "ref" => "")) for x in ref_folders))
end

ref_folder = find_max_ref_folder("./output")
println("Reading data from $ref_folder")
total_year = "1980-2019"
ref_full = matread("output\\$ref_folder\\heatmap_values_$(total_year)_amp$(amplitude_resolution)_window$(window)_area.mat")
ref_mat = ref_full["recurrance"]
ref_mat[isnan.(ref_mat)].= 0
ref_y = ref_full["duration"][:,1]
ref_x = ref_full["amplitude"][1,:]
printstyled("\nImported total matrix $(size(ref_mat)) for $(total_year) \n"; color=:green)
#printstyled("Sum of extreme rows: $(sum(ref_mat[1,:])) and $(sum(ref_mat[end,:])) \n"; color=:cyan)
#printstyled("Sum of extreme columns: $(sum(ref_mat[:,1])) and $(sum(ref_mat[:,end])) \n"; color=:cyan)
# load weight matrices to be used with the error func sum_weight_mat, see git\python\figures\weight_matrix#.png for visuals
weight_matrices = matread("output/weight_matrices.mat")
weight_matrix_lin19diff = weight_matrices["Z_lin19diff"]
weight_matrix_lin190diff = weight_matrices["Z_lin190diff"]
weight_matrix_sqrt = weight_matrices["Z_sqrt"]  # min = 1, max = 14

# Generate combinations of years to optimize match for
year_combinations = Dict()
final_SSE = Dict()
weights = Dict()
queue = Queue{Any}()
cores = Threads.nthreads()
all_combinations = []
if import_combinations
    # read folder_name from results/most_recent_results.txt
    folder_name = readlines("results/$ref_folder/most_recent_results.txt")[1]
    # read folder_name/best_100.json, or skip to the else-block if the file does not exist
    if !isfile("$(folder_name)/best_100.json")
        println("File $(folder_name)/best_100.json does not exist, skipping import of combinations")
        @goto skip_import
    end
    best_100 = JSON.parsefile("$(folder_name)/best_100.json")
    # add each item in best_100 to all_combinations and queue
    for item in best_100
        enqueue!(queue,item)
        push!(all_combinations,item)
    end
    # remove all items from years if they are not found in any list in all_combinations
else
    @label skip_import
    printstyled("Building combinations instead of importing! \n"; color=:red)
    println("Years: $(years_list)")
    println("Number of years: $(length(years_list))")

    if all_interesting_years_at_once
        years_to_use = [i for i in years_list if !(i in most_interesting_years)]
        year_combinations = combinations(years_to_use, years_to_add)
        for combination in year_combinations
            case = copy(most_interesting_years)
            append!(case,combination)
            enqueue!(queue,case)
            push!(all_combinations,case)
        end
    else
        for interesting_year in most_interesting_years
            #printstyled("Starting optimization that include year $(interesting_year)\n"; color=:cyan)
            year_combinations[interesting_year] = combinations(filter(!=(interesting_year),years_list), years_to_add)  # a generator instead of a list until collect() is used
            for combination in year_combinations[interesting_year]
                case = [interesting_year]
                append!(case,combination)
                enqueue!(queue,case)
                push!(all_combinations,case)
            end
        end
    end
end

cfd_data = Dict()
y_data = Dict()
x_data = Dict()
for year in years_list
    filename = "output\\$ref_folder\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area_padded.mat"
    filename2 = "output\\$ref_folder\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area.mat"
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
    cfd_data[year] = replace(temp["recurrance"], NaN => 0)
    #take [:,1]or [1,:]if ndims==2 otherwise just take the whole thing
    y_data[year] = getindex(temp["duration"], :, 1)
    x_data[year] = getindex(temp["amplitude"], 1, :)
    if size(cfd_data[year]) == size(ref_mat)
        #println("Matrix for $(year) is already the same size as the reference matrix")
        continue # move on to the next year
    end
    if length(findall(in(x_data[year]),ref_x))<length(x_data[year]); error("Non-matching x-axes"); end
    printstyled("Padding the matrix $(size(cfd_data[year])) for $(year) ..\n"; color=:green)
    columns_to_add = count(x -> x > maximum(x_data[year]), ref_x)
    println("Adding $(columns_to_add) columns")
    xpad = zeros((size(cfd_data[year])[1],columns_to_add))
    cfd_data[year] = hcat(cfd_data[year],xpad)
    #println("Added columns - new size is $(size(cfd_data[year]))")
    start_rows = count(y -> y < minimum(y_data[year]), ref_y)
    end_columns = count(y -> y > maximum(y_data[year]), ref_y)
    println("Adding $(start_rows) rows at the top and $(end_columns) rows at the bottom")
    ypad1 = zeros((start_rows,size(cfd_data[year])[2]))
    ypad2 = zeros((end_columns,size(cfd_data[year])[2]))
    cfd_data[year] = vcat(ypad1,cfd_data[year],ypad2)
    if size(cfd_data[year]) != size(ref_mat)
        #print in red the sizes of cfd_data[year] and ref_mat
        printstyled("size(cfd_data[year]) = $(size(cfd_data[year])) and size(ref_mat) = $(size(ref_mat))\n"; color=:red)
        error("The dimensions of the matrix for $(year) are not the same as the reference matrix")
    end
    # save padded mat to filename but replace .mat with _padded.mat
    matwrite("output\\$ref_folder\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area_padded.mat",
        Dict("recurrance" => cfd_data[year], "duration" => ref_y, "amplitude" => ref_x),
        compress=true)
end

#dequeue!(queue)  # remove the first element
#dequeue!(queue)  # remove the second element
#print number of all_combinations
println("Number of combinations: $(length(queue))")
threads_to_start = min(length(queue),cores)
consequtive_runs = div(length(queue),threads_to_start,RoundUp)
for i in threads_to_start-1:-1:1
    if div(length(queue),threads_to_start-i,RoundUp) == consequtive_runs
        printstyled("Reducing number of threads to $(threads_to_start-i) since this wont affect time to complete queue\n"; color=:red)
        global threads_to_start -= i
        break
    end
end

#printstyled("At around 25 s per combination, this will take $(round(length(queue)*25/60)) minutes\n"; color=:green)
#printstyled("At around 25 s per combination and $(cores) cores, this will take $(round(length(queue)*25/60/min(length(queue),cores),sigdigits=2)) minutes with multi-threading\n"; color=:green)
scaled_ref_mat = ref_mat ./ 40
function sigmoid(x)
    return 1 / (1 + exp(-x))
end

function weights_penalty(weights;fixed_weights=0,slack_distance=0.011,amplitude=1e6)
    weight_sum = sum(weights)+fixed_weights*1/40
    penalty = (sigmoid((weight_sum-(1+slack_distance))*1000) + sigmoid(((1-slack_distance)-weight_sum)*1000))*amplitude
    return penalty
end

function diff_sum_weighted_mats(matrices,weights)
    # if matrices and weights have different lengths, it is assumed that the first matrices should have weights 1/40
    # the remaining matrices should have weights from the weights array
    m_sum = zeros(size(matrices[1]))
    if length(matrices) > length(weights)
        for i in 1:years_not_optimized
            m_sum .+= matrices[i] .* 1/40
        end
        matrices_left = matrices[years_not_optimized+1:end]
        print("matrices_left = $(matrices_left)")
    else
        matrices_left = matrices
    end
    for i in 1:length(weights)
        m_sum .+= weights[i] .* matrices_left[i]
    end
    diff = m_sum .- scaled_ref_mat
    return diff
end

println("Starting $(threads_to_start) threads (use ´julia --threads $(Sys.CPU_THREADS) script_name.jl´ to use max cores)") # returns "Starting 63 threads"

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
BBO_algs_single = [:probabilistic_descent]
if maxtime>120
    BBO_algs_adaptive = [:probabilistic_descent, :adaptive_de_rand_1_bin]
else
    BBO_algs_adaptive = [:pso, :probabilistic_descent]
end
if typeof(algs_size) == String
    BBO_algs = eval(Meta.parse("BBO_algs_$(algs_size)"))
else
    BBO_algs = [algs_size]
end
printstyled("At $maxtime s per solve, $(length(BBO_algs)) algs and $(threads_to_start) threads, this will take $(round(length(queue)*maxtime/60/threads_to_start*length(BBO_algs),digits=1)) minutes with multi-threading\n"; color=:green)
longest_alg_name = maximum([length(string(alg)) for alg in BBO_algs])
#print, in yellow and with ######-separation, the maxtime and algs that the loop is ran with
global_best = 9e9
printstyled("############# -- Starting optimization loop with maxtime=$(maxtime)s and algs_size '$(algs_size)' -- #############\n"; color=:yellow)

Threads.@threads for thread = 1:threads_to_start
    #sleep for 250 ms to stagger thread starts
    time_to_sleep = 0.2*thread
    sleep(time_to_sleep)
    global global_best
    while true
        if length(queue) == 0
            #println("Nothing to do")
            break
        end
        start_time = Dates.now()
        local case = []
        lock(print_lock) do # for some reason, julia would freeze and the dequeue would bug out if this was not locked
            case = dequeue!(queue)
            printstyled("Thread $(thread) started working on $(case) at $(Dates.format(now(), "HH:MM:SS")), $(length(queue)) left in queue\n"; color=:cyan)
        end
        convert(Vector{String},case)
        matrices = [cfd_data[year] for year in case if !(year in most_interesting_years)]
        # Use an optimization algorithm to find the best weights
        function sse(x)
           diff = diff_sum_weighted_mats(matrices,x)
           return dot(diff,diff)
        end
        function abs_sum(x)
            diff = diff_sum_weighted_mats(matrices,x)
            result = 0.0
            @inbounds @simd for i in eachindex(diff)
                result += abs(diff[i])
            end
            return result
        end
        function sqrt_sum(x)
            diff = diff_sum_weighted_mats(matrices,x)
            result = 0.0
            @inbounds @simd for i in eachindex(diff)
                result += sqrt(abs(diff[i]))
            end
            return result
        end
        function log_sum(x)
           diff = diff_sum_weighted_mats(matrices,x)
           diff = replace(diff, 0 => NaN)
           e = abs.(log10.(abs.(diff)))
           # return sum of e but ignoring NaN
           #penalty = sigmoid((sum(x)-1.011)*1000)+sigmoid((0.989-sum(x))*1000)
           return sum(e[.!isnan.(e)])#+penalty*100000
        end
        function weighted_mat_sum(x, weight_matrix=weight_matrix_lin19diff)
              diff = diff_sum_weighted_mats(matrices,x).*weight_matrix'
            return sum(abs.(diff[.!isnan.(diff)]))
        end
        # a vector w that is the same length as the number of matrices and equals 1/number of matrices
        w = ones(length(matrices)) ./ length(matrices)
        upper = ones(length(matrices))
        lower = zeros(length(matrices))
        ###----------------------------
        ### SET THE ERROR FUNCTION TO OPTIMIZE WITH HERE
        ###----------------------------
        global opt_func_str = "sqrt_sum(x) + weights_penalty(x,fixed_weights=years_not_optimized,slack_distance=0.011,amplitude=10000)" #sigmoid((sum(x)-1.011)*1000) +
        opt_func(x) = sqrt_sum(x) + weights_penalty(x,fixed_weights=years_not_optimized,slack_distance=0.011,amplitude=10000) #sigmoid((sum(x)-1.011)*1000) +
        local initial_guesses_3 = [
            # considering the solution space as a triangle where each corner is 100% of one axis such as (1,0,0)
            # let some initial guesses be the center of the triangle and on the center of the edges of the triangle
            [1/3,1/3,1/3], [19/40, 19/40, 2/40], [2/40, 19/40, 19/40], [19/40, 2/40, 19/40],
            # then divide the triangle into 4 new triangles (like a triforce) and do the same again
            [2/3, 1/6, 1/6], [1/6, 2/3, 1/6], [1/6, 1/6, 2/3], # center of smaller triangles
            [1/2, 1/4, 1/4], [1/4, 1/2, 1/4], [1/4, 1/4, 1/2], # center of inner edges of smaller triangles
            [29, 9, 2]./40, [2, 29, 9]./40, [9, 2, 29]./40, # center of outer edges of smaller triangles
            [29, 2, 9]./40, [9, 29, 2]./40, [2, 9, 29]./40, # center of outer edges of smaller triangles
            ]
        local initial_guesses_4 = [
            [1/4,1/4,1/4,1/4], [15/40,15/40,5/40,5/40], [15/40,5/40,15/40,5/40],
            [15/40,5/40,5/40,15/40], [5/40,15/40,15/40,5/40], [5/40,15/40,5/40,15/40],
            [5/40,5/40,15/40,15/40]
            ]
        local initial_guesses_2 = [
            [1/2, 1/2], [1/3, 2/3], [2/3, 1/3], [2/40, 38/40], [38/40, 2/40]
            ]
        local initial_guesses_1 = [
            [1.]
            ]
        local initial_guesses = initial_guesses_3

        bounds = (1/40, 1-1/40)
        if !optimize_all
            # if we are not optimizing all years, that means we are optimizing the last years_to_add years
            # so initial_guesses should be the nr equal to years_to_add
            if years_to_add == 1
                initial_guesses = initial_guesses_1
            elseif years_to_add == 2
                initial_guesses = initial_guesses_2
            elseif years_to_add == 3
                initial_guesses = initial_guesses_3
            end
            if years_to_add == 1
                #if we're optimizing only 1 year, then the bounds are just 1 value: 1-length(most_interesting_years)/40
                bounds = (1-length(most_interesting_years)/40, 1-length(most_interesting_years)/40)
            end
            # decrease all values in the lists in initial_guesses by 1/40
            for i in 1:length(initial_guesses)
                initial_guesses[i] = initial_guesses[i] .- years_not_optimized/40/years_to_add
            end
            #println("decreased initial guesses by $(years_not_optimized/40/years_to_add) so that the initial guess should sum to $(sum(initial_guesses[1])+years_not_optimized/40)")
            #println(initial_guesses)

        else
            length(years_per_combination) == 4 && (initial_guesses = initial_guesses_4)
            length(years_per_combination) == 3 && (initial_guesses = initial_guesses_3)
            length(years_per_combination) == 2 && (initial_guesses = initial_guesses_2)
            length(years_per_combination) == 1 && (initial_guesses = initial_guesses_1)
        end
        local init
        local alg_solutions = Dict()
        for alg in BBO_algs
            #print the next line only tif thread==1
            if thread == 1
                printstyled("Trying $(alg) with bounds = $bounds and $(length(initial_guesses[1])) dims..\n"; color=:cyan)
            end
            local res
            try
                res = bboptimize(opt_func, initial_guesses; method=alg, NumDimensions=length(initial_guesses[1]),
                                    SearchRange=bounds, MaxTime=maxtime, TraceInterval=2, TraceMode=:silent) #TargetFitness=88355.583298,FitnessTolerance=0.0001
            catch e
                println("$case, $alg failed with error: \n$e")
                println("retrying..")
                try
                    res = bboptimize(opt_func, initial_guesses; method=alg, NumDimensions=length(initial_guesses[1]),
                                    SearchRange=bounds, MaxTime=maxtime, TraceInterval=2, TraceMode=:silent) #TargetFitness=88355.583298,FitnessTolerance=0.0001
                catch e
                    printstyled("$case, $alg failed AGAIN with error: \n$e"; color=:red)
                end
            end
            local weights_list = best_candidate(res)
            local e = opt_func(weights_list)
            alg_solutions[alg] = (e, weights_list)
        end
        #print each alg's solution
        lock(print_lock) do
            _best_alg = BBO_algs[argmin([alg_solutions[alg][1] for alg in BBO_algs])]
            best_errors[case] = alg_solutions[_best_alg][1]
            years_not_optimized==0 ? best_weights[case] = alg_solutions[_best_alg][2] : best_weights[case] = vcat([1/40 for i in 1:years_not_optimized],alg_solutions[_best_alg][2])
            best_alg[case] = _best_alg
            if alg_solutions[_best_alg][1] < global_best
                printstyled("years: $(case)"; color=:green)
                printstyled("       <-- best so far\n"; color=:red)
                global_best = best_errors[case]
            else
                printstyled("years: $(case)\n"; color=:green)
            end
            # find for which alg the error is the lowest
            for alg in BBO_algs
                print("$(round(alg_solutions[alg][1],digits=1)) $(round.(alg_solutions[alg][2],digits=3)) $(rpad(round(sum(alg_solutions[alg][2]),digits=2)+years_not_optimized*1/40,4)) $(alg)")
                if alg == _best_alg
                    printstyled(" <-\n"; color=:green)
                else
                    print("\n")
                end

            end
        end
        #if case not in best_errors
        if !(case in keys(best_errors))
            printstyled("did not find $case in best_errors\n"; color=:red)
            best_errors[case] = alg_solutions[_best_alg][1]
            best_weights[case] = alg_solutions[_best_alg][2]
            best_alg[case] = _best_alg
        end
        if !(case in keys(best_errors))
            printstyled("AGAIN did not find $case in best_weights\n"; color=:red)
            lock(print_lock) do
                best_errors[case] = alg_solutions[_best_alg][1]
                best_weights[case] = alg_solutions[_best_alg][2]
                best_alg[case] = _best_alg
            end
        end
        if !(case in keys(best_errors))
            printstyled("AGAIN AGAIN did not find $case in best_alg\n"; color=:red)
            error("failed to add $case to best_errors")
        end
    end
end
for comb in all_combinations
    #if comb not in best_errors
    if !(comb in keys(best_errors))
        best_errors[comb] = Inf
        best_weights[comb] = zeros(length(comb))
        best_alg[comb] = "none"
    end
end
# sum finc should be the text in opt_func_str before the first +
sum_func = split(opt_func_str, "(")[1]

# Find the 3 best combinations (lowest SSE), print their SSE and weights
println("Done optimizing all combinations at $(Dates.format(now(), "HH:MM:SS"))")
printstyled("The 3 best combinations are ($(years[1])-$(years[end])) [sum_func=$(sum_func)()]:\n", color=:cyan)
try
    global sorted_cases = sort(collect(best_errors), by=x->x[2])
    for (case, error) in sorted_cases[1:3]
        printstyled("$(case) with error $(round(error,digits=1))\n", color=:green)
        println("weights: $(round.(best_weights[case],digits=3)) (sum: $(round(sum(best_weights[case]),digits=3)))")
        # print each item in the case and its respective weight
    end
    #sort all_combinations by its value in the dictionary best_errors
    global all_combinations = sort(collect(all_combinations), by=x->best_errors[x])
catch e
    printstyled("!Error: $(e)\n", color=:red)
end

# Save the results as a .json file
folder_name = "results\\$ref_folder/FP $sum_func $timestamp"
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
using XLSX
XLSX.openxlsx(joinpath(folder_name, "results $sum_func $timestamp.xlsx"), mode="w") do xf
    sheet = xf[1] # Add sheet
    XLSX.rename!(sheet, "Results $maxtime s") # Rename sheet

    # Step 6.3: Write the headers for the columns
    n = years_per_combination # Assuming all_combinations is non-empty
    year_headers = ["Year $i" for i in 1:n]
    weight_headers = ["W$i" for i in 1:n]
    headers = vcat(["Error"], year_headers, weight_headers, ["Algorithm"])
    sheet["A1", dim=2] = headers

    # Step 6.4: Iterate through the combinations and write the results to the worksheet
    for i in 1:length(all_combinations)
        combination = all_combinations[i]
        error = best_errors[combination]
        weight = best_weights[combination]
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
