function optimize_manual(cfd_data, combos, params)
    (; maxtime, print_lock, algs_size, BBO_algs, sum_func, years_to_add, years_to_optimize, years_not_optimized, optimize_all) = params
    (; queue, cores, ref_mat) = combos

    #dequeue!(queue)  # remove the first element
    #dequeue!(queue)  # remove the second element
    #print number of all_combinations
    println("Number of combinations: $(length(queue))")
    threads_to_start = num_threads(queue, cores)

    #printstyled("At around 25 s per combination, this will take $(round(length(queue)*25/60)) minutes\n"; color=:green)
    #printstyled("At around 25 s per combination and $(cores) cores, this will take $(round(length(queue)*25/60/min(length(queue),cores),sigdigits=2)) minutes with multi-threading\n"; color=:green)
    
    scaled_ref_mat = ref_mat ./ 40

    println("Starting $(threads_to_start) threads (use ´julia --threads $(Sys.CPU_THREADS) script_name.jl´ to use max cores)") # returns "Starting 63 threads"

    best_weights = Dict()
    best_errors = Dict()
    best_alg = Dict()

    hours_to_solve = Int(div(length(queue)*maxtime/60/threads_to_start*length(BBO_algs),60))
    minutes_to_solve = round((length(queue)*maxtime/60/threads_to_start*length(BBO_algs))%60)
    printstyled("At $maxtime s per solve, $(length(BBO_algs)) algs and $(threads_to_start) threads, this will take $(hours_to_solve)h$(minutes_to_solve)m with multi-threading\n"; color=:green)
    longest_alg_name = maximum([length(string(alg)) for alg in BBO_algs])
    #print, in yellow and with ######-separation, the maxtime and algs that the loop is ran with
    global_best = 9e9
    global_midpoint_tracker = 0  # keeps track of the highest midpoint among solutions that are still good (within x% of the best solution)
    printstyled("############# -- Starting optimization loop with maxtime=$(maxtime)s and algs_size '$(algs_size)' -- #############\n"; color=:yellow)
    initial_guesses_3 = [
        # considering the solution space as a triangle where each corner is 100% of one axis such as (1,0,0)
        # let some initial guesses be the center of the triangle and on the center of the edges of the triangle
        [1/3, 1/3, 1/3], [18/40, 18/40, 4/40], [4/40, 18/40, 18/40], [18/40, 4/40, 18/40],
        # then divide the triangle into 4 new triangles (like a triforce) and do the same again
        [2/3, 1/6, 1/6], [1/6, 2/3, 1/6], [1/6, 1/6, 2/3], # center of smaller triangles
        [1/2, 1/4, 1/4], [1/4, 1/2, 1/4], [1/4, 1/4, 1/2], # center of inner edges of smaller triangles
        #[29, 9, 2]./40, [2, 29, 9]./40, [9, 2, 29]./40, # center of outer edges of smaller triangles
        #[29, 2, 9]./40, [9, 29, 2]./40, [2, 9, 29]./40, # center of outer edges of smaller triangles
        ]
    initial_guesses_4 = [
        [1/4,1/4,1/4,1/4], [15/40,15/40,5/40,5/40], [15/40,5/40,15/40,5/40],
        [15/40,5/40,5/40,15/40], [5/40,15/40,15/40,5/40], [5/40,15/40,5/40,15/40],
        [5/40,5/40,15/40,15/40]
        ]
    initial_guesses_5 = [
        [1/5,1/5,1/5,1/5,1/5], [5/40,5/40,10/40,10/40,10/40], [5/40,10/40,5/40,10/40,10/40],
        [5/40,10/40,10/40,5/40,10/40], [5/40,10/40,10/40,10/40,5/40], [10/40,5/40,5/40,10/40,10/40],
        [10/40,5/40,10/40,5/40,10/40], [10/40,5/40,10/40,10/40,5/40], [10/40,10/40,5/40,5/40,10/40],
        [10/40,10/40,5/40,10/40,5/40], [10/40,10/40,10/40,5/40,5/40]
        ]
    initial_guesses_6 = [
        [1/6,1/6,1/6,1/6,1/6,1/6], 
        [4/40, 4/40, 8/40, 8/40, 8/40, 8/40],
        [4/40, 8/40, 4/40, 8/40, 8/40, 8/40], 
        [4/40, 8/40, 8/40, 4/40, 8/40, 8/40],
        [4/40, 8/40, 8/40, 8/40, 4/40, 8/40], 
        [4/40, 8/40, 8/40, 8/40, 8/40, 4/40],
        [8/40, 4/40, 4/40, 8/40, 8/40, 8/40],
        [8/40, 4/40, 8/40, 4/40, 8/40, 8/40], 
        [8/40, 4/40, 8/40, 8/40, 4/40, 8/40],
        [8/40, 4/40, 8/40, 8/40, 8/40, 4/40],
        [8/40, 8/40, 4/40, 4/40, 8/40, 8/40],
        [8/40, 8/40, 4/40, 8/40, 4/40, 8/40],
        [8/40, 8/40, 4/40, 8/40, 8/40, 4/40],
        [8/40, 8/40, 8/40, 4/40, 4/40, 8/40],
        [8/40, 8/40, 8/40, 4/40, 8/40, 4/40],
        [8/40, 8/40, 8/40, 8/40, 4/40, 4/40]
        ]
    initial_guesses_2 = [
        [1/2, 1/2], [1/3, 2/3], [2/3, 1/3], [6/40, 34/40], [34/40, 6/40] #, [2/40, 38/40], [38/40, 2/40]
        ]
    initial_guesses_1 = [
        [1.]
        ]
    initial_guesses = initial_guesses_3

    bounds = (0+years_not_optimized/40, 1-years_not_optimized/40)
    # if we are not optimizing all years, that means we are optimizing the last years_to_add years
    # so initial_guesses should be the nr equal to years_to_add
    if years_to_optimize == 1
        initial_guesses = initial_guesses_1
        printstyled("Initial guesses: initial_guesses_1\n"; color=:yellow)
    elseif years_to_optimize == 2
        initial_guesses = initial_guesses_2
        printstyled("Initial guesses: initial_guesses_2\n"; color=:yellow)
    elseif years_to_optimize == 3
        initial_guesses = initial_guesses_3
        printstyled("Initial guesses: initial_guesses_3\n"; color=:yellow)
    elseif years_to_optimize == 4
        initial_guesses = initial_guesses_4
        printstyled("Initial guesses: initial_guesses_4\n"; color=:yellow)
    elseif years_to_optimize == 5
        initial_guesses = initial_guesses_5
        printstyled("Initial guesses: initial_guesses_5\n"; color=:yellow)
    elseif years_to_optimize == 6
        initial_guesses = initial_guesses_6
        printstyled("Initial guesses: initial_guesses_6\n"; color=:yellow)
    else
        error("years_to_optimize = $(years_to_optimize) is not supported")
    end
    # decrease all values in the lists in initial_guesses by 1/40
    for i in 1:length(initial_guesses)
        initial_guesses[i] = initial_guesses[i] .- years_not_optimized/40/years_to_add
    end
    !optimize_all && println("decreased each initial guess by $(years_not_optimized/40/years_to_add) so that the initial guesses sum to $(sum(initial_guesses[1])+years_not_optimized/40)")
    #println(initial_guesses)

    msums = [zeros(size(cfd_data["1984-1985"])) for i = 1:threads_to_start]

    average_time_to_solve_per_thread = [0. for i in 1:threads_to_start]
    Threads.@threads for thread = 1:threads_to_start
        time_to_solve_array = [0.]
        #sleep for 250 ms to stagger thread starts
        #time_to_sleep = 0.5*thread
        #sleep(time_to_sleep)
        global_best
        global_midpoint_tracker
        sum_func
        while true
            if length(queue) == 0
                #println("Nothing to do")
                average_time_to_solve_per_thread[thread] = mean(time_to_solve_array)
                break
            end
            start_time = Dates.now()
            local case
            lock(print_lock) do
                case = dequeue!(queue)
            end
            # if thread == 1 || maxtime > 60
            #     lock(print_lock) do
            #         printstyled("Thread $(thread) started working on $(case) at $(Dates.format(now(), "HH:MM:SS")), $(length(queue)) left in queue\n"; color=:cyan)
            #     end
            # end
            matrices = [cfd_data[year] for year in case]# if !(year in extreme_years && !optimize_all)]
            if length(matrices) == 0
                printstyled("\n!! No matrices found for $(case) in thread $(thread)\n")
                continue
            end
            if thread == 1 && global_best > 1e8
                printstyled("There are $(length(matrices)) matrices sent to diff()\n"; color=:magenta)
            end
            # Use an optimization algorithm to find the best weights

            # a vector w that is the same length as the number of matrices and equals 1/number of matrices
            # w = ones(length(matrices)) ./ length(matrices)
            #upper = ones(length(matrices))
            #lower = zeros(length(matrices))
            ###----------------------------
            ### SET THE ERROR FUNCTION TO OPTIMIZE WITH HERE
            ###----------------------------
            
            m_sum = msums[thread]
            if sum_func == "sse"
                opt_func = x -> sse(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
            elseif sum_func == "abs_sum"
                opt_func = x -> abs_sum(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
            elseif sum_func == "sqrt_sum"
                opt_func = x -> sqrt_sum(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
            elseif sum_func == "log_sum"
                opt_func = x -> log_sum(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
            else
                error("Invalid sum_func")
            end

            local alg_solutions = Dict()
            # define paramters for maxtime and midpoint_factor_for_skipping
            local maxtime_manual = 9
            local midpoint_factor_for_skipping = 2.6 # from testing, it seems like 25% is about as much as the error can get improved (for abs_sum), though this decreases as the number of years increases
            # for sse, the improvement seems like it can be a lot higher!
            sum_func != "sse" && (midpoint_factor_for_skipping = 1.75)
            if maxtime < maxtime_manual
                if thread == 1 && global_best > 1e9
                    lock(print_lock) do
                        printstyled("maxtime is less than 61 seconds, testing starting points manually\n"; color=:magenta)
                    end
                end
                #manually test the initial guesses one by one using opt_func() instead of the BBOptim.jl package
                local best_guess = (0,Inf)
                local x = initial_guesses[1]
                local e = opt_func(x)
                local midpoint_error = e
                best_guess = (x,e)
                #=
                lock(print_lock) do # trying this to stop an error later when trying to sort best_errors, possibly because best_errors got corrupted by the multiple threads
                    best_weights[case] = best_guess[1]
                    best_errors[case] = best_guess[2]
                    best_alg[case] = "manual mid-point"
                end
                =#
                if midpoint_error < global_best*midpoint_factor_for_skipping
                    for i in 2:length(initial_guesses)
                        local x = initial_guesses[i]
                        local e = opt_func(x)
                        if e < best_guess[2]
                            best_guess = (x,e)
                        end
                    end
                end
                # if the thread is the first one, print which starting point is being tested
                #if thread == 1
                #    lock(print_lock) do
                #        printstyled("  Thread $(thread) finished working on $(case) at $(Dates.format(now(), "HH:MM:SS")), after $((Dates.now()-start_time)/Dates.Millisecond(1000)) s\n"; color=:green)
                #         printstyled("  Midpoint error was $(round(midpoint_error/global_best,digits=2)) of the best\n"; color=:yellow)
                #         #printstyled("  Error = $(round(best_guess[2],digits=1)) for $(round.(best_weights[case],digits=3))\n"; color=:white)
                #         printstyled("best so far = $(round(global_best))\n"; color=:magenta)
                #    end
                #end
                lock(print_lock) do
                    best_weights[case] = best_guess[1]
                    best_errors[case] = best_guess[2]
                    #let best_alg say "-20% from mid-point" if the best guess is 20% from the mid-point guess, since there is no alg anyway
                    best_alg[case] = "$(round(Int,(best_guess[2]-midpoint_error)/midpoint_error*100))% from mid-point"
                end
                if best_guess[2] <= global_best
                    lock(print_lock) do
                        # prepare a string that indicates +/-% from the mid-point error to the previous best
                        # if the midpoint_error was +30% of the previous best, the string will be "+30%" specifically with the + sign
                        midpoint_error_string = "$(round(Int,(midpoint_error-global_best)/global_best*100))%"
                        if midpoint_error > global_best
                            midpoint_error_string = "+$(midpoint_error_string)"
                        end
                        global_midpoint_tracker *= best_guess[2]/global_best
                        global_best = best_guess[2]
                        printstyled("-> New global best: $(round(Int,best_guess[2])) at $(Dates.format(now(), "HH:MM:SS")) for $case\n"; color=:red)
                        printstyled("  Midpoint error was $midpoint_error_string of the best, and average time per case is now $(mean(time_to_solve_array))\n"; color=:yellow)
                    end
                else
                    #printstyled("\n"; color=:white)
                    if best_guess[2] < global_best*1.1
                        lock(print_lock) do
                            #printstyled(" Only $(round(best_guess[2]/global_best,digits=2)) from the best with the midpoint error at $(round(midpoint_error/global_best,digits=2))\n"; color=:blue)
                            if midpoint_error > global_midpoint_tracker
                                global_midpoint_tracker = midpoint_error
                            end
                        end
                    end
                    
                end
                #add the time it took to solve this case (in not rounded seconds) to the array time_to_solve_array
                push!(time_to_solve_array, (Dates.now()-start_time)/Dates.Millisecond(1000))

            else # if the maxtime is not less than maxtime_manual, use the BBOptim.jl package
                for alg in BBO_algs
                    #print the next line only if thread==1
                    if thread == 1
                        printstyled("Trying $(alg) with bounds = $bounds and $(length(initial_guesses[1])) dims\n"; color=:yellow)
                        hours_to_solve = Int(div(length(queue)*maxtime/60/threads_to_start*length(BBO_algs),60))
                        minutes_to_solve = round((length(queue)*maxtime/60/threads_to_start*length(BBO_algs))%60)
                        printstyled("Estimated time left: $(hours_to_solve)h$(minutes_to_solve)m\n"; color=:yellow)
                    end
                    local res
                    try
                        res = bboptimize(opt_func, initial_guesses; method=alg, NumDimensions=years_to_optimize,
                                            SearchRange=bounds, MaxTime=maxtime, TraceInterval=2, TraceMode=:silent) #TargetFitness=88355.583298,FitnessTolerance=0.0001
                    catch e
                        println("$case, $alg failed with error: \n$e")
                        println("retrying..")
                        try
                            res = bboptimize(opt_func, initial_guesses; method=alg, NumDimensions=years_to_optimize,
                                            SearchRange=bounds, MaxTime=maxtime, TraceInterval=2, TraceMode=:silent) #TargetFitness=88355.583298,FitnessTolerance=0.0001
                        catch e
                            printstyled("$case, $alg failed AGAIN with error: \n$e"; color=:red)
                        end
                    end
                    local weights_list = best_candidate(res)
                    local e = opt_func(weights_list)
                    alg_solutions[alg] = (e, weights_list)
                end
                #print each alg's solution
                lock(print_lock) do
                    _best_alg = BBO_algs[argmin([alg_solutions[alg][1] for alg in BBO_algs])]
                    best_errors[case] = alg_solutions[_best_alg][1]
                    years_not_optimized==0 ? best_weights[case] = alg_solutions[_best_alg][2] : best_weights[case] = vcat([1/40 for i in 1:years_not_optimized],alg_solutions[_best_alg][2])
                    best_alg[case] = _best_alg
                    if alg_solutions[_best_alg][1] < global_best
                        printstyled("years: $(case)"; color=:green)
                        printstyled("       <-- best so far\n"; color=:red)
                        global_best = best_errors[case]
                    else
                        printstyled("years: $(case)\n"; color=:green)
                    end
                    # find for which alg the error is the lowest
                    for alg in BBO_algs
                        print("  $(round(alg_solutions[alg][1],digits=1)) $(round.(alg_solutions[alg][2],digits=3)) $(rpad(round(sum(alg_solutions[alg][2]),digits=3)+years_not_optimized*1/40,4)) $(alg)")
                        if alg == _best_alg
                            printstyled(" <-\n"; color=:green)
                        else
                            print("\n")
                        end

                    end
                end
                #add the time it took to solve this case (in not rounded seconds) to the array time_to_solve_array
                push!(time_to_solve_array, (Dates.now()-start_time)/Dates.Millisecond(1000))
                #if case not in best_errors
                if !(case in keys(best_errors))
                    printstyled("did not find $case in best_errors\n"; color=:red)
                    best_errors[case] = alg_solutions[_best_alg][1]
                    best_weights[case] = alg_solutions[_best_alg][2]
                    best_alg[case] = _best_alg
                end
                if !(case in keys(best_errors))
                    printstyled("AGAIN did not find $case in best_weights\n"; color=:red)
                    lock(print_lock) do
                        best_errors[case] = alg_solutions[_best_alg][1]
                        best_weights[case] = alg_solutions[_best_alg][2]
                        best_alg[case] = _best_alg
                    end
                end
                if !(case in keys(best_errors))
                    printstyled("AGAIN AGAIN did not find $case in best_alg\n"; color=:red)
                    error("failed to add $case to best_errors")
                end
            end
        end
    end

    opt_func_str = "$sum_func(x) + weights_penalty(x,fixed_weights=years_not_optimized,slack_distance=0.007,amplitude=2e5)" #sigmoid((sum(x)-1.011)*1000) +

    return (; global_best, global_midpoint_tracker, best_errors, best_weights, best_alg, opt_func_str, average_time_to_solve_per_thread)
end



function num_threads(queue, cores)
    threads_to_start = min(length(queue),cores)
    consequtive_runs = div(length(queue),threads_to_start,RoundUp)
    for i in threads_to_start-1:-1:1
        if div(length(queue),threads_to_start-i,RoundUp) == consequtive_runs
            printstyled("Reducing number of threads to $(threads_to_start-i) since this wont affect time to complete queue\n"; color=:red)
            threads_to_start -= i
            break
        end
    end
    return threads_to_start
end

function sigmoid(x)
    return 1 / (1 + exp(-x))
end

function weights_penalty(weights;fixed_weights=0,slack_distance=0.007,amplitude=2e6)
    weight_sum = sum(weights)+fixed_weights*1/40
    penalty = (sigmoid((weight_sum-(1+slack_distance))*1000) + sigmoid(((1-slack_distance)-weight_sum)*1000))*amplitude
    return penalty
end

function sse(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
    diff = diff_sum_weighted_mats(m_sum, matrices, x, scaled_ref_mat, years_not_optimized)
    return dot(diff,diff) + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
end

function abs_sum(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
    diff = diff_sum_weighted_mats(m_sum, matrices, x, scaled_ref_mat, years_not_optimized)
    #if diff == false
    #    return 0
    #end
    #result = 0.0
    #@inbounds @simd for i in eachindex(diff)
    #    result += abs(diff[i])
    #end
    return sum(abs.(diff)) + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
    #return result
end

function sqrt_sum(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
    diff = diff_sum_weighted_mats(m_sum, matrices, x, scaled_ref_mat, years_not_optimized)
    result = 0.0
    @inbounds @simd for i in eachindex(diff)
        result += sqrt(abs(diff[i]))
    end
    return result + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
end

function log_sum(x, m_sum, matrices, scaled_ref_mat, years_not_optimized)
    diff = diff_sum_weighted_mats(m_sum, matrices, x, scaled_ref_mat, years_not_optimized)
    diff = replace(diff, 0 => NaN)
    e = abs.(log10.(abs.(diff)))
    # return sum of e but ignoring NaN
    #penalty = sigmoid((sum(x)-1.011)*1000)+sigmoid((0.989-sum(x))*1000)
    return sum(e[.!isnan.(e)]) + weights_penalty(x, fixed_weights=years_not_optimized, slack_distance=0.007, amplitude=2e5)
end

function diff_sum_weighted_mats(m_sum, matrices, weights, scaled_ref_mat, years_not_optimized)
    # if matrices and weights have different lengths, it is assumed that the first matrices should have weights 1/40
    # the remaining matrices should have weights from the weights array
    fill!(m_sum, 0.0)
    if length(matrices) > length(weights)
        for i in 1:years_not_optimized
            m_sum .+= matrices[i] .* 1/40 # assuming the hand-picked years' matrices are first in the list
        end
        matrices_left = @view matrices[years_not_optimized+1:end]
        #println("matrices_left = $(length(matrices_left))")
    elseif length(matrices) < length(weights)
        error("Warning: more weights than matrices\n")
    else
        matrices_left = matrices
    end
    for i in 1:length(weights)
        m_sum .+= weights[i] .* matrices_left[i]
    end
    m_sum .= m_sum .- scaled_ref_mat
    return m_sum
end
