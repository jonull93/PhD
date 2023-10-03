#=
fingerprintmatching:
- Julia version: 
- Author: Jonathan Ullmark
- Date of creation: 2023-01-18
=#

import Combinatorics: combinations
import Statistics: mean
using MAT
using Optim
using BlackBoxOptim
using DataStructures
using Dates
using Printf
using LinearAlgebra
using Plots
using JSON
using XLSX


#=
This script is currently set up to run with one or multiple heuristic optimization algorithms for a certain amount of time, then stop.
To circumvent the issue of spending up to an hour per year-combination for up to 5e5 (5 out of 39 years) combinations, the script can
be run for a very short time initially and then rerun for the 100 best combinations (after running figure_CFD.py inbetween).

A better solution would be to manually test all of the starting points (would probably take <1 second per combination) and then run the
optimization algorithm for some longer duration for the best 5-10% of solutions. This would make the script more automatic and could
ensure that the aborted optimization algorithm doesn't return a solution worse than the starting points (happens sometimes but is
counteracted by long optimization times and multiple algorithms).
=#

#make it clear in the command prompt that the code is running
timestamp = Dates.format(now(), "u_dd_HH.MM.SS")
printstyled("\n ############# -- Starting fingerprintmatching.jl at $(timestamp) -- ############# \n"; color=:yellow)
start_time = Dates.now()
const print_lock = ReentrantLock()
#if the script was started with more than 5 threads, print a warning in red and later reduce the number of threads to 5
if Threads.nthreads() > 5
    printstyled("Warning: more than 5 threads are being used, this has no benefit on the results!\n"; color=:red)
    printstyled("Setting the max number of threads to 5..\n"; color=:red)
end

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
extreme_years = ["2002-2003", "1996-1997"]#["1986-1987","1989-1990"]["2002-2003", "1996-1997"]["1989-1990","2005-2006"]#["1984-1985", "1995-1996"]#["2010-2011","2002-2003",]
#extreme_years = ["1986-1987","1989-1990"]
#extreme_years = ["1985-1986", "1996-1997"]
#extreme_years = ["1995-1996", "1996-1997"]
function find_max_ref_folder(parent_directory)
    ref_folders = filter(x -> occursin(r"^ref\d+$", x), readdir(parent_directory))
    isempty(ref_folders) ? nothing : "ref" * string(maximum(parse(Int, replace(x, "ref" => "")) for x in ref_folders))
end
ref_folder = find_max_ref_folder("./output")
#ref_folder = "ref14"

