function read_inputdata(combos, params)
    (; ref_folder, amplitude_resolution, window) = params
    (; years_list, ref_mat) = combos

    cfd_data = Dict()
    y_data = Dict()
    x_data = Dict()
    for year in years_list
        filename = "output\\$ref_folder\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area_padded.mat"
        filename2 = "output\\$ref_folder\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area.mat"
        local temp
        try
            temp = matread(filename)
        catch e
            try
                temp = matread(filename2)
            catch e
                try
                    temp = matread(filename3)
                catch e
                    error("Could not find file for $(year)")
                end
            end
        end
        cfd_data[year] = replace(temp["recurrance"], NaN => 0)
        #take [:,1]or [1,:]if ndims==2 otherwise just take the whole thing
        y_data[year] = getindex(temp["duration"], :, 1)
        x_data[year] = getindex(temp["amplitude"], 1, :)
        if size(cfd_data[year]) == size(ref_mat)
            #println("Matrix for $(year) is already the same size as the reference matrix")
            continue # move on to the next year
        end
        if length(findall(in(x_data[year]),ref_x))<length(x_data[year]); error("Non-matching x-axes"); end
        printstyled("Padding the matrix $(size(cfd_data[year])) for $(year) ..\n"; color=:green)
        columns_to_add = count(x -> x > maximum(x_data[year]), ref_x)
        #println("Adding $(columns_to_add) columns")
        xpad = zeros((size(cfd_data[year])[1],columns_to_add))
        cfd_data[year] = hcat(cfd_data[year],xpad)
        #println("Added columns - new size is $(size(cfd_data[year]))")
        start_rows = count(y -> y < minimum(y_data[year]), ref_y)
        end_columns = count(y -> y > maximum(y_data[year]), ref_y)
        #println("Adding $(start_rows) rows at the top and $(end_columns) rows at the bottom")
        #instead of printing how many rows and columns are added, print a warning of none are added
        if start_rows == 0 && end_columns == 0 && columns_to_add == 0
            printstyled("Warning: no rows or columns are added to the matrix for $(year)\n"; color=:red)
        end
        ypad1 = zeros((start_rows,size(cfd_data[year])[2]))
        ypad2 = zeros((end_columns,size(cfd_data[year])[2]))
        cfd_data[year] = vcat(ypad1,cfd_data[year],ypad2)
        if size(cfd_data[year]) != size(ref_mat)
            #print in red the sizes of cfd_data[year] and ref_mat
            printstyled("size(cfd_data[year]) = $(size(cfd_data[year])) and size(ref_mat) = $(size(ref_mat))\n"; color=:red)
            error("The dimensions of the matrix for $(year) are not the same as the reference matrix")
        end
        # save padded mat to filename but replace .mat with _padded.mat
        matwrite("output\\$ref_folder\\heatmap_values_$(year)_amp$(amplitude_resolution)_window$(window)_area_padded.mat",
            Dict("recurrance" => cfd_data[year], "duration" => ref_y, "amplitude" => ref_x),
            compress=true)
    end

    return cfd_data
end
