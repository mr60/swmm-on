'''
                                            ,~~_
                                            |/\ =_ _ ~
                                             _( )_( )\~~
                                             \,\  _|\ \~~~
                                                \`   \
                                                `    `

                                    University of EXETER, 2020
                                           
                                           Mayra Rodriguez
Multiprocessing for GI application

'''

import sys, os
import math
import numpy as np
import pandas as pd
import geopandas as gpd


from shapely.geometry import Point, Polygon, LineString

import shapely.wkt

import pyswmm
import swmmtb as st

#Subcatchments info

subcat=pd.read_csv('Res_files/subcat_modified')

subcat.drop(columns=['Unnamed: 0'],inplace=True)

for index, row in subcat.iterrows():
    subcat.loc[index, 'geometry']=shapely.wkt.loads(row['geometry'])

subcat=gpd.GeoDataFrame(subcat, geometry='geometry',crs='EPSG:27700')

#Relationship between subcatchment and node
subcatinode=pd.read_csv('GRA_files/subcatinode')
subcatinode.set_index('Node',inplace=True)

subcatinode.drop(list(subcatinode[subcatinode['Name'].isin(['SX96884607_t','SX96885506_t','SX96884622_t','SX96884509_t','SX96884535_t'])].index),inplace=True)

subtonode=subcatinode.to_dict()
subtonode=subtonode['Name']

#Node info
nodes=pd.read_csv('GRA_files/nodes')
nodes.drop(columns='Unnamed: 0',inplace=True)

#Subcatchmentinfo
import sections as sec
df=sec.import_inputfile('Res_files/input_files/topsham_ag.inp')
inputer=sec.deteriminesections(df)
for index, row in inputer['subcatchments'].iterrows():
    if 0<=row['Width']<1:
        df.loc[index,'Width']=1
for index, row in inputer['subcatchments'].iterrows():
    inputer['subcatchments'].loc[index,'Name']=row['Name'].strip()
    
##------------------------------------------------##    
## FUNCTIONS ##
##-----------##

##-----------------------------------------------##
## EXTRACTING ALL THE DATA NEEDED ##
##---------------------------------##
def get_flood(filename):

    '''
    This functions extracts relevant information from the report file


    Inputs
    ------
    filename: path to the report file - as a string

    Outputs
    -------
    Pandas dataframe with flooding results from the report
    '''

    #Upload the report
    thereport=pd.read_table(filename,sep='\n',header=None)

    #Where the info is TOTAL V FLOODING
    indr=thereport.index[thereport[0].str.contains("Node Flooding Summary",regex=False)]
    locr=thereport.index.get_loc(indr[0])

    #Where the info ends
    indr2=thereport.index[thereport[0].str.contains("Storage Volume Summary",regex=False)]
    locr2=thereport.index.get_loc(indr2[0])

    #load entire base model input file
    df= thereport.iloc[locr+9:locr2-1].copy()

    #drop uneeded rows
    df.drop(df[df[0].str.contains('-',regex=False)].index, axis=0, inplace=True)
    df.reset_index(drop=True, inplace=True)

    #format of the df is not good, need to change it
    for i in range(0,df.shape[0]):
        listi=df[0][i].split(' ')
        listi=[x for x in listi if x != '']
        listi='\t'.join(listi)
        df[0][i]=listi

    #split into several columns using spaces as delimiters
    df[['Name', 'HoursFlooded','MaxRateLPS', 'Days','TimeMax', 'TotalVFlood(10^6L)','MaxPonded']] =df[0].str.split('\t',0, expand=True)

    #drop uneeded columns
    df['Name']=df['Name'].str.strip()
    df.drop(columns=[0],inplace=True)

    #Calculate total runoff
    df[['HoursFlooded','MaxRateLPS', 'TotalVFlood(10^6L)','MaxPonded']]=df[['HoursFlooded','MaxRateLPS', 'TotalVFlood(10^6L)','MaxPonded']].astype(float)

    return df