maxtime = 60*1 # 60*30=30 minutes
autotime = false
algs_size = "single" # "small" or "large" or "single" or "adaptive"
years_per_combination = 3
import_combinations = false
requested_sum_func = "sse" # "abs_sum" or "sqrt_sum" or "log_sum" or "sse"
simultaneous_extreme_years = 2
years_to_add = years_per_combination - simultaneous_extreme_years # number of years to add to the extreme years for each combination
years_to_optimize = years_to_add
optimize_all = years_to_optimize == years_per_combination
# ask the user whether to import the 100 best combinations from the previous run
while true
    printstyled("
  The script is set up with the following parameters:
    maxtime = $(maxtime/60) minutes,
    algs_size = $(algs_size),
    years_per_combination = $(years_per_combination),
    import_combinations = $(import_combinations),
    extreme_years = $(extreme_years),
    simultaneous_extreme_years = $(simultaneous_extreme_years),
    optimize_all = $(optimize_all),
    requested_sum_func = $(requested_sum_func),
    ref_folder = $(ref_folder)
        - Enter a number to set the max number of minutes for each optimization (5-10 min recommended)
          (<= 1 min will start a 'manual' search of the starting points to filter out the bad combinations)
        - Enter 'single', 'small', 'adaptive' or 'large' to change the size of the algorithm
        - Enter '#years' (e.g 4years) to change the number of years in each combination
        - Enter 'ifalse'/'i25'/'i50'/'i100'/'i2x' to change the number of combinations to import
        - Enter 'o' to optimize the weights also for the extreme years
        - Enter '#ey' (e.g 2ey) to change the number of extreme years in each combination
        - Enter 'abs', 'sqrt', 'log' or 'sse' to change the sum function
        - Enter 'ref' followed by a number (e.g. 'ref1') to change the ref_folder
        - Enter 'exit' or 'e' to skip\n"; color=:yellow)
    input = readline()
    if input == "exit" || input == "e" || input == ""
        break
    #import combinations?
    elseif input == "ifalse" || occursin(r"^i\d+(\.\d+)?x?$", input)    #input == "i25" || input == "i50" || input == "i100" || input == "i2x" || occursin(r"^\d+$", input)
        if input == "ifalse"
            global import_combinations = false
        else
            #parse the input to an integer
            global import_combinations = input[2:end]
        end
        printstyled("Importing combinations: $(import_combinations) \n"; color=:green)
    elseif input == "a"
        global simultaneous_extreme_years = length(extreme_years)  # if true, use all years in extreme_years, if false, use only one at a time
        global years_to_add = years_per_combination - simultaneous_extreme_years
        global years_to_optimize = years_to_add + simultaneous_extreme_years*optimize_all
        global optimize_all = years_to_optimize == years_per_combination
        printstyled("Using all extreme years at once \n"; color=:green)
    elseif tryparse(Float32,input) != nothing || (input[end]=='s' && tryparse(Float32,input[1:end-1]) != nothing) || input == "auto"
        if input[end] == 's'
            global maxtime = parse(Float32,input[1:end-1])
            global autotime = false
            printstyled("Max time set to $(maxtime) seconds \n"; color=:green)
        elseif input == "auto"
            global maxtime = years_per_combination+1
            global autotime = true
            printstyled("Max time set to $(maxtime/60) minutes \n"; color=:green)
        else
            global maxtime = parse(Float32,input)*60
            global autotime = false
            printstyled("Max time set to $(maxtime/60) minutes \n"; color=:green)
        end
    elseif input == "o"
        global optimize_all = years_to_optimize == years_per_combination
        global years_to_optimize = years_to_add + simultaneous_extreme_years*optimize_all
        printstyled("Optimizing weights for all years \n"; color=:green)
    elseif input == "single" || input == "small" || input == "adaptive" || input == "large"
        global algs_size = input
        printstyled("Algorithm size set to $algs_size \n"; color=:green)
    elseif input == "abs" || input == "sqrt" || input == "log"
        global requested_sum_func = input * "_sum"
        printstyled("Sum function set to $requested_sum_func \n"; color=:green)
    elseif input == "sse"
        global requested_sum_func = input
        printstyled("Sum function set to $requested_sum_func \n"; color=:green)
    elseif occursin(r"^ref", input)
        global ref_folder = input
        printstyled("Ref folder set to $ref_folder \n"; color=:green)
    elseif occursin(r"^\d+years$", input) || occursin(r"^\d+y$", input)
        global years_per_combination = parse(Int, replace(replace(input, "years" => ""), "y" => ""))
        global years_to_add = years_per_combination - simultaneous_extreme_years
        global years_to_optimize = years_to_add + simultaneous_extreme_years*optimize_all
        global optimize_all = years_to_optimize == years_per_combination
        printstyled("Years per combination set to $years_per_combination, $years_to_add years to add from list\n"; color=:green)
        autotime && global maxtime = years_per_combination+1
        printstyled("Max time set to $(maxtime/60) minutes \n"; color=:green)
    elseif occursin(r"^\d+ey$", input)
        global simultaneous_extreme_years = parse(Int, replace(input, "ey" => ""))
        global years_to_add = years_per_combination - simultaneous_extreme_years
        global years_to_optimize = years_to_add + simultaneous_extreme_years*optimize_all
        global optimize_all = years_to_optimize == years_per_combination
        printstyled("Simultaneous extreme years set to $simultaneous_extreme_years, $years_to_add years to add from list\n"; color=:green)
    else
        printstyled("Invalid input \n"; color=:red)
    end
end
years_not_optimized = years_per_combination - years_to_optimize
printstyled("-- Optimizing for $years_to_optimize year(s) out of $years_per_combination -- \n"; color=:red, bold=true)

if years_to_optimize == 1
    printstyled("There is only one year to 'optimize', so maxtime will be reduced to 5s and alg set to 'single'\n"; color=:red)
    maxtime = 5
    algs_size = "single"
end

if optimize_all && years_to_optimize == years_per_combination
    optimize_all = true
    printstyled("All years will be optimized, so optimize_all will be set to true\n"; color=:green)
end

#sleep_time=60*60*1;println("Sleeping for $(sleep_time/3600) hr");sleep(sleep_time)
# years_to_add scales insanely with the number of years, so it is not recommended to use more than 2

years_list = map(x -> string(x, "-", x+1), years)
years_list = vcat(years_list,[i for i in extreme_years if !(i in years_list)]) # if some years has been excluded, make sure to add back the extreme years

# Load mat data
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
#=
weight_matrices = matread("output/weight_matrices.mat", )
weight_matrix_lin19diff = weight_matrices["Z_lin19diff"]
weight_matrix_lin190diff = weight_matrices["Z_lin190diff"]
weight_matrix_sqrt = weight_matrices["Z_sqrt"]  # min = 1, max = 14
=#

# Generate combinations of years to optimize match for
year_combinations = Dict()
final_SSE = Dict()
weights = Dict()
queue = Queue{Any}()
cores = Threads.nthreads()
all_combinations = []
if import_combinations != false
    # read folder_name from results/most_recent_results.txt
    folder_name = readlines("results/$ref_folder/most_recent_results.txt")[1]
    # read folder_name/best_100.json, or skip to the else-block if the file does not exist
    if !isfile("$folder_name/best_$import_combinations.json")
        printstyled("File $(folder_name)/best_$import_combinations.json does not exist, skipping import of combinations\n", color=:red)
        sleep(5)
        @goto skip_import
    end
    best_100 = JSON.parsefile("$(folder_name)/best_$import_combinations.json")
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
    good_candidates = [
    ["1986-1987", "1989-1990", "1982-1983", "1991-1992", "1996-1997", "2004-2005", "2018-2019"],
    ["1986-1987", "1989-1990", "1982-1983", "1991-1992", "1996-1997", "2004-2005", "2016-2017"],
    ["1986-1987", "1989-1990", "1982-1983", "1991-1992", "1996-1997", "2004-2005"],
    ["2002-2003", "1996-1997", "1980-1981", "1981-1982", "1992-1993", "2003-2004", "2018-2019", "1982-1983"],
    ["1986-1987", "1989-1990", "1980-1981", "1981-1982", "1992-1993", "2003-2004", "2018-2019", "1982-1983"],
    ["1986-1987", "1989-1990", "1981-1982", "1985-1986", "1988-1989", "1999-2000", "2016-2017", "1982-1983"],
    ["2002-2003", "1996-1997", "1982-1983", "1990-1991", "1994-1995", "2008-2009", "2010-2011", "2015-2016"],
    ["2002-2003", "1996-1997", "1993-1994", "1999-2000", "2000-2001", "2003-2004", "2010-2011", "2011-2012"],
    ["1985-1986", "1996-1997", "1984-1985", "1988-1989", "1989-1990", "1991-1992", "2004-2005"],
    ["1985-1986", "1996-1997", "1993-1994", "2000-2001", "2003-2004", "2010-2011", "2011-2012"],
    ["2002-2003", "1996-1997", "1986-1987", "1995-1996", "2003-2004", "2014-2015", "2016-2017"],
    ["2002-2003", "1996-1997", "1980-1981", "1981-1982", "1992-1993", "2003-2004", "2018-2019"],
    ["2002-2003", "1996-1997", "1993-1994", "2012-2013", "2013-2014"],
    ["2002-2003", "1996-1997", "1981-1982", "2014-2015", "2017-2018"],
    ["1995-1996", "1996-1997", "1993-1994", "2012-2013", "2013-2014"],
    ["1995-1996", "1996-1997", "1982-1983", "1999-2000", "2002-2003"],
    ["1981-1982", "1982-1983", "1985-1986", "2018-2019"],
    ["2000-2001", "2002-2003", "2014-2015", "2017-2018"],
    ["1980-1981", "1992-1993", "1996-1997", "2014-2015"],
    ["2002-2003", "1996-1997", "2003-2004", "2009-2010"],
    ["2002-2003", "1996-1997", "2014-2015"],
    ["1981-1982", "2014-2015", "2016-2017"],
    ["1981-1982", "1999-2000", "2016-2017"],
    ["2002-2003", "1996-1997", "2014-2015"],
    ["2000-2001", "2016-2017"]
    ]
    extreme_year_combinations = combinations(extreme_years, simultaneous_extreme_years)
    for extreme_year_set in extreme_year_combinations
        years_to_use = [i for i in years_list if !(i in extreme_year_set)]
        if length(years_to_use) >= years_to_add
            global year_combinations = combinations(years_to_use, years_to_add)
            for combination in year_combinations
                case = copy(extreme_year_set)
                append!(case, combination)
                #enqueue!(queue,case)
                push!(all_combinations,case)
            end
        end
    end
    # add all combinations to the queue, but add the good_candidates, if in all_combinations, to the front of the queue
    for candidate in good_candidates
        if candidate in all_combinations
            enqueue!(queue, candidate)
        end
    end
    for combination in all_combinations
        if !(combination in good_candidates)
            enqueue!(queue, combination)
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
    #println("Adding $(columns_to_add) columns")
    xpad = zeros((size(cfd_data[year])[1],columns_to_add))
    cfd_data[year] = hcat(cfd_data[year],xpad)
    #println("Added columns - new size is $(size(cfd_data[year]))")
    start_rows = count(y -> y < minimum(y_data[year]), ref_y)
    end_columns = count(y -> y > maximum(y_data[year]), ref_y)
    #println("Adding $(start_rows) rows at the top and $(end_columns) rows at the bottom")
    #instead of printing how many rows and columns are added, print a warning of none are added
    if start_rows == 0 && end_columns == 0 && columns_to_add == 0
        printstyled("Warning: no rows or columns are added to the matrix for $(year)\n"; color=:red)
    end
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
threads_to_start = min(length(queue),cores,5)
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

function weights_penalty(weights;fixed_weights=0,slack_distance=0.007,amplitude=2e6)
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
            m_sum .+= matrices[i] .* 1/40 # assuming the hand-picked years' matrices are first in the list
        end
        matrices_left = matrices[years_not_optimized+1:end]
        #println("matrices_left = $(length(matrices_left))")
    elseif length(matrices) < length(weights)
        printstyled("Warning: more weights than matrices\n"; color=:red)
        return false
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
:probabilistic_descent,
:adaptive_de_rand_1_bin,]
BBO_algs_single = [:adaptive_de_rand_1_bin_radiuslimited] #adaptive_de_rand_1_bin_radiuslimited() is recommended in the bboxoptim documentation
if maxtime >= 29*60 # 29 minutes
    BBO_algs_adaptive = BBO_algs_single
