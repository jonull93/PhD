function optimize_jump(cfd_data, combos, params)
    (; years_to_optimize, extreme_years, nr_extreme_yrs, ref_folder) = params
    (; years_list, ref_mat) = combos

    nyears = length(years_list)
    fixed_year_indices = [findfirst(x -> x == y, years_list) for y in extreme_years[1:nr_extreme_yrs]]
    cfd_mat = hcat((@view cfd_data[y][:] for y in years_list)...)
    ref_vect = @view ref_mat[:]

    jumpmodel = Model(Gurobi.Optimizer) # alternatively, you could install Pkg.add("Clp") and use Clp.Optimizer

    @variables jumpmodel begin
        0.0 <= Weight[1:nyears] <= 1.0
        Active_weight[1:nyears], Bin
    end

    # fix the weights for the exterem years to 1/40
    fix.(Weight[fixed_year_indices], 1/40, force=true)
    fix.(Active_weight[fixed_year_indices], 1)

    @constraints jumpmodel begin
        Link_weights_to_indicators,
            Weight .<= Active_weight

        Sum_weights,
            sum(Weight) == 1.0
        
        Fix_number_of_active_years,
            sum(Active_weight) == years_to_optimize + nr_extreme_yrs
    end

    @time @expression(jumpmodel, diff, cfd_mat * Weight - ref_vect/40)
    @time @objective(jumpmodel, Min, dot(diff, diff)/1e3)

    set_attributes(jumpmodel, "Threads" => Threads.nthreads(), "Cuts" => 1, "MIPGap" => 1e-9, "DisplayInterval" => 1)
    optimize!(jumpmodel)

    println("\nSolve status: ", termination_status(jumpmodel))
    println("Objective: ", objective_value(jumpmodel) * 1e3)

    years = (value.(Active_weight) .== 1)
    weights = round.(value.(Weight[years]), digits=4)
    @show years_list[years]
    @show weights

    println("Making folder and files..")
    foldername = "results\\$ref_folder\\JuMP\\"
    #make the folder and subfolders if they don't exist
    mkpath(foldername)
    #save the years and weights to a .txt file
    open(foldername * "optimal set for $(years_to_optimize+nr_extreme_yrs)yrs $(nr_extreme_yrs)eyrs ($(round(Int,objective_value(jumpmodel)*1e3))).txt", "w") do io
        for i in 1:length(years_list[years])
            println(io, "$(years_list[years][i]): $(weights[i])")
        end
    end
    
end
