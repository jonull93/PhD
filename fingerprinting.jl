#=
fingerprinting:
- Julia version: 
- Author: jonull
- Date: 2023-01-17
=#

netload_40 = ..
netload_1 = ..
netload_2 = ..
netload_3 = ..




function calculate_fit(net_load40, netload_1, netload_2, netload_3):
    #sum of squared residuals
    ssr::Float32 = 0
    for i in size()
end

```The following Julia function can be used to find the weights that best fit matrices 2, 3 and 4 to matrix 1:

```julia
function find_weights(mat1, mat2, mat3, mat4)
# Initialize weights
w1 = 0
w2 = 0
w3 = 0
w4 = 0

# Calculate the sum of squared errors
sse = 0
for i in 1:size(mat1, 1)
    for j in 1:size(mat1, 2)
        sse += (mat1[i, j] - (w1*mat2[i, j] + w2*mat3[i, j] + w3*mat4[i, j]))^2
    end
end

# Use gradient descent to find the optimal weights
learning_rate = 0.01
for i in 1:1000
    # Calculate the gradient
    grad_w1 = 0
    grad_w2 = 0
    grad_w3 = 0
    grad_w4 = 0
    for i in 1:size(mat1, 1)
        for j in 1:size(mat1, 2)
            grad_w1 += -2*(mat1[i, j] - (w1*mat2[i, j] + w2*mat3[i, j] + w3*mat4[i, j]))*mat2[i, j]
            grad_w2 += -2*(mat1[i, j] - (w1*mat2[i, j] + w2*mat3[i, j] + w3*mat4[i, j]))*mat3[i, j]
            grad_w3 += -2*(mat1[i, j] - (w1*mat2[i, j] + w2*mat3[i, j] + w3*mat4[i, j]))*mat4[i, j]
        end
    end

    # Update the weights
    w1 -= learning_rate*grad_w1
    w2 -= learning_rate*grad_w2
    w3 -= learning_rate*grad_w3
    w4 -= learning_rate*grad_w4
end

return (w1, w2, w3, w4)
end