elseif maxtime > 60 # 1 minute
    BBO_algs_adaptive = [:probabilistic_descent, :adaptive_de_rand_1_bin]
else
    BBO_algs_adaptive = BBO_algs_single # at less than 1 minute, manual mode is used anyway so the alg doesn't matter
end
if typeof(algs_size) == String
    BBO_algs = eval(Meta.parse("BBO_algs_$(algs_size)"))
else
    BBO_algs = [algs_size]
end
hours_to_solve = Int(div(length(queue)*maxtime/60/threads_to_start*length(BBO_algs),60))
minutes_to_solve = round((length(queue)*maxtime/60/threads_to_start*length(BBO_algs))%60)
printstyled("At $maxtime s per solve, $(length(BBO_algs)) algs and $(threads_to_start) threads, this will take $(hours_to_solve)h$(minutes_to_solve)m with multi-threading\n"; color=:green)
longest_alg_name = maximum([length(string(alg)) for alg in BBO_algs])
#print, in yellow and with ######-separation, the maxtime and algs that the loop is ran with
global_best = 9e9
global_midpoint_tracker = 0  # keeps track of the highest midpoint among solutions that are still good (within x% of the best solution)
printstyled("############# -- Starting optimization loop with maxtime=$(maxtime)s and algs_size '$(algs_size)' -- #############\n"; color=:yellow)
global initial_guesses_3 = [
    # considering the solution space as a triangle where each corner is 100% of one axis such as (1,0,0)
    # let some initial guesses be the center of the triangle and on the center of the edges of the triangle
    [1/3, 1/3, 1/3], [18/40, 18/40, 4/40], [4/40, 18/40, 18/40], [18/40, 4/40, 18/40],
    # then divide the triangle into 4 new triangles (like a triforce) and do the same again
    [2/3, 1/6, 1/6], [1/6, 2/3, 1/6], [1/6, 1/6, 2/3], # center of smaller triangles
    [1/2, 1/4, 1/4], [1/4, 1/2, 1/4], [1/4, 1/4, 1/2], # center of inner edges of smaller triangles
    #[29, 9, 2]./40, [2, 29, 9]./40, [9, 2, 29]./40, # center of outer edges of smaller triangles
    #[29, 2, 9]./40, [9, 29, 2]./40, [2, 9, 29]./40, # center of outer edges of smaller triangles
    ]
