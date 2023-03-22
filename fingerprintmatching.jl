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
printstyled("\n ############# -- Starting fingerprintmatching.jl -- #############\n", color=:yellow)
const print_lock = ReentrantLock()
#=
printstyled("Starting test optimization\n"; color=:cyan)
# Define the matrices
m1 = [10 11 12; 4 5 6; 0 2 0]
m2 = [10 11 12; 13 14 15; 1 1 0]
m3 = [19 20 21; 22 23 24; 1 0 1]
m4 = (m1+10*m2+85*m3)/90

# Define the weights
w1 = 0.05
w2 = 0.05
w3 = 0.9

# Set upper and lower limits
lower = [0, 0, 0]
upper = [1, 1, 1]

# Use an optimization algorithm to find the best weights
function sse_func(x)
    w1 = x[1]
    w2 = x[2]
    w3 = x[3]
    m_sum = w1*m1 + w2*m2 + w3*m3
    diff = m_sum - m4
    sse = sum(diff.^2)
    return sse
end
println("Initial SSE = $(round(sse_func([w1, w2, w3]), digits=2))")
res = optimize(sse_func, lower, upper, [w1, w2, w3])
#w1_new = res.minimizer[1]
#w2_new = res.minimizer[2]
#w3_new = res.minimizer[3]
w = res.minimizer

# Print the best weights
println("The best weights are:")
println("w1 = $(w[1])")
println("w2 = $(w[2])")
println("w3 = $(w[3])")
#println("w1 = $(w1_new)")
#println("w2 = $(w2_new)")
#println("w3 = $(w3_new)")

println("Final SSE = $(sse_func(w))")
printstyled("Finished test optimization\n"; color=:cyan)=#
#The output of the code will be the best weights that can be used to match matrices 1,2,3 to matrix 4.

# Parameters
amplitude_resolution = 1
window = 12
years = 1980:1981#:2018
most_interesting_years = ["2010-2011","2002-2003",]
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
for interesting_year in most_interesting_years
    #printstyled("Starting optimization that include year $(interesting_year)\n"; color=:cyan)
    year_combinations[interesting_year] = combinations(filter(!=(interesting_year),years_list), 2)  # a generator instead of a list until collect() is used
    for combination in year_combinations[interesting_year]
        case = [interesting_year,combination[1],combination[2]]
        enqueue!(queue,case)
    end
end
#dequeue!(queue)  # remove the first element
#dequeue!(queue)  # remove the second element
#print number of combinations
println("Number of combinations: $(length(queue))")
printstyled("At around 1 min per combination, this will take $(round(length(queue)/60)) hours\n"; color=:green)
printstyled("At around 8 min per combination and $(cores) cores this will take $(round(length(queue)*8/60/min(length(queue),cores),sigdigits=2)) hours with multi-threading\n"; color=:green)
#printstyled("At around 25 s per combination, this will take $(round(length(queue)*25/60)) minutes\n"; color=:green)
#printstyled("At around 25 s per combination and $(cores) cores, this will take $(round(length(queue)*25/60/min(length(queue),cores),sigdigits=2)) minutes with multi-threading\n"; color=:green)
scaled_ref_mat = ref_mat ./ 40
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

gr()
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

