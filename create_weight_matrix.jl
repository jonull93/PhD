#=
create_weight_matrix.jl:
- Julia version: 1.8.5
- Author: jonathan
- Date: 2023-03-23
=#

using MAT

# load the 1980-2019 data from (f"output\\heatmap_values_1980-2019_amp{amp_length}_window{rolling_hours}{'_area'*area_mode_in_cfd}.mat")
filepath = "output\\heatmap_values_1980-2019_amp1_window12_area.mat"

println("Loading heatmap values from $filepath")
mat = matread(filepath)
#print type of mat
println("Type of mat: $(typeof(mat))") #dict
#print keys of mat
println("Keys of mat: $(keys(mat))") #duration, recurrance, amplitude
Z = mat["recurrance"]'./40 # matrix with NaNs and floats
println("Size of Z: $(size(Z))") # 303x2640'
Z_nonan = replace(Z, NaN=>0)
Z_inv = maximum(Z_nonan).-Z.+1 # invert the matrix but with 1 instead of 0 at the peak
minmax_inv = (round(minimum(Z_inv[.!isnan.(Z_inv)]),digits=1), round(maximum(Z_inv[.!isnan.(Z_inv)])))
Z_log = log.(Z_inv)
minmax_log = (round(minimum(Z_log[.!isnan.(Z_log)]),digits=1), round(maximum(Z_log[.!isnan.(Z_log)])))
Z_sqrt = sqrt.(Z_inv)
minmax_sqrt = (round(minimum(Z_sqrt[.!isnan.(Z_sqrt)]),digits=1), round(maximum(Z_sqrt[.!isnan.(Z_sqrt)])))
# make two heatmap subplots, one of Z as is, and one of max(Z)-Z
using Plots
gr()
println("Plotting heatmaps")
#prepare subplots
l = @layout [a b; c d e]
#plot
p1 = heatmap(Z, title="Recurrance", color=:turbo, colorbar=true, size=(800,400), titlefontsize=12)
p2 = heatmap(Z_inv, title="Recurrance (inverted)\n(min, max)=$minmax_inv", color=:turbo, colorbar=true, size=(800,400), titlefontsize=12)
p3 = heatmap(Z_log, title="Weight matrix (log)\n(min, max)=$minmax_log", color=:turbo, colorbar=true, size=(800,400), titlefontsize=12)
p4 = heatmap(Z_sqrt, title="Weight matrix (sqrt)\n(min, max)=$minmax_sqrt", color=:turbo, colorbar=true, size=(800,400), titlefontsize=12)
println("Putting subplots together")
p = plot(p1, p2, p3, p4, layout=(2,2), size=(800,800))
#save fig as "weight_matrix1.png"
savefig(p, "figures/weight_matrix1.png")

Z_lin1 = (Z_inv.+9)./10
minmax_lin1 = (round(minimum(Z_lin1[.!isnan.(Z_lin1)]),digits=1), round(maximum(Z_lin1[.!isnan.(Z_lin1)])))
Z_lin2 = (Z_inv.+99)./100
minmax_lin2 = (round(minimum(Z_lin2[.!isnan.(Z_lin2)]),digits=1), round(maximum(Z_lin2[.!isnan.(Z_lin2)])))
Z_lin3 = (Z_inv)./10
minmax_lin3 = (round(minimum(Z_lin3[.!isnan.(Z_lin3)]),digits=1), round(maximum(Z_lin3[.!isnan.(Z_lin3)])))

println("Plotting linearly scaled heatmaps")
p5 = heatmap(Z_lin1, title="Lin weights (+10/10), (min, max)=$minmax_lin1", color=:turbo, colorbar=true, size=(800,400))
p6 = heatmap(Z_lin2, title="Lin weights (+100/100), (min, max)=$minmax_lin2", color=:turbo, colorbar=true, size=(800,400))
p7 = heatmap(Z_lin3, title="Lin weights (+1/10), (min, max)=$minmax_lin3", color=:turbo, colorbar=true, size=(800,400))
println("Putting subplots together")
p = plot(p5, p6, p7, layout=(1,3), size=(2400,1200))
savefig(p, "figures/weight_matrix2.png")

# save the weight matrices as a .mat file
println("Saving weight matrices as .mat file")
mats = Dict("Z" => Z, "Z_inv" => Z_inv, "Z_log" => Z_log, "Z_sqrt" => Z_sqrt, "Z_lin19diff" => Z_lin1, "Z_lin2diff" => Z_lin2, "Z_lin190diff" => Z_lin3)
matwrite("output/weight_matrices.mat", mats, compress=true)
