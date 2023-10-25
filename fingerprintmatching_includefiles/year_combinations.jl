function makecombinations(use_jump, params)
    (; years, extreme_years, nr_extreme_yrs, years_to_add, ref_folder, amplitude_resolution, window, import_sets) = params
    (use_jump && import_sets != 0) && printstyled("use_jump is 'true', so no sets will be imported\n"; color=:red)

    #sleep_time=60*60*1;println("Sleeping for $(sleep_time/3600) hr");sleep(sleep_time)
    # years_to_add scales insanely with the number of years, so it is not recommended to use more than 2

    years_list = map(x -> string(x, "-", x+1), years)
    years_list = vcat(years_list,[i for i in extreme_years if !(i in years_list)]) # if some years has been excluded, make sure to add back the extreme years

    # Load mat data
    total_year = "1980-2019"
    ref_full = matread("output\\$ref_folder\\heatmap_values_$(total_year)_amp$(amplitude_resolution)_window$(window)_area.mat")
    ref_mat = ref_full["recurrance"]
    ref_mat[isnan.(ref_mat)].= 0
    ref_y = ref_full["duration"][:,1]
    ref_x = ref_full["amplitude"][1,:]
    printstyled("\nImported total matrix $(size(ref_mat)) for $(total_year) \n"; color=:green)
    use_jump && return (; ref_mat, ref_y=Int[], ref_x=Float64[], year_combinations=combinations(years_list, 2), years_list,
                        weights=Dict(), queue=Queue{Any}(), cores=0, all_combinations=[])
    #printstyled("Sum of extreme rows: $(sum(ref_mat[1,:])) and $(sum(ref_mat[end,:])) \n"; color=:cyan)
    #printstyled("Sum of extreme columns: $(sum(ref_mat[:,1])) and $(sum(ref_mat[:,end])) \n"; color=:cyan)
    # load weight matrices to be used with the error func sum_weight_mat, see git\python\figures\weight_matrix#.png for visuals
    #=
    weight_matrices = matread("output/weight_matrices.mat", )
    weight_matrix_lin19diff = weight_matrices["Z_lin19diff"]
    weight_matrix_lin190diff = weight_matrices["Z_lin190diff"]
    weight_matrix_sqrt = weight_matrices["Z_sqrt"]  # min = 1, max = 14
    =#

    # Generate combinations of years to optimize match for
    local year_combinations = []
    weights = Dict()
    queue = Queue{Any}()
    cores = Threads.nthreads()
    all_combinations = []
    if import_sets > 0
        # read folder_name from results/most_recent_results.txt
        folder_name = readlines("results/$ref_folder/most_recent_results.txt")[1]
        # read folder_name/best_100.json, or skip to the else-block if the file does not exist
        if !isfile("$folder_name/best_$import_sets.json")
            error("File $(folder_name)/best_$import_sets.json does not exist")
            #sleep(5)
            #@goto skip_import
        end
        best_100 = JSON.parsefile("$(folder_name)/best_$import_sets.json")
        # add each item in best_100 to all_combinations and queue
        for item in best_100
            enqueue!(queue,item)
            push!(all_combinations,item)
        end
        # remove all items from years if they are not found in any list in all_combinations
    else
        #@label skip_import
        printstyled("Building combinations instead of importing! \n"; color=:red)
        println("Years: $(years_list)")
        println("Number of years: $(length(years_list))")
        good_candidates = [
        ["1986-1987", "1989-1990", "1982-1983", "1991-1992", "1996-1997", "2004-2005", "2018-2019"],
        ["1986-1987", "1989-1990", "1982-1983", "1991-1992", "1996-1997", "2004-2005", "2016-2017"],
        ["1986-1987", "1989-1990", "1982-1983", "1991-1992", "1996-1997", "2004-2005"],
        ["2002-2003", "1996-1997", "1980-1981", "1981-1982", "1992-1993", "2003-2004", "2018-2019", "1982-1983"],
        ["1986-1987", "1989-1990", "1980-1981", "1981-1982", "1992-1993", "2003-2004", "2018-2019", "1982-1983"],
        ["1986-1987", "1989-1990", "1981-1982", "1985-1986", "1988-1989", "1999-2000", "2016-2017", "1982-1983"],
        ["2002-2003", "1996-1997", "1982-1983", "1990-1991", "1994-1995", "2008-2009", "2010-2011", "2015-2016"],
        ["2002-2003", "1996-1997", "1993-1994", "1999-2000", "2000-2001", "2003-2004", "2010-2011", "2011-2012"],
        ["1985-1986", "1996-1997", "1984-1985", "1988-1989", "1989-1990", "1991-1992", "2004-2005"],
        ["1985-1986", "1996-1997", "1993-1994", "2000-2001", "2003-2004", "2010-2011", "2011-2012"],
        ["2002-2003", "1996-1997", "1986-1987", "1995-1996", "2003-2004", "2014-2015", "2016-2017"],
        ["2002-2003", "1996-1997", "1980-1981", "1981-1982", "1992-1993", "2003-2004", "2018-2019"],
        ["2002-2003", "1996-1997", "1993-1994", "2012-2013", "2013-2014"],
        ["2002-2003", "1996-1997", "1981-1982", "2014-2015", "2017-2018"],
        ["1995-1996", "1996-1997", "1993-1994", "2012-2013", "2013-2014"],
        ["1995-1996", "1996-1997", "1982-1983", "1999-2000", "2002-2003"],
        ["1981-1982", "1982-1983", "1985-1986", "2018-2019"],
        ["2000-2001", "2002-2003", "2014-2015", "2017-2018"],
        ["1980-1981", "1992-1993", "1996-1997", "2014-2015"],
        ["2002-2003", "1996-1997", "2003-2004", "2009-2010"],
        ["2002-2003", "1996-1997", "2014-2015"],
        ["1981-1982", "2014-2015", "2016-2017"],
        ["1981-1982", "1999-2000", "2016-2017"],
        ["2002-2003", "1996-1997", "2014-2015"],
        ["2000-2001", "2016-2017"]
        ]
        extreme_year_combinations = combinations(extreme_years, nr_extreme_yrs)
        for extreme_year_set in extreme_year_combinations
            years_to_use = [i for i in years_list if !(i in extreme_year_set)]
            if length(years_to_use) >= years_to_add
                year_combinations = combinations(years_to_use, years_to_add)
                for combination in year_combinations
                    case = copy(extreme_year_set)
                    append!(case, combination)
                    #enqueue!(queue,case)
                    push!(all_combinations,case)
                end
            end
        end
        # add all combinations to the queue, but add the good_candidates, if in all_combinations, to the front of the queue
        for candidate in good_candidates
            if candidate in all_combinations
                enqueue!(queue, candidate)
            end
        end
        for combination in all_combinations
            if !(combination in good_candidates)
                enqueue!(queue, combination)
            end
        end
    end

    return (; ref_mat, ref_y, ref_x, year_combinations, years_list, weights, queue, cores, all_combinations)
end
