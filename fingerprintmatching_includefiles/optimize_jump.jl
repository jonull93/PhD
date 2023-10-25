function optimize_jump(cfd_data, combos, params)
    (; years_to_optimize, extreme_years, nr_extreme_yrs) = params
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
            sum(Active_weight) == years_to_optimize + length(extreme_years[1:nr_extreme_yrs])
    end

    @time @expression(jumpmodel, diff, cfd_mat * Weight - ref_vect/40)
    @time @objective(jumpmodel, Min, dot(diff, diff)/1e3)

    set_attributes(jumpmodel, "Threads" => Threads.nthreads(), "Cuts" => 1, "MIPGap" => 1e-9, "DisplayInterval" => 1)
    optimize!(jumpmodel)

    println("\nSolve status: ", termination_status(jumpmodel))
    println("Objective: ", objective_value(jumpmodel) * 1e3)

    years = (value.(Active_weight) .== 1)
    weights = value.(Weight[years])
    @show years_list[years]
    @show weights
end
