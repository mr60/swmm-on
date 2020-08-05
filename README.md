
# SWMM-ON 

Mayra Rodriguez
University of Exeter, 2020
QUEX INSTITUTE

SWMM-ON is an interface tool between SWMM5 & Python, for data adquisition and manipulation. 

Using this tool, SWMM input files can be,

1. Used to extract information and use it in Python. This allows easy manipulation of the characteristics of the catchment studied, and also easy to generate maps. 
2. Modified in various ways, including rainfall changes, as well as characteristics of subcatchments and GI implementation.

The tool provides scripts for,
1. Parallelising simulations and creating/deleting input/report/output files as the simulaitons are over, in a simple manner. This is an advantage, as the simulations results can be very memory intensive. This functions need to be called from the terminal & not from Jupyter Notebook, due to the characteristics of the parallisation in Python.
2. Extracting relevant results from the report file. 
3. Extracting relevant results from the output file (in conjunction with using SWMM tool box).


## Utility tools

Folder XXX contains utility programs for various tasks. 
- sec.py
- theinputer.py
- rainwally.py
- GRA.py

## General information
All the scripts are written in Python 3. They have been tested in Mac OS Catalina. 

The packages required are,

- Pandas
- Geopandas
- Numpy
- Math
- Os
- PySWMM
- SWMM tool box

## Examples
The folder XX contains examples of data extrated using SWMM-on tools, using a case-study in the United Kingdom. 
