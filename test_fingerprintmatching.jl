#=
test_fingerprintmatching.jl:
- Julia version: 
- Author: jonathan
- Date: 2023-03-24
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
years = 1998:2012#:2018
most_interesting_years = ["2010-2011","2002-2003",]
maxtime = 45
algs_size = "adaptive" # "small" or "large" or "single"


years_list = map(x -> string(x, "-", x+1), years)
years_list = vcat(years_list,[i for i in most_interesting_years if !(i in years_list)])
println("Years: $(years_list)")
println("Number of years: $(length(years_list))")

# Load mat data
total_year = "1980-2019"
ref_full = matread("output\\heatmap_values_$(total_year)_amp$(amplitude_resolution)_window$(window)_area.mat")
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
#printstyled("At around 25 s per combination, this will take $(round(length(queue)*25/60)) minutes\n"; color=:green)
#printstyled("At around 25 s per combination and $(cores) cores, this will take $(round(length(queue)*25/60/min(length(queue),cores),sigdigits=2)) minutes with multi-threading\n"; color=:green)
scaled_ref_mat = ref_mat ./ 40
function sigmoid(x)
    return 1 / (1 + exp(-x))
end

function diff_sum_weighted_mats(matrices,weights,replacenans=false)
    ms = matrices
    for m in ms
        replacenans==true && (m = replace(m, NaN => 0))
        nothing
    end
    m_sum = sum(wi * mi for (wi, mi) in zip(weights, ms))
    diff = m_sum - scaled_ref_mat
    return diff
end
function sse(x, matrices)
   diff = diff_sum_weighted_mats(matrices,x)
   return dot(diff,diff)
end
function abs_sum(x, matrices)
   diff = diff_sum_weighted_mats(matrices,x)
   return sum(abs.(diff))
end
function sqrt_sum(x, matrices)
   diff = diff_sum_weighted_mats(matrices,x)
   return sum(sqrt.(abs.(diff)))
end
function log_sum(x, matrices)
   diff = diff_sum_weighted_mats(matrices,x)
   diff = replace(diff, 0 => NaN)
   e = abs.(log10.(abs.(diff)))
   return sum(e[.!isnan.(e)])#+penalty*100000
end

#matrices = [cfd_data[year] for year in case]