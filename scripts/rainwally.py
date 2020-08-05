
'''
 ___      _       __      _ _  __      __    _ _ _            __            _
 | _ \__ _(_)_ _  / _|__ _| | | \ \    / /_ _| | (_)_ _  __ _ / _|___ _ _ __| |
 |   / _` | | ' \|  _/ _` | | |  \ \/\/ / _` | | | | ' \/ _` |  _/ _ \ '_/ _` |
 |_|_\__,_|_|_||_|_| \__,_|_|_|   \_/\_/\__,_|_|_|_|_||_\__, |_| \___/_| \__,_|
                                                        |___/

Makes dataframes with the Wallinford raifall data to use in the SWMM input file.


Mayra Rodriguez, 2020
CWS, University of Exeter

'''
#Import packages
#=======================
import sys, os
import math
import numpy as np
import pandas as pd

arr=os.listdir('./storms')
rainfalls={}

for i in arr:
    storm=pd.read_csv('storms/'+i)
    rainfalls[i]=storm


def givemetherain(name):
    '''
    Given the name of a rainfall series, it gives back the rainfall timeseries dataframe

    Input
    -----
    name: name of the rainfall
    Available timeseries

    1,2,5,10,20,50,100 years

    5,10,15,30,60 mins


    Output
    ------
    rts: rainfall timeseries in the form of a dataframe
    '''

    rts=rainfalls[name]

    return rts
