#=
solution_space:
- Julia version: 
- Author: jonathan
- Date: 2023-03-29
=#

using MAT
using Plots
using LinearAlgebra
using LaTeXStrings
using JSON

function find_max_ref_folder(parent_directory)
    ref_folders = filter(x -> occursin(r"^ref\d+$", x), readdir(parent_directory))
    isempty(ref_folders) ? nothing : "ref" * string(maximum(parse(Int, replace(x, "ref" => "")) for x in ref_folders))
end

ref_folder = find_max_ref_folder("./output")
ref_folder = "ref26"
println("ref_folder = $ref_folder")


function diff_sum_weighted_mats(matrices,weights)
    m_sum = zeros(size(matrices[1]))
    for i in 1:length(matrices)
        m_sum .+= weights[i] .* matrices[i]
    end
    diff = m_sum .- scaled_ref_mat
    return diff
end
function sse(diff)
   return dot(diff,diff)
end
function abs_sum(diff)
    result = 0.0
    @inbounds @simd for i in eachindex(diff)
        result += abs(diff[i])
    end
    return result
end
function sqrt_sum(diff)
    result = 0.0
    @inbounds @simd for i in eachindex(diff)
        result += sqrt(abs(diff[i]))
    end
    return result
end
function log_sum(diff)
   diff = replace(diff, 0 => NaN)
   e = abs.(log10.(abs.(diff).+1))
   # return sum of e but ignoring NaN
   #penalty = sigmoid((sum(x)-1.011)*1000)+sigmoid((0.989-sum(x))*1000)
   return sum(e[.!isnan.(e)])#+penalty*100000
end
function weighted_mat_sum(diff,weight_matrix)
      diff = diff.*weight_matrix'
    return sum(abs.(diff[.!isnan.(diff)]))
end

starttime = time()

# Load mat data
total_year = "1980-2019"
ref_full = matread("output\\$ref_folder\\heatmap_values_$(total_year)_amp1_window12_area.mat")
ref_mat = ref_full["recurrance"]
ref_y = ref_full["duration"][:,1]
ref_x = ref_full["amplitude"][1,:]
printstyled("Imported total matrix $(size(ref_mat)) for $(total_year) \n"; color=:green)
# load weight matrices to be used with the error func sum_weight_mat, see git\python\figures\weight_matrix#.png for visuals
#weight_matrices = matread("output/weight_matrices.mat")
#weight_matrix_lin19diff = weight_matrices["Z_lin19diff"]
#weight_matrix_lin190diff = weight_matrices["Z_lin190diff"]
#weight_matrix_sqrt = weight_matrices["Z_sqrt"]  # min = 1, max = 14

ref_mat[isnan.(ref_mat)].= 0
scaled_ref_mat = ref_mat ./ 40

#combination = ["2005-2006", "1989-1990", "2014-2015"]
# in the folder results\$ref_folder there is a file called most_recent_results.txt which holds the path to the folder with the file results.json
# in this results.json file there is a key called "combinations" which holds all combination of years, sorted from best to worst
# take the first set of years and make it into a list called combination
# step 1, read the file most_recent_results.txt
file = open("results\\$ref_folder\\most_recent_results.txt")
path = readline(file)
close(file)
# step 2, read the file results.json
file = open("$path\\results.json")
json = JSON.parse(read(file, String))
close(file)
combination = json["combinations"][1]
printstyled("Combination of years: $(combination) \n"; color=:green)

cfd_data = Dict()
for year in combination
    filename = "output\\$ref_folder\\heatmap_values_$(year)_amp1_window12_area_padded.mat"
    temp = matread(filename)
    cfd_data[year] = replace(temp["recurrance"], NaN => 0)
end
matrices = [cfd_data[year] for year in combination]
printstyled("M1[1:2,1:2] = $(matrices[1][1:2,1:2]) \n"; color=:cyan)

res = 32  # make sure res+1 is divisible by 3
center = (res-1)÷3+1

function create_filled_triangle_matrix2(n::Int)
    # Creates a matrix with a triangle of non-NaN values in the topleft corner
    # Create a square matrix of tuples
    matrix = Array{Tuple{Float64, Float64, Float64}, 2}(undef, n, n)
    # Iterate over the matrix indices and set non-triangle elements to NaN
    for i in 1:n
        for j in 1:n
            if i + j <= n+1
                x = (n + 1 - i - j) / (n-1)
                y = (j - 1) / (n-1)
                z = (i - 1) / (n-1)
                matrix[i, j] = (x, y, z)
            else
                matrix[i, j] = (NaN, NaN, NaN)
            end
        end
    end
    return matrix
end

m = create_filled_triangle_matrix2(res)
#make abs_error and sqrt_error matrices
square_error = fill(NaN,res,res)
abs_errors = fill(NaN,res,res)
sqrt_errors = fill(NaN,res,res)
log_errors = fill(NaN,res,res)
#wmat_errors = fill(NaN,res,res)
#wmat2_errors = fill(NaN,res,res)
diff_mats = Dict()
# numbers if elements in the diagonal of a matrix with res rows
printstyled("Calculating errors for $(res) x $(res) matrix \n"; color=:green)
for x in 1:res
    for y in 1:res
        if x + y <= res+1
            x+y % (res^2 /10) == 0 && printstyled("."; color=:red)
            weight = m[x,y]
            diff_mat = diff_sum_weighted_mats(matrices,weight)
            square_error[x,y] = sse(diff_mat)
            abs_errors[x,y] = abs_sum(diff_mat)
            sqrt_errors[x,y] = sqrt_sum(diff_mat)
            log_errors[x,y] = log_sum(diff_mat)
            #wmat_errors[x,y] = weighted_mat_sum(diff_mat,weight_matrix_lin19diff)
            #wmat2_errors[x,y] = weighted_mat_sum(diff_mat,weight_matrix_sqrt)
        end
    end
