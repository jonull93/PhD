# Electricity System Capacity Expansion Modeling

## Introduction

This repository is part of a broader research focused on electricity system modeling and analysis using a GAMS model. The primary focus of this project is on the management of net load variations in the electricity system. Most scripts herein have been used at some point (and in some version) for the following publications:
- [Actuating the European Energy System Transition: Indicators for Translating Energy Systems Modelling Results into Policy-Making](https://doi.org/10.3389/fenrg.2021.677208)
- [Inclusion of frequency control constraints in energy system investment modeling](https://doi.org/10.1016/j.renene.2021.03.114)
- [Optimization modeling of frequency reserves and inertia in the transition to a climate-neutral electricity system](https://research.chalmers.se/en/publication/530495)
- [Frequency reserves and inertia in the transition to future electricity systems](https://doi.org/10.1007/s12667-023-00568-1)
- "Potential revenue from reserve market participation in wind power- and solar power-dominated electricity grids" submitted for publication
- "Selecting weather-years to represent high net load events in electricity system capacity expansion models" submitted for publication


## Repository Contents

This repository includes several scripts primarily written in Python and Julia, that are used for various stages of data processing, model running, and visualization. The key scripts are:

**Set Building**

1.  `fingerprintmatching.jl`
2.  `year_selection.py`
3.  `profile_analysis.py`
4.  `figure_CFD.py`

These scripts are used for building representative sets of typical and particularly challenging net-load events. This is done by running the `year_selection` script first, followed by `fingerprintmatching` script (with a start-up parameter of max_time=1 min), and then `year_selection` script again. After these, `fingerprintmatching` is run again with a longer max_time option (60-120 mins). 

**Data Processing** 

5.  `gdx_processing.py`
6.  `gdx_processing_functions.py`
7.  `get_from_gams_db.py`

These scripts are used for reading the GAMS output in gdx format and turning it into .pickle files for further processing and analysis. This is done by setting up variables in, and running, `gdx_processing.py`.

**Visualization** Several other scripts in this repository are used for generating figures out of the model results stored in the .pickle files created by 5.


## Dependencies

The Data Processing scripts use the `gdx-reader` package developed by [Joel Goop](https://github.com/joelgoop/gdx-reader) and are run from an Anaconda environment exported to `environment_pygams.yml`. All other scripts are ran in an environment with a more recent version of Python, found in `environment_py311.yml`

To install these environments in the Anaconda command prompt, this command should do the trick:
```
conda env create -f environment[..].yml
```
Note that you may have to manually install the GAMS API package by running: 
```
python "C:\GAMS\37\apifiles\Python\api_36\setup.py" install
```

If the environment packages provided do not work then you may find more success using the `incomplete_pygams.yml` file or following the instructions https://github.com/joelgoop/gdx-reader, then manually installing the missing packages using `pip install package_name_1` in the Anaconda environment.

## Input 

Input for running these scripts is either provided in the `/input` folder or `.gdx` files generated from the Multinode GAMS model. 

## Contact

If you have questions or need further clarification, feel free to reach out to Jonathan Ullmark at <ins>jonathan.ullmark@chalmers.se</ins>.

## License

This repository is licensed under the Creative Commons Attribution 4.0 International license (CC BY 4.0). You are free to share and adapt the material for any purpose, even commercially, as long as you give appropriate credit, provide a link to the license, and indicate if changes were made.