def resilienceindex_nodes_sys(filename):
    '''
    INPUT
    -----
    filname: filename as a string

    OUTPUT
    ------
    pandas dataframe with res, inflow and flood for the subcatchments only accounting the outlet

    '''

    #Total Inflow at Nodes
    totalinflownode={}
    for i in nodes['Node']:
        totalinflownode[i]=st.extract('Res_files/'+filename + '.out',['node', i, 'Total_inflow'])

    for key, value in totalinflownode.items():
        value.rename(columns={'node_{}_Total_inflow'.format(key):'TotalInflow'},inplace=True)

    totalinflowvolume=pd.DataFrame()
    totalinflowvolume['Name']=nodes['Node']
    totalinflowvolume['TInflowVolume']=None

    for key, value in totalinflownode.items():
        totalinflowvolume.loc[totalinflowvolume['Name']==key,'TInflowVolume']=np.trapz(value['TotalInflow'])

    print('...Total Inflow subcatchments obtained')
    
    lateral_inflow=st.extract('Res_files/'+filename+'.out',['system', 'Total_lateral_inflow', 'Total_lateral_inflow'])
    lateral_inflow_tot=np.trapz(lateral_inflow['system__Total_lateral_inflow'])

    print('...Total Inflow system obtained')


    #Total Volume Flood at nodes
        #First, flood flow time series
    floodnode={}
    for i in nodes['Node']:
        floodnode[i]=st.extract('Res_files/'+filename+'.out',['node', i, 'Flow_lost_flooding'])

    for key, value in floodnode.items():
        value.rename(columns={'node_{}_Flow_lost_flooding'.format(key):'Flooding'},inplace=True)
        
    totalfloodvolume_sys=pd.DataFrame()
    totalfloodvolume_sys['Name']=nodes['Node']
    totalfloodvolume_sys['Flood']=None

    for key,value in floodnode.items():
        totalfloodvolume_sys.loc[totalfloodvolume_sys['Name']==key,'Flood']=np.trapz(value['Flooding'])

    print('... Flooding obtained system')


        #From flow to volume
    totalfloodvolume=pd.DataFrame()
    totalfloodvolume['Name']=nodes['Node']
    totalfloodvolume['Flood']=None

    for key,value in floodnode.items():
        totalfloodvolume.loc[totalfloodvolume['Name']==key,'Flood']=np.trapz(value['Flooding'])

    print('... Flooding obtained for subcatchments')


        #Hours flooded
        #Info from report
    nodeflood=get_flood('Res_files/'+ filename + '.rpt')
    hoursflooded=nodeflood['HoursFlooded'].mean()
    

    print('...Hours Flooded obtained for system & subcatchment')

        #Resilience Index
    resindexnode=pd.DataFrame()
    resindexnode=totalinflowvolume.copy()
    resindexnode=resindexnode.merge(totalfloodvolume,on='Name')
    resindexnode=resindexnode.merge(nodeflood[['HoursFlooded','Name']],on='Name',how='left')
    resindexnode=resindexnode.fillna(0)

    resindexnode['Res']=None
    resindexnode['Res']=1-(resindexnode['Flood']/resindexnode['TInflowVolume'])*((1/48)*resindexnode['HoursFlooded'])
    resindexnode=resindexnode.fillna(1)
    resindexnode=nodes.rename(columns={'Node':'Name'}).merge(resindexnode, on='Name', how='inner')
    
    print('Resilience Index at subcatchment calculated')
    
    resindexsyst=1-(totalfloodvolume_sys['Flood'].sum()/lateral_inflow_tot)*(hoursflooded/48)

    return [resindexnode, [resindexsyst,lateral_inflow_tot, totalfloodvolume_sys['Flood'].sum(),hoursflooded]]  