global initial_guesses_4 = [
    [1/4,1/4,1/4,1/4], [15/40,15/40,5/40,5/40], [15/40,5/40,15/40,5/40],
    [15/40,5/40,5/40,15/40], [5/40,15/40,15/40,5/40], [5/40,15/40,5/40,15/40],
    [5/40,5/40,15/40,15/40]
    ]
global initial_guesses_5 = [
    [1/5,1/5,1/5,1/5,1/5], [5/40,5/40,10/40,10/40,10/40], [5/40,10/40,5/40,10/40,10/40],
    [5/40,10/40,10/40,5/40,10/40], [5/40,10/40,10/40,10/40,5/40], [10/40,5/40,5/40,10/40,10/40],
    [10/40,5/40,10/40,5/40,10/40], [10/40,5/40,10/40,10/40,5/40], [10/40,10/40,5/40,5/40,10/40],
    [10/40,10/40,5/40,10/40,5/40], [10/40,10/40,10/40,5/40,5/40]
    ]
global initial_guesses_6 = [
    [1/6,1/6,1/6,1/6,1/6,1/6], 
    [4/40, 4/40, 8/40, 8/40, 8/40, 8/40],
    [4/40, 8/40, 4/40, 8/40, 8/40, 8/40], 
    [4/40, 8/40, 8/40, 4/40, 8/40, 8/40],
    [4/40, 8/40, 8/40, 8/40, 4/40, 8/40], 
    [4/40, 8/40, 8/40, 8/40, 8/40, 4/40],
    [8/40, 4/40, 4/40, 8/40, 8/40, 8/40],
    [8/40, 4/40, 8/40, 4/40, 8/40, 8/40], 
    [8/40, 4/40, 8/40, 8/40, 4/40, 8/40],
    [8/40, 4/40, 8/40, 8/40, 8/40, 4/40],
    [8/40, 8/40, 4/40, 4/40, 8/40, 8/40],
    [8/40, 8/40, 4/40, 8/40, 4/40, 8/40],
    [8/40, 8/40, 4/40, 8/40, 8/40, 4/40],
    [8/40, 8/40, 8/40, 4/40, 4/40, 8/40],
    [8/40, 8/40, 8/40, 4/40, 8/40, 4/40],
    [8/40, 8/40, 8/40, 8/40, 4/40, 4/40]
    ]
