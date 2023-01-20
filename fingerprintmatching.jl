#=
fingerprintmatching:
- Julia version: 
- Author: Jonathan
- Date: 2023-01-18
=#

#The following code can be used to find the best weights to match matrices 1,2,3 to matrix 4 in Julia:


# Define the matrices
m1 = [10 11 12; 4 5 6; 0 2 0]
m2 = [10 11 12; 13 14 15; 1 1 0]
m3 = [19 20 21; 22 23 24; 1 0 1]
m4 = [28 29 30; 31 32 33; 3 4 2]/2

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

#The output of the code will be the best weights that can be used to match matrices 1,2,3 to matrix 4.