##-----------------------------------------------##
## CHANGE USE GI ##
##---------------–##
def LIDsubcat_area(filename,subcatchments):
    '''
    Modifies the input file dataframe and sets the usage of GI in the different subcatchments

    Inputs
    -----
    filename: swmm input file name as a string in the form of a dataframe
    subcatchment:


    Note: the use is a porcentage.

    Output
    ------
    Swmm input file modified
    '''
    theinputer=pd.read_csv('Res_files/input_files/'+filename+'.inp', header=None, skip_blank_lines=False)
    #--------------------------------------------------------------

    area=500

    #Gets the index from where the LID USAGE is
    indGI=theinputer.index[theinputer[0]=='[LID_USAGE]'] 
    locGI=theinputer.index.get_loc(indGI[0])

    df=inputer['subcatchments'].copy()

    gi_info=[]
    for index,row in df.iterrows():
        if row['Name'] in subcatchments:
            if row['Area']>=(area/10000):
                data_string=row['Name']+f'\tBIOCELL\t1\t{area}\t1\t0\t1\t0'
                gi_info.append(data_string)
            else:
                value=row['Area']*10000
                data_string=row['Name']+f'\tBIOCELL\t1\t{value}\t1\t0\t1\t0'
                gi_info.append(data_string)

    data_strings = pd.DataFrame(gi_info)

    #Insert new data
    dfA=theinputer[theinputer.index<= locGI+2]
    dfB=theinputer[theinputer.index>locGI+3]

    theinputermodified=dfA.append(data_strings, ignore_index=True)
    theinputermodified=theinputermodified.append(dfB, ignore_index=True)

    #Index information Subcatchments
    indsub=theinputermodified.index[theinputermodified[0]=='[SUBCATCHMENTS]']
    ind2sub=theinputermodified.index[theinputermodified[0]=='[SUBAREAS]']
    locsub=theinputermodified.index.get_loc(indsub[0])
    loc2sub=theinputermodified.index.get_loc(ind2sub[0])

    #set %impervious as floating number
    df[['%Imperv','Area']] = df[['%Imperv','Area']].astype(float)

    #Change imperviousness
    for index, row in df.iterrows():
        if row['Name'] in subcatchments:
            if row['Area']>=area*1000:
                 if row['%Imperv']>= (100*area(1/10000)*(1/row['Area'])):
                    df.loc[index,'%Imperv']= row['%Imperv']-100*area*(1/10000)*(1/row['Area'])
            else:
                value=row['Area']
                if row['%Imperv']>= (100*value*(1/row['Area'])):
                    df.loc[index,'%Imperv']= row['%Imperv']-100*value*(1/10000)*(1/row['Area'])

    #Data series new rainfall data
    data=df.round(2).astype(str)+'\t'
    data_strings = pd.DataFrame(data.values.sum(axis=1))

    #Insert new data
    dfA=theinputermodified[theinputermodified.index<= locsub+2]
    dfB=theinputermodified[theinputermodified.index>=loc2sub]

    theinputermod=dfA.append(data_strings, ignore_index=True)
    theinputermod=theinputermod.append(dfB, ignore_index=True)

    fin='Res_files/'+filename+str(hash(''.join(subcatchments)))+f'area_{area}'+'.inp'

    theinputermod.to_csv(fin,header=False, index=False, quoting=3, sep='\n', na_rep=' ')

    print('... the modified input file was saved')
    
    
 ##-----------------------------------------------------------##   
 ## SIMULATION ##   
##-------------------##

def simul_nodes(i,filename):
    '''
    Function to be iterated using parallelisation
    Filename needs to be changed every time that the storm is changed
    
    Input
    -----
    list of subcatchments where GI will be implemented

    Output
    ------
    resilience index pandas dataframe
    '''
    from pyswmm import Simulation
    
    area = 500
    
    LIDsubcat_area(filename,i)

    fin=filename+str(hash(''.join(i)))+f'area_{area}'

    sim=Simulation('Res_files/'+fin+'.inp')
    sim.execute()

    res=resilienceindex_nodes_sys(fin)
    print('Resilience Index Calculated')

    os.remove('Res_files/'+fin+'.inp')
    os.remove('Res_files/'+fin+'.out')
    os.remove('Res_files/'+fin+'.rpt')

    print('Files removed!')

    return res


def simul_nodes_unpack(args):
    return simul_nodes(*args)


def set_simul_node(j,rs, num_processors,filename):
    '''
    Input
    ------
    j: simulation number
    rs: random sequence -- each element of the list is a list.
    num_processors: the number of processors to be used - MAX 12
    
    Output
    ------
    output: results in the form of a list, where the elements are pandas dataframes
    '''
    
    from multiprocessing import Pool
    import time
    import itertools
    from tqdm import tqdm
    

    start=time.time()    
    p=Pool(num_processors)
    output=p.map(simul_nodes_unpack,zip(rs,itertools.repeat(filename)))
    p.close()

    elapsed=start-time.time()
    print(f'RES Simulation {j} finished at time {elapsed}.')

    return output

##---------------------------------------------##
## SAVE RESULTS ##
##--------------##

def save_results_2(j,rs,storm,output):
    
    res_sys=pd.DataFrame()
    res_sys=pd.DataFrame()
    res_sys['simulation']=range(0,len(output))
    res_sys['Res']=None
    res_sys['Inflow']=None
    res_sys['Flood']=None
    res_sys['HoursFlooded']=None

    
    for i in range(0, len(output)):
        output[i][0].to_csv(f'Res_files/{storm}/simulation_{j}_{i}')
        
        res_sys.loc[res_sys['simulation']==i,'Res']=output[i][1][0]
        res_sys.loc[res_sys['simulation']==i,'Inflow']=output[i][1][1]
        res_sys.loc[res_sys['simulation']==i,'flood']=output[i][1][2]
        res_sys.loc[res_sys['simulation']==i,'HoursFlooded']=output[i][1][3]
                            
    res_sys.to_csv(f'Res_files/{storm}/simulation_{j}_system')    
                            
    rswrite=''
                            
    for i in rs:
        rswrite=rswrite+'\n'+','.join(i)
    f=open(f'Res_files/{storm}/rs{j}','w')
    f.write(rswrite)
    f.close()
    print(f'Results saved for GRA {j}')
                    