global initial_guesses_2 = [
    [1/2, 1/2], [1/3, 2/3], [2/3, 1/3], [6/40, 34/40], [34/40, 6/40] #, [2/40, 38/40], [38/40, 2/40]
    ]
global initial_guesses_1 = [
    [1.]
    ]
global initial_guesses = initial_guesses_3

bounds = (0+years_not_optimized/40, 1-years_not_optimized/40)
# if we are not optimizing all years, that means we are optimizing the last years_to_add years
# so initial_guesses should be the nr equal to years_to_add
if years_to_optimize == 1
    initial_guesses = initial_guesses_1
    printstyled("Initial guesses: initial_guesses_1\n"; color=:yellow)
elseif years_to_optimize == 2
    initial_guesses = initial_guesses_2
    printstyled("Initial guesses: initial_guesses_2\n"; color=:yellow)
elseif years_to_optimize == 3
    initial_guesses = initial_guesses_3
    printstyled("Initial guesses: initial_guesses_3\n"; color=:yellow)
elseif years_to_optimize == 4
    initial_guesses = initial_guesses_4
    printstyled("Initial guesses: initial_guesses_4\n"; color=:yellow)
elseif years_to_optimize == 5
    initial_guesses = initial_guesses_5
    printstyled("Initial guesses: initial_guesses_5\n"; color=:yellow)
