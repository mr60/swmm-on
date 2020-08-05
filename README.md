
# SWMM-ON 

Mayra Rodriguez
University of Exeter, 2020
QUEX INSTITUTE

SWMM-ON is an interface tool between SWMM5 & Python, for data acquisition and manipulation. 

Using this tool, SWMM input files can be,

1. Used to extract information and use it in Python. This allows easy manipulation of the characteristics of the catchment studied, making it easy to generate maps and understanding available data. 
2. Modified in various ways, including rainfall changes, as well as characteristics of subcatchments and GI implementation.

The tool provides scripts for,
1. Parallelising simulations and creating/deleting input/report/output files as the simulations take place, in a simple manner. This is an advantage, as the simulation's results can be very memory intensive. This functions need to be called from the terminal & not from Jupyter Notebook, due to the characteristics of the parallelisation in Python.
2. Extracting relevant results from the report file. 
3. Extracting relevant results from the output file (in conjunction with using SWMM tool box).


## Utility tools

The folder <b>'scripts'</b> contains utility programs for various tasks. 

- sections.py
This script allows the identification of the main sections in a given SWMM input file. This allows an easy extraction and access of all the information contained in the input file for use in Python. The first function imports the input file into a Pandas' Data Frame. The second's function output is a python's Dictionary, where the keys are the name of the section and the values are Pandas' Data Frames. 

IMPORTANT NOTE!
As sometimes the columns are not filled, this may cause problems with importing the file. If you have errors, please check in the sections, if there is an incongruence with the columns and what is written in the code. 

- theinputer.py
A set of functions that allow the interaction of SWMM with Python. 
The main functions are,
1. Importing the input file into a Pandas DataFrame.
2. Modification of rainfalls and setting of rainfall in raingage. 
3. Modifies subcatchment characteristics (imperviousness, area, etc.).
4. Modifies Dry weather flow. 
5. Modifies use of GI. 
6. Obtains different results from the report file.  

- rainwally.py
The rainfall events were obtained using the Wallingford procedure and using the 50% summer profile by FSR. 
Using the storms generated, this script modifies the rainfall csv files to the correct format and inserts it correctly int the input file.

- parallel.py
Allows multiprocessing for GI scenario application. 
Functions allow to,
1. Application of LID to different subcatchments, by the modification of the input file. The parameters of the LID can be easily changed, including the area. 
2. Obtain total flood volume and flood duration, and calculate the resilience index (based on Mugume et al. 2010) at a system, subcatchment and node level. 
3. Simulate different scenarios using PySWMM. Delete input, output and report file of the created simulation scenarios. 
4. Parallelise different scenarios using multiprocessing.
5. Save the obtained results in cvs format for easy use and analysis in Python.


## General information
All the scripts are written in Python 3. They have been tested in Mac OS Catalina. 

The packages required are,

- Pandas
- Geopandas
- Numpy
- Math
- Os
- PySWMM
- Multiprocessing
- Time
- Itertools
- Tqdm
- SWMM ToolBox

## Applications
The folder <b>'examples'</b> contains examples of data extracted using SWMM-on tools, using a case-study in the United Kingdom. 