Threads.@threads for thread = 1:min(length(queue),cores)
    #sleep for 5 ms to stagger thread starts
    sleep(5e-3)
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
           return sum(e[.!isnan.(e)])
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
        opt_func = log_sum2
        ###----------------------------
        # NelderMead()
        # Fminbox(LBFGS())
        #=
        local res = optimize(opt_func, lower, upper, w, NelderMead(), Optim.Options(iterations=4000, show_every=50, show_trace=true))
        local weights_list = res.minimizer
        weights_list = replace(weights_list, NaN => 0)
        #if weights_list != weights_list2
        #    printstyled("Thread $(thread) found a mismatch between weights_list and weights_list2\n"; color=:red)
        #    printstyled("weights_list: $(weights_list)\n"; color=:red)
        #    printstyled("weights_list2: $(weights_list2)\n"; color=:red)
        #end
        final_SSE[case] = opt_func(weights_list)
        weights[case] = weights_list
        time_diff_seconds = Dates.value(now() - start_time)/1000
        minutes = div(time_diff_seconds, 60)
        seconds = mod(time_diff_seconds, 60)
        time_string = @sprintf("%02d:%02d", minutes, seconds)
        printstyled("Thread $(thread) finished working on $(case) after $(time_string)\n"; color=:green)
        #print (in green) the error and weights_list
        printstyled("error: $(round.(final_SSE[case],digits=2)), weights: $(round.(weights_list,digits=4))\n"; color=:green)
        =#
        BBO_algs_large = [:generating_set_search,
        :adaptive_de_rand_1_bin_radiuslimited,
        :simulated_annealing,
        :probabilistic_descent,
        :pso,
        :adaptive_de_rand_1_bin,
        :dxnes,
        ]
        BBO_algs_small = [:pso,
        :adaptive_de_rand_1_bin]
        BBO_algs = BBO_algs_small
        longest_alg_name = maximum([length(string(alg)) for alg in BBO_algs])
        maxtime = 300
        extreme_guesses = [[0.99999,0,0], [0,0.99999,0], [0,0,0.99999]]
        local guesses = [w]
        for g in extreme_guesses
            push!(guesses, g)
        end
        local alg_solutions = Dict()
        for alg in BBO_algs
            #print the next line only tif thread==1
            if thread == 1
                printstyled("Trying $(alg) with maxtime=$(maxtime) ..\n"; color=:cyan)
            end
            local res = bboptimize(opt_func, guesses; method=alg, NumDimensions=length(w),
                                    SearchRange=(0,1), MaxTime=maxtime, TraceInterval=10, TraceMode=:silent) #TargetFitness=88355.583298,FitnessTolerance=0.0001
            local weights_list = best_candidate(res)
            local e = opt_func(weights_list)
            #PRINT THE ERROR AND WEIGHTS
            #printstyled("years: $(case)\n"; color=:green)
            #printstyled("alg: $(alg)\n"; color=:green)
            #printstyled("error: $(round.(e,digits=5)), weights: $(round.(weights_list,digits=3))\n"; color=:green)
            alg_solutions[alg] = (e, weights_list)
        end
        #print each alg's solution
        lock(print_lock) do
            printstyled("years: $(case)\n"; color=:green)
            for alg in BBO_algs
                #change the following line so that the printed length of algs of different lengths is the same
                printstyled("$(rpad(string(alg),longest_alg_name+1)) error: $(round.(alg_solutions[alg][1],digits=3)), weights: $(round.(alg_solutions[alg][2],digits=3))\n"; color=:white)
                #@sprintf("%20i-30s error: %10.5f, weights: %s\n", rpad(string(alg)), alg_solutions[alg][1], round.(alg_solutions[alg][2],digits=3))

            end
        end
    end
end

# Find the 3 best combinations (lowest SSE), print their SSE and weights
println("Done optimizing all combinations! :)")
exit()

println(final_SSE)
println(weights)
best_cases = []
println("The 3 best combinations are:")
sorted_cases = sort(collect(final_SSE), by=x->x[2])
for (case, SSE) in sorted_cases[1:3]
    println("$(case) with SSE $(round(SSE,digits=2))")
    # print each item in the case and its respective weight
    for (i,year) in enumerate(case)
        println("w$(year) = $(round(weights[case][i], digits=2))")
    end
    push!(best_cases,case)
end

#=# Print the best weights
println("The best weights are:")
println("w1 = $(round(w1_new,sigdigits=2)) for year $(interesting_year)")
println("w2 = $(round(w2_new,sigdigits=2)) for year $(combination[1])")
println("w3 = $(round(w3_new,sigdigits=2)) for year $(combination[2])")
#println("The weights are $(w1_new), $(w2_new), $(w3_new) for years $(combination) and $(interesting_year) with SSE $(res.minimum)")
println("Final SSE = $(matrix_SSE(m1,m2,m3,[w1_new,w2_new,w3_new]))")

min_val = minimum(values(final_SSE))

for (key, value) in final_SSE
    if value == min_val
        println("Minimum value is $(value) for key $(key)")
    end
end
=#