end
println()
function indexmins2(A::AbstractArray{T,N}, n::Integer) where {T,N}
    perm = sortperm(vec(A))
    ci = CartesianIndices(A)
    return ci[perm[1:n]]
end
square_best_index = indexmins2(square_error,1)[1]
abs_best_index = indexmins2(abs_errors,1)[1]
println("abs_best_index = $(str(abs_best_index))")
sqrt_best_index = [indexmins2(sqrt_errors,1)[1][i] for i in 1:2]
log_best_index = [indexmins2(log_errors,1)[1][i] for i in 1:2]
#wmat_best_index = [indexmins2(wmat_errors,1)[1][i] for i in 1:2]
#wmat2_best_index = [indexmins2(wmat2_errors,1)[1][i] for i in 1:2]

#plot heatmap of the errors
combination_string = join(combination,", ")
path = "figures/$ref_folder/$combination_string"
mkpath(path)

using Plots

heatmap_colors = [:Reds, :Blues, :Greens, :Oranges]

# Create a 2x2 plot with subplots for each heatmap
p = plot(
    heatmap(square_error./1000, color=heatmap_colors[1], title=L"\sum_{i,j} {|M^{diff}_{i,j}|}^2", size=(600,600), ticks=false, right_margin = 6Plots.mm, left_margin=5Plots.mm, bottom_margin=5Plots.mm),
    heatmap(abs_errors./1000, color=heatmap_colors[2], title=L"\sum_{i,j} |M^{diff}_{i,j}|", size=(600,600), ticks=false, right_margin = 6Plots.mm, bottom_margin=5Plots.mm),
    heatmap(sqrt_errors./1000, color=heatmap_colors[3], title=L"\sum_{i,j} \sqrt{|M^{diff}_{i,j}|}", size=(600,600), ticks=false, right_margin = 6Plots.mm, left_margin=5Plots.mm, bottom_margin=5Plots.mm),
    heatmap(log_errors./1000, color=heatmap_colors[4], title=L"\sum_{i,j} \log_{10}(|M^{diff}_{i,j}|+1)", size=(600,600), ticks=false, bottom_margin=5Plots.mm),
    layout=(2,2),
)

# Add the labels for the min and max to each subplot
for (i, heatmap) in enumerate([square_error, abs_errors, sqrt_errors, log_errors])
    best_index = indexmins2(heatmap, 1)[1]
    annotate!(p[i], [(1,-0.5,text("$(Int.(m[1,1]))",8,:center))])
    #annotate!(p[i], [(1,1,text("$(Int.(m[1,1]))",8,:center))])
    annotate!(p[i], [(res,-0.5,text("$(Int.(m[res,1]))",8,:center))])
    annotate!(p[i], [(1,res,text("$(Int.(m[1,res]))",8,:center))])
    annotate!(p[i], [(center,center,text("x",8,:left))])
    annotate!(p[i], [(best_index[2],best_index[1],text("+",18,:center))])
end
# print the difference between the error in (center,center) and the best error
printstyled("Difference between center and best error for each metric: \n"; color=:green)
printstyled("square_error: $(round(square_error[center,center])) / $(round(square_error[square_best_index])) \n"; color=:green)
printstyled("abs_errors: $(round(abs_errors[center,center])) / $(round(abs_errors[abs_best_index])) \n"; color=:green)
printstyled("sqrt_errors: $(round(sqrt_errors[center,center])) / $(round(sqrt_errors[sqrt_best_index[1]])) \n"; color=:green)
printstyled("log_errors: $(round(log_errors[center,center])) / $(round(log_errors[log_best_index[1]])) \n"; color=:green)
# Save the figure
combination_string = join(combination,", ")
path = "figures/solution_space/$ref_folder/$combination_string"
mkpath(path)
savefig(joinpath(path,"res$(res)_error_triangles.png"))

#=
printstyled("Making wmat plot where min = $(minimum(wmat_errors[.!isnan.(wmat_errors)])) and max = $(maximum(wmat_errors[.!isnan.(wmat_errors)])) \n"; color=:green)
heatmap(wmat_errors, color=:Reds, title="wmatlin19 error", size=(600,600))
#add the labels for the min and max
annotate!([(1,1,text("$(Int.(m[1,1]))",8,:center))])
annotate!([(res,1,text("$(Int.(m[res,1]))",8,:center))])
annotate!([(1,res,text("$(Int.(m[1,res]))",8,:center))])
annotate!([(center,center,text("   <--(⅓,⅓,⅓)",7,:left))])
annotate!([(wmat_best_index[2],wmat_best_index[1],text("+",18,:center))])
savefig(joinpath(path,"res$(res)_wmatlin19_error_triangle.png"))

printstyled("Making wmat2 plot where min = $(minimum(wmat2_errors[.!isnan.(wmat2_errors)])) and max = $(maximum(wmat2_errors[.!isnan.(wmat2_errors)])) \n"; color=:green)
heatmap(wmat2_errors, color=:Reds, title="wmatlinsqrt error", size=(600,600))
#add the labels for the min and max
annotate!([(1,1,text("$(Int.(m[1,1]))",8,:center))])
annotate!([(res,1,text("$(Int.(m[res,1]))",8,:center))])
annotate!([(1,res,text("$(Int.(m[1,res]))",8,:center))])
annotate!([(center,center,text("   <--(⅓,⅓,⅓)",7,:center))])
annotate!([(wmat2_best_index[2],wmat2_best_index[1],text("+",18,:center))])
savefig(joinpath(path,"res$(res)_wmatsqrt_error_triangle.png"))
=#
println("Done with $combination_string after $(round((time()-starttime)/60,digits=2)) minutes")