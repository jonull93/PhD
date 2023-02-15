#=
fingerprintmatching:
- Julia version: 
- Author: Jonathan
- Date: 2023-01-18
=#
import Combinatorics: combinations
using MAT
using Optim

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

# Calculate the weighted sum of the matrices
function matrix_SSE(m1,m2,m3,w)
    m_sum = w[1]*m1 + w[2]*m2 + w[3]*m3
    # Calculate the difference between the weighted sum and matrix 4
    diff = m_sum - m4
    # Calculate the sum of the squares of the differences
    sse = sum(diff.^2)
    return sse
end

println("Initial SSE = $(matrix_SSE(m1,m2,m3,[w1,w2,w3]))")
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
res = optimize(sse_func, lower, upper, [w1, w2, w3])
w1_new = res.minimizer[1]
w2_new = res.minimizer[2]
w3_new = res.minimizer[3]

# Print the best weights
println("The best weights are:")
println("w1 = $(w1_new)")
println("w2 = $(w2_new)")
println("w3 = $(w3_new)")

println("Final SSE = $(matrix_SSE(m1,m2,m3,[w1_new,w2_new,w3_new]))")
printstyled("Finished test run\n"; color=:cyan)
#The output of the code will be the best weights that can be used to match matrices 1,2,3 to matrix 4.

# Parameters
amplitude_resolution = 1
window = 12
years = 1980:1983#1980:2019
most_interesting_years = ["2010-2011","2002-2003",]
years_list = map(x -> string(x, "-", x+1), years)
years_list = vcat(years_list,[i for i in most_interesting_years if !(i in years_list)])

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
    temp = matread(filename)
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
println(years_list)
year_combinations = Dict()
final_SSE = Dict()
for interesting_year in most_interesting_years
    printstyled("Starting optimization with year $(interesting_year)\n"; color=:cyan)
    year_combinations[interesting_year] = combinations(filter(!=(interesting_year),years_list), 2)  # a generator instead of a list until collect() is used
    println("$(length(year_combinations[interesting_year])) combinations to consider")
    for combination in year_combinations[interesting_year]
        printstyled("Year combination = $(combination)\n"; color=:white)
        println(size(combination))
        matrices = [cfd_data[year] for year in combination]
        println([year for year in combination])
        #print(matrices[1]*0.2+matrices[2]*0.3)
        #println(sum(matrices[1]))
        #println(typeof(matrices[1]))
        # Use an optimization algorithm to find the best weights
        function sse_func(x)
            w1 = x[1]
            w2 = x[2]
            w3 = x[3]
            m1 = cfd_data[interesting_year]
            m2 = matrices[1]
            m3 = matrices[2]
            m_sum = w1*m1 + w2*m2 + w3*m3
            diff = m_sum - ref_mat/40
            sse = sum(diff.^2)
            return sse
        end
        local res = optimize(sse_func, lower, upper, [w1, w2, w3])
        local w1_new = res.minimizer[1]
        local w2_new = res.minimizer[2]
        local w3_new = res.minimizer[3]

        # Print the best weights
        println("The best weights are:")
        println("w1 = $(w1_new)")
        println("w2 = $(w2_new)")
        println("w3 = $(w3_new)")

        println("Final SSE = $(matrix_SSE(m1,m2,m3,[w1_new,w2_new,w3_new]))")
    end
end
