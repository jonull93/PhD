#=
fingerprintmatching:
- Julia version: 
- Author: Jonathan
- Date: 2023-01-18
=#
import Combinatorics: combinations
using MAT
using Optim
using DataStructures
using Dates
using Printf

printstyled("Starting test run\n"; color=:cyan)
# Define the matrices
m1 = [10 11 12; 4 5 6; 0 2 0]
m2 = [10 11 12; 13 14 15; 1 1 0]
m3 = [19 20 21; 22 23 24; 1 0 1]
m4 = (m1+10*m2+85*m3)/90

# Define the weights
w1 = 0.5
w2 = 0.3
w3 = 0.2

# Set upper and lower limits
lower = [0, 0, 0]
upper = [1, 1, 1]

# Use an optimization algorithm to find the best weights
using Optim
function sse_func(x)
    w1 = x[1]
    w2 = x[2]
    w3 = x[3]
    m_sum = w1*m1 + w2*m2 + w3*m3
    diff = m_sum - m4
    sse = sum(diff.^2)
    return sse
end
println("Initial SSE = $(sse_func([w1, w2, w3]))")
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
printstyled("Finished test run\n"; color=:cyan)
#The output of the code will be the best weights that can be used to match matrices 1,2,3 to matrix 4.

# Parameters
amplitude_resolution = 1
window = 12
years = 1980:1983#1980:2019
most_interesting_years = ["2010-2011"]#,"2002-2003",]
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
    filename = "input\\heatmap_values_$(year)_amp$(amplitude_resolution)_area.mat"
    try
        global temp = matread(filename)
    catch e
        filename = "output\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area.mat"
        global temp = matread(filename)
    end
    cfd_data[year] = replace(temp["recurrance"], NaN => 0)
    x_data[year] = temp["amplitude"][1,:]
    y_data[year] = temp["duration"][:,1]
    xlim = [minimum(x_data[year]), minimum(x_data[year])]
    ylim = [minimum(y_data[year]), minimum(y_data[year])]
    if length(findall(in(x_data[year]),ref_x))<length(x_data[year]); error("Non-matching x-axes"); end
    printstyled("Padding the matrix $(size(cfd_data[year])) for $(year) ..\n"; color=:green)
    columns_to_add = count(x -> x > maximum(x_data[year]), ref_x)
    #end_columns = count(x -> x > maximum(x_data[year]), ref_x)
    xpad = zeros((size(cfd_data[year])[1],columns_to_add))
    #xpad2 = zeros((size(cfd_data[year])[2],end_columns))
    cfd_data[year] = hcat(cfd_data[year],xpad)
    #println("Added columns - new size is $(size(cfd_data[year]))")
    start_rows = count(y -> y < minimum(y_data[year]), ref_y)
    end_columns = count(y -> y > maximum(y_data[year]), ref_y)
    ypad1 = zeros((start_rows,size(cfd_data[year])[2]))
    ypad2 = zeros((end_columns,size(cfd_data[year])[2]))
    cfd_data[year] = vcat(ypad1,cfd_data[year],ypad2)
    #printstyled("Done with matrix for $(year), new size is $(size(cfd_data[year])) \n"; color=:green)

end

# Generate combinations of years to optimize match for
year_combinations = Dict()
final_SSE = Dict()
weights = Dict()
queue = Queue{Any}()
cores = max(1,Sys.CPU_THREADS-1)
for interesting_year in most_interesting_years
    #printstyled("Starting optimization that include year $(interesting_year)\n"; color=:cyan)
    year_combinations[interesting_year] = combinations(filter(!=(interesting_year),years_list), 2)  # a generator instead of a list until collect() is used
    for combination in year_combinations[interesting_year]
        case = [interesting_year,combination[1],combination[2]]
        enqueue!(queue,case)
    end
end
#print number of combinations
println("Number of combinations: $(length(queue))")
printstyled("At around 25 s per combination, this will take $(round(length(queue)*25/60)) minutes\n"; color=:green)
printstyled("At around 25 s per combination and $(cores) cores, this will take $(round(length(queue)*25/60/min(length(queue),cores),sigdigits=2)) minutes with multi-threading\n"; color=:green)


println("Starting $(min(length(queue),cores)) threads (if Julia was started using ´julia --threads $(min(length(queue),cores)) script_name.jl´)") # returns "Starting 63 threads"
Threads.@threads for thread = 1:min(length(queue),cores)
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
        function sse_func(x,matrices)
            w1 = x[1]
            w2 = x[2]
            w3 = x[3]
            m1 = matrices[1]
            m2 = matrices[2]
            m3 = matrices[3]
            m_sum = w1*m1 + w2*m2 + w3*m3
            diff = m_sum - ref_mat/40
            sse = sum(diff.^2)
            return sse
        end
        function sse_func(x)
            return sse_func(x,matrices)
        end

        function sse_func2(x)
            m_sum = zero(eltype(matrices))
            for i in 1:length(x)
                wi = x[i]
                mi = matrices[i]
                m_sum += wi * mi
            end
            diff = m_sum - ref_mat/40
            sse = sum(diff.^2)
            return sse
        end

        local res = optimize(sse_func, lower, upper, [w1, w2, w3])
        local w1_new = res.minimizer[1]
        local w2_new = res.minimizer[2]
        local w3_new = res.minimizer[3]
        local weights_list = [w1_new,w2_new,w3_new]
        final_SSE[case] = sse_func(weights_list)
        weights[case] = weights_list
        time_diff_seconds = Dates.value(now() - start_time)/1000
        minutes = div(time_diff_seconds, 60)
        seconds = mod(time_diff_seconds, 60)
        time_string = @sprintf("%02d:%02d", minutes, seconds)
        printstyled("Thread $(thread) finished working on $(case) (SSE=$(round(final_SSE[case]))) after $(time_string)\n"; color=:green)
    end
end

# Find the 3 best combinations (lowest SSE), print their SSE and weights
println("Done optimizing all combinations! :)")
println(final_SSE)
println(weights)
best_cases = []
println("The 3 best combinations are:")
sorted_cases = sort(collect(final_SSE), by=x->x[2])
for (case, SSE) in sorted_cases[1:3]
    println("$(case) with SSE $(SSE)")
    # print each item in the case and its respective weight
    for (i,year) in enumerate(case)
        println("w$(year) = $(round(weights[case][i]))")
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