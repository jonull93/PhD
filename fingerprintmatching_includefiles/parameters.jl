# maxtime = 60*1 # 60*30=30 minutes
# algs_size = "adaptive" # "small" or "large" or "single" or "adaptive"
# sum_func = "sse" # "abs_sum" or "sqrt_sum" or "log_sum" or "sse"
function getparameters(; maxtime=1, algs_size="single", years_per_set=3, import_sets=0, sum_func="sse",
                        nr_extreme_yrs=2, outputfolder="./output", ref_folder=false,extreme_years=["2002-2003", "1996-1997"])
    start_time = Dates.now()
    print_lock = ReentrantLock()

    #set parameters
    amplitude_resolution = 1
    window = 12
    years = 1980:2018 # cannot include 2019

    #extreme_years = ["2002-2003", "1996-1997"]#["1986-1987","1989-1990"]["2002-2003", "1996-1997"]["1989-1990","2005-2006"]#["1984-1985", "1995-1996"]#["2010-2011","2002-2003",]
    #extreme_years = ["1986-1987","1989-1990"]
    #extreme_years = ["1985-1986", "1996-1997"]
    #extreme_years = ["1995-1996", "1996-1997"]

    ref_folder == false && (ref_folder = find_max_ref_folder(outputfolder))

    years_to_add = years_per_set - nr_extreme_yrs # number of years to add to the extreme years for each combination
    years_to_optimize = years_to_add
    optimize_all = years_to_optimize == years_per_set
    years_not_optimized = years_per_set - years_to_optimize

    printstyled("-- Optimizing for $years_to_optimize year(s) out of $years_per_set -- \n"; color=:red, bold=true)

    if maxtime == "full"
        maxtime = (years_per_set+1)*60 
        printstyled("maxtime is set to $(maxtime/60) minutes\n"; color=:green)
    elseif maxtime == "brief"
        maxtime = 0.1
        printstyled("maxtime estimated to $(maxtime) seconds\n"; color=:green)
    end
    if years_to_optimize == 1
        printstyled("There is only one year to 'optimize', so only the single viable weight will be evaluated\n"; color=:green)
        maxtime = 0.1
        algs_size = "single"
    end

    if optimize_all && years_to_optimize == years_per_set
        optimize_all = true
        printstyled("All years will be optimized, so optimize_all will be set to true\n"; color=:green)
    end

    alglist = Dict(
        "large" => [:generating_set_search, :adaptive_de_rand_1_bin_radiuslimited, :simulated_annealing, :probabilistic_descent,
                    :pso, :adaptive_de_rand_1_bin, :dxnes],
        "small" => [:pso, :probabilistic_descent, :adaptive_de_rand_1_bin],
        "single" => [:adaptive_de_rand_1_bin_radiuslimited] #adaptive_de_rand_1_bin_radiuslimited() is recommended in the bboxoptim documentation
    )
    if maxtime >= 29*60 # 29 minutes
        alglist["adaptive"] = alglist["single"]
    elseif maxtime > 60 # 1 minute
        alglist["adaptive"] = [:probabilistic_descent, :adaptive_de_rand_1_bin]
    else
        alglist["adaptive"] = alglist["single"] # at less than 1 minute, manual mode is used anyway so the alg doesn't matter
    end
    BBO_algs = alglist[algs_size]

    return (; start_time, print_lock, amplitude_resolution, window, years, extreme_years, ref_folder, maxtime,
            algs_size, BBO_algs, years_per_set, import_sets, sum_func, nr_extreme_yrs,
            years_to_add, years_to_optimize, years_not_optimized, optimize_all)
end

function find_max_ref_folder(parent_directory)
    ref_folders = filter(x -> occursin(r"^ref\d+$", x), readdir(parent_directory))
    isempty(ref_folders) ? nothing : "ref" * string(maximum(parse(Int, replace(x, "ref" => "")) for x in ref_folders))
end
