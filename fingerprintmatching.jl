#=
fingerprintmatching:
- Julia version: 
- Author: Jonathan Ullmark
- Date of creation: 2023-01-18
- Co-author: Niclas Mattsson (JuMP model and code-juliafication)
=#

import Combinatorics: combinations
import Statistics: mean
using MAT, Optim, BlackBoxOptim, DataStructures, Dates, Printf, LinearAlgebra, Plots, JSON, XLSX, JuMP, Gurobi

#=
This script is currently set up to run with one or multiple heuristic optimization algorithms for a certain amount of time, then stop.
To circumvent the issue of spending minutes per year-combination for up to 5e5 (5 out of 39 years) combinations, the script can
be run for a very short time (maxtime="brief") initially and then rerun for the 5/25/50 best combinations.

A better solution would be to manually test all of the starting points (would probably take <1 second per combination) and then automatically 
run the longer optimization (3-6 min) for the best solutions. This would make the script more automatic .
=#

#make it clear in the command prompt that the code is running
timestamp = Dates.format(now(), "u_dd HH.MM.SS")
printstyled("\n ------ Loaded fingerprintmatching.jl at $(timestamp) ------  \n"; color=:yellow)
printstyled("To run the optimization, call the fpmatch() function\n", color=:white, bold=true)
println("  use_jump=false, maxtime=Int/\"full\"/\"brief\", years_per_set=3, import_sets=0, sum_func=\"sse\"/\"abs_sum\", nr_extreme_yrs=2\n")
println(" ex: fpmatch(use_jump=true,years_per_set=4,ref_folder=\"ref999\",extreme_years=[\"1996-1997\",\"2002-2003\"])")

include("fingerprintmatching_includefiles/parameters.jl")
include("fingerprintmatching_includefiles/year_combinations.jl")
include("fingerprintmatching_includefiles/inputdata.jl")
include("fingerprintmatching_includefiles/optimize_years.jl")
include("fingerprintmatching_includefiles/optimize_jump.jl")
include("fingerprintmatching_includefiles/output.jl")

"See getparameters() for keyword arguments."
function fpmatch(; use_jump=false, options...)
    params = getparameters(; options...)
    combos = makecombinations(use_jump, params)
    cfd_data = read_inputdata(combos, params)
    printstyled("\n ------ Starting optimization at $(Dates.format(now(), "u_dd HH.MM.SS")) ------  \n"; color=:yellow)
    if use_jump
        @time results = optimize_jump(cfd_data, combos, params)
    else
        @time results = optimize_manual(cfd_data, combos, params)
        print_results(results, combos, params)
    end
    nothing
end