elseif years_to_optimize == 6
    initial_guesses = initial_guesses_6
    printstyled("Initial guesses: initial_guesses_6\n"; color=:yellow)
else
    error("years_to_optimize = $(years_to_optimize) is not supported")
end
# decrease all values in the lists in initial_guesses by 1/40
for i in 1:length(initial_guesses)
    initial_guesses[i] = initial_guesses[i] .- years_not_optimized/40/years_to_add
end
!optimize_all && println("decreased each initial guess by $(years_not_optimized/40/years_to_add) so that the initial guesses sum to $(sum(initial_guesses[1])+years_not_optimized/40)")
#println(initial_guesses)
#=else
    if length(years_per_combination) == 4
        initial_guesses = initial_guesses_4
        printstyled("Initial guesses: initial_guesses_4\n"; color=:yellow)
    end
    if length(years_per_combination) == 3
        initial_guesses = initial_guesses_3
        printstyled("Initial guesses: initial_guesses_3\n"; color=:yellow)
    end
    if length(years_per_combination) == 2
        initial_guesses = initial_guesses_2
        printstyled("Initial guesses: initial_guesses_2\n"; color=:yellow)
    end
    if length(years_per_combination) == 1
        initial_guesses = initial_guesses_1
        printstyled("Initial guesses: initial_guesses_1\n"; color=:yellow)
    end
    printstyled("Sum of initial guesses [1]: $(sum(initial_guesses[1]))\n"; color=:yellow)
end=#
average_time_to_solve_per_thread = [0. for i in 1:threads_to_start]
Threads.@threads for thread = 1:threads_to_start
    time_to_solve_array = [0.]
    #sleep for 250 ms to stagger thread starts
    #time_to_sleep = 0.5*thread
    #sleep(time_to_sleep)
    global global_best
    global global_midpoint_tracker
    global requested_sum_func
    while true
        if length(queue) == 0
            #println("Nothing to do")
            average_time_to_solve_per_thread[thread] = mean(time_to_solve_array)
            break
        end
        start_time = Dates.now()
        local case = []
        lock(print_lock) do # for some reason, julia would freeze and the dequeue would bug out if this was not locked
            if length(queue) > 0
                case = dequeue!(queue)
            end
        end
        if thread == 1 || maxtime > 60
            lock(print_lock) do
                printstyled("Thread $(thread) started working on $(case) at $(Dates.format(now(), "HH:MM:SS")), $(length(queue)) left in queue\n"; color=:cyan)
            end
        end
        convert(Vector{String},case)
        matrices = [cfd_data[year] for year in case]# if !(year in extreme_years && !optimize_all)]
        if length(matrices) == 0
            printstyled("\n!! No matrices found for $(case) in thread $(thread)\n")
            continue
        end
        if thread == 1 && global_best > 1e8
            printstyled("There are $(length(matrices)) matrices sent to diff()\n"; color=:magenta)
        end
        # Use an optimization algorithm to find the best weights

        # a vector w that is the same length as the number of matrices and equals 1/number of matrices
        # w = ones(length(matrices)) ./ length(matrices)
        #upper = ones(length(matrices))
        #lower = zeros(length(matrices))
        ###----------------------------
        ### SET THE ERROR FUNCTION TO OPTIMIZE WITH HERE
        ###----------------------------
        
        global opt_func_str = "$requested_sum_func(x) + weights_penalty(x,fixed_weights=years_not_optimized,slack_distance=0.007,amplitude=2e5)" #sigmoid((sum(x)-1.011)*1000) +
        function opt_func(x)
            if requested_sum_func == "sse"
                function sse(x)
                    diff = diff_sum_weighted_mats(matrices,x)
                    return dot(diff,diff)
                 end
                return sse(x) + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
            elseif requested_sum_func == "abs_sum"
                function abs_sum(x)
                    diff = diff_sum_weighted_mats(matrices,x)
                    #if diff == false
                    #    return 0
                    #end
                    #result = 0.0
                    #@inbounds @simd for i in eachindex(diff)
                    #    result += abs(diff[i])
                    #end
                    return sum(abs.(diff))
                    #return result
                end
                return abs_sum(x) + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
            elseif requested_sum_func == "sqrt_sum"
                function sqrt_sum(x)
                    diff = diff_sum_weighted_mats(matrices,x)
                    result = 0.0
                    @inbounds @simd for i in eachindex(diff)
                        result += sqrt(abs(diff[i]))
                    end
                    return result
                end
                return sqrt_sum(x) + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
            elseif requested_sum_func == "log_sum"
                function log_sum(x)
                    diff = diff_sum_weighted_mats(matrices,x)
                    diff = replace(diff, 0 => NaN)
                    e = abs.(log10.(abs.(diff)))
                    # return sum of e but ignoring NaN
                    #penalty = sigmoid((sum(x)-1.011)*1000)+sigmoid((0.989-sum(x))*1000)
                    return sum(e[.!isnan.(e)])#+penalty*100000
                 end
                return log_sum(x) + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
            else
                #raise error
                error("Invalid requested_sum_func")
                #=function weighted_mat_sum(x, weight_matrix=weight_matrix_lin19diff)
                    diff = diff_sum_weighted_mats(matrices,x).*weight_matrix'
                    return sum(abs.(diff[.!isnan.(diff)]))
                end=#
            end
        end

        local alg_solutions = Dict()
        # define paramters for maxtime and midpoint_factor_for_skipping
        local maxtime_manual = 10 # seconds
        local midpoint_factor_for_skipping = 2.6 # from testing, it seems like 25% is about as much as the error can get improved (for abs_sum), though this decreases as the number of years increases
        # for sse, the improvement seems like it can be a lot higher!
        if maxtime < maxtime_manual
            if thread == 1 && global_best > 1e9
                lock(print_lock) do
                    printstyled("maxtime is less than 61 seconds, testing starting points manually\n"; color=:magenta)
                end
            end
            #manually test the initial guesses one by one using opt_func() instead of the BBOptim.jl package
            local best_guess = (0,Inf)
            local x = initial_guesses[1]
            local e = opt_func(x)
            local midpoint_error = e
            best_guess = (x,e)
            #=
            lock(print_lock) do # trying this to stop an error later when trying to sort best_errors, possibly because best_errors got corrupted by the multiple threads
                best_weights[case] = best_guess[1]
                best_errors[case] = best_guess[2]
                best_alg[case] = "manual mid-point"
            end
            =#
            if midpoint_error < global_best*midpoint_factor_for_skipping
                for i in 2:length(initial_guesses)
                    # if the thread is the first one, print which starting point is being tested
                    local x = initial_guesses[i]
                    local e = opt_func(x)
                    if e < best_guess[2]
                        best_guess = (x,e)
                    end
                end
            end
            if thread == 1
                lock(print_lock) do
                    printstyled("  Thread $(thread) finished working on $(case) at $(Dates.format(now(), "HH:MM:SS")), after $((Dates.now()-start_time)/Dates.Millisecond(1000)) s\n"; color=:green)
                    #printstyled("  Midpoint error was $(round(midpoint_error/global_best,digits=2)) of the global best\n"; color=:yellow)
                    #printstyled("  Error = $(round(best_guess[2],digits=1)) for $(round.(best_weights[case],digits=3))\n"; color=:white)
                    printstyled("Global best so far = $(round(global_best))\n"; color=:magenta)
                end
            end
            lock(print_lock) do
                best_weights[case] = best_guess[1]
                best_errors[case] = best_guess[2]
                #let best_alg say "-20% from mid-point" if the best guess is 20% from the mid-point guess, since there is no alg anyway
                best_alg[case] = "$(round(Int,(best_guess[2]-midpoint_error)/midpoint_error*100))% from mid-point"
            end
            if best_guess[2] <= global_best
                lock(print_lock) do
                    # prepare a string that indicates +/-% from the mid-point error to the previous global best
                    # if the midpoint_error was +30% of the previous global best, the string will be "+30%" specifically with the + sign
                    midpoint_error_string = "$(round(Int,(midpoint_error-global_best)/global_best*100))%"
                    if midpoint_error > global_best
                        midpoint_error_string = "+$(midpoint_error_string)"
                    end
                    global_midpoint_tracker *= best_guess[2]/global_best
                    global_best = best_guess[2]
                    printstyled("-> New global best: $(round(best_guess[2])) for $case (midpoint was $midpoint_error_string of old best)\n"; color=:red)
                end
            else
                #printstyled("\n"; color=:white)
                if best_guess[2] < global_best*1.2
                    lock(print_lock) do
                        #printstyled(" Only $(round(best_guess[2]/global_best,digits=2)) from the global best with the midpoint error at $(round(midpoint_error/global_best,digits=2))\n"; color=:blue)
                        if midpoint_error > global_midpoint_tracker
                            global_midpoint_tracker = midpoint_error
                        end
                    end
                end
                
            end
            #add the time it took to solve this case (in not rounded seconds) to the array time_to_solve_array
            push!(time_to_solve_array, (Dates.now()-start_time)/Dates.Millisecond(1000))

        else # if the maxtime is not less than maxtime_manual, use the BBOptim.jl package
            for alg in BBO_algs
                #print the next line only if thread==1
                if thread == 1
                    printstyled("Trying $(alg) with bounds = $bounds and $(length(initial_guesses[1])) dims\n"; color=:yellow)
                    hours_to_solve = Int(div((length(queue)/threads_to_start+1)*maxtime/60*length(BBO_algs),60))
                    minutes_to_solve = round(((length(queue)/threads_to_start+1)*maxtime/60*length(BBO_algs))%60)
                    printstyled("Estimated time left: $(hours_to_solve)h$(minutes_to_solve)m\n"; color=:yellow)
                end
                local res
                try
                    res = bboptimize(opt_func, initial_guesses; method=alg, NumDimensions=years_to_optimize,
                                        SearchRange=bounds, MaxTime=maxtime, TraceInterval=60, TraceMode=:compact) #TargetFitness=88355.583298,FitnessTolerance=0.0001
                catch e
                    println("$case, $alg failed with error: \n$e")
                    println("retrying..")
                    try
                        res = bboptimize(opt_func, initial_guesses; method=alg, NumDimensions=years_to_optimize,
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
                    print("  $(round(alg_solutions[alg][1],digits=1)) $(round.(alg_solutions[alg][2],digits=3)) $(rpad(round(sum(alg_solutions[alg][2]),digits=3)+years_not_optimized*1/40,4)) $(alg)")
                    if alg == _best_alg
                        printstyled(" <-\n"; color=:green)
                    else
                        print("\n")
                    end

                end
            end
            #add the time it took to solve this case (in not rounded seconds) to the array time_to_solve_array
            push!(time_to_solve_array, (Dates.now()-start_time)/Dates.Millisecond(1000))
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
end

println('\a') #beep
sleep(1)
#if global_midpoint_tracker is larger than 0, print it and say how many % higher it is than the global best
if global_midpoint_tracker > 0
    printstyled("global_midpoint_tracker = $(round(global_midpoint_tracker,digits=2)) ($(round(global_midpoint_tracker/global_best*100-100))% higher than global_best)\n"; color=:yellow)
    printstyled("This indicates that the threshold for skipping non-midpoints should be a bit higher than $(round(global_midpoint_tracker/global_best,digits=2)) for $years_to_optimize years and $requested_sum_func\n"; color=:yellow)
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
println("best_errors is $(length(best_errors)) items long")
global sorted_cases = sort(collect(best_errors), by=x->x[2])
global all_combinations = sort(collect(all_combinations), by=x->best_errors[x])
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
folder_name = "results\\$ref_folder/FP $sum_func $timestamp $(years_per_combination)yr $simultaneous_extreme_years eyrs"
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
maxtime_filename = joinpath(folder_name, "Maxtime= $maxtime, avg_time=$(round(mean(average_time_to_solve_per_thread),digits=2)), threads=$(threads_to_start)")
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
