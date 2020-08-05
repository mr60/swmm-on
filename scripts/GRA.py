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

subcat=pd.read_csv('GRA_files/subcatgeo')

subcat.drop(columns=['Unnamed: 0'],inplace=True)

for index, row in subcat.iterrows():
    subcat.loc[index, 'geometry']=shapely.wkt.loads(row['geometry'])

subcat=gpd.GeoDataFrame(subcat, geometry='geometry',crs='EPSG:27700')

#Relationship between subcatchment and node
subcatinode=pd.read_csv('GRA_files/subcatinode')
subcatinode.set_index('Node',inplace=True)
subtonode=subcatinode.to_dict()
subtonode=subtonode['Name']

#Relationship between subcatchemnt and all nodes within
nodes_subcat_clean=pd.read_csv('GRA_files/nodes_subcat_clean')
subcat_to_node_dict=nodes_subcat_clean.set_index('name_subcat').to_dict()['Name']
node_to_subcat_dict=nodes_subcat_clean.set_index('Name').to_dict()['name_subcat']

#Node info
nodes=pd.read_csv('GRA_files/nodes')
nodes.drop(columns='Unnamed: 0',inplace=True)

#Subcatchmentinfo
import sections as sec
df=sec.import_inputfile('Topshamrain_modi13-4.inp')
inputer=sec.deteriminesections(df)
for index, row in inputer['subcatchments'].iterrows():
    if 0<=row['Width']<1:
        df.loc[index,'Width']=1
for index, row in inputer['subcatchments'].iterrows():
    inputer['subcatchments'].loc[index,'Name']=row['Name'].strip()

#FUNCTIONS
#---------

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


def resilienceindex(filename):
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
        totalinflownode[i]=st.extract('GRA_files/'+filename + '.out',['node', i, 'Total_inflow'])

    for key, value in totalinflownode.items():
        value.rename(columns={'node_{}_Total_inflow'.format(key):'TotalInflow'},inplace=True)

    #Total Inflows at Subcatchments (relates outlet node data with subcatchment)
    totalinflowsubcat={}

    for key, value in totalinflownode.items():
        if key in list(subtonode.keys()):
            totalinflowsubcat[subtonode[key]]=value

    totalinflowvolume=pd.DataFrame()
    totalinflowvolume['Name']=subcat['Name']
    totalinflowvolume['TInflowVolume']=None

    for key, value in totalinflowsubcat.items():
        totalinflowvolume.loc[totalinflowvolume['Name']==key,'TInflowVolume']=np.trapz(value['TotalInflow'])

    print('...Total Inflow obtained')


    #Total Volume Flood at nodes
        #First, flood flow time series
    floodnode={}
    for i in nodes['Node']:
        floodnode[i]=st.extract('GRA_files/'+filename+'.out',['node', i, 'Flow_lost_flooding'])

    for key, value in floodnode.items():
        value.rename(columns={'node_{}_Flow_lost_flooding'.format(key):'Flooding'},inplace=True)

        #Translation to Subcatchment
    floodsubcat={}

    for key, value in floodnode.items():
        if key in list(subtonode.keys()):
            floodsubcat[subtonode[key]]=value

        #From flow to volume
    totalfloodvolume=pd.DataFrame()
    totalfloodvolume['Name']=subcat['Name']
    totalfloodvolume['Flood']=None

    for key,value in floodsubcat.items():
        totalfloodvolume.loc[totalfloodvolume['Name']==key,'Flood']=np.trapz(value['Flooding'])

    print('... Flooding obtained')


        #Hours flooded
        #Info from report
    nodeflood=get_flood('GRA_files/'+ filename + '.rpt')
    nodeflood['sub']=None

        #Relates node to subcatchment
    for i , row in nodeflood.iterrows():
        if row['Name'] in subtonode.keys():
            nodeflood.loc[i,'sub']=subtonode[row['Name']]
        else:
            nodeflood.loc[i,'sub']='NO'

    nodeflood=nodeflood[nodeflood['sub']!='NO'].copy()
    nodeflood.drop(columns='Name',inplace=True)
    nodeflood.rename(columns={'sub':'Name'},inplace=True)

    print('...Hours Flooded obtained')

        #Resilience Index
    resindexsubcat=pd.DataFrame()
    resindexsubcat=totalinflowvolume.copy()
    resindexsubcat=resindexsubcat.merge(totalfloodvolume,on='Name')
    resindexsubcat=resindexsubcat.merge(nodeflood[['HoursFlooded','Name']],on='Name',how='left')
    resindexsubcat=resindexsubcat.fillna(0)

    resindexsubcat['Res']=None
    resindexsubcat['Res']=1-(resindexsubcat['Flood']/resindexsubcat['TInflowVolume'])*((1/48)*resindexsubcat['HoursFlooded'])
    resindexsubcat=resindexsubcat.fillna(1)
    resindexsubcat=subcat.merge(resindexsubcat, on='Name', how='inner')

    return resindexsubcat

#CHANGE USE OF GI
#=======================
def LIDsubcat(filename,subcatchments):
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
    theinputer=pd.read_csv('GRA_files/input_files/apond_0/'+filename+'.inp', header=None, skip_blank_lines=False)
    
    #--------------------------------------------------------------
    #Gets the index from where the LID USAGE is
    indGI=theinputer.index[theinputer[0]=='[LID_USAGE]'] 
    locGI=theinputer.index.get_loc(indGI[0])
    
    gi_info=[]
    for i in subcatchments:
        data_string=i+'\tBIOCELL\t1\t100\t1\t0\t1\t0'
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

    df=inputer['subcatchments'].copy()

    #set %impervious as floating number
    df[['%Imperv','Area']] = df[['%Imperv','Area']].astype(float)


    #Change imperviousness
    for index, row in df.iterrows():
        if row['Name'] in subcatchments:
             if row['%Imperv']>= (100*0.01*(1/row['Area'])):
                df.loc[index,'%Imperv']= row['%Imperv']-100*0.01*(1/row['Area'])

    #Data series new rainfall data
    data=df.round(2).astype(str)+'\t'
    data_strings = pd.DataFrame(data.values.sum(axis=1))

    #Insert new data
    dfA=theinputermodified[theinputermodified.index<= locsub+2]
    dfB=theinputermodified[theinputermodified.index>=loc2sub]

    theinputermod=dfA.append(data_strings, ignore_index=True)
    theinputermod=theinputermod.append(dfB, ignore_index=True)
    
    fin='GRA_files/'+filename+str(hash(''.join(subcatchments)))+'.inp'

    theinputermod.to_csv(fin,header=False, index=False, quoting=3, sep='\n', na_rep=' ')

    print('... the modified input file was saved')
    
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
    theinputer=pd.read_csv('GRA_files/input_files/apond_0/'+filename+'.inp', header=None, skip_blank_lines=False)
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

    fin='GRA_files/'+filename+str(hash(''.join(subcatchments)))+f'area_{area}'+'.inp'

    theinputermod.to_csv(fin,header=False, index=False, quoting=3, sep='\n', na_rep=' ')

    print('... the modified input file was saved')
    
def resindsys(filename):
    '''
    INPUT
    -----
    filname: filename as a string

    OUTPUT
    ------
    value of resilience for the system

    '''
    
    lateral_inflow=st.extract('GRA_files/'+filename+'.out',['system', 'Total_lateral_inflow', 'Total_lateral_inflow'])
    lateral_inflow_tot=np.trapz(lateral_inflow['system__Total_lateral_inflow'])

    print('...Total Inflow obtained')


    #Total Volume Flood at nodes
        #First, flood flow time series
    floodnode={}
    for i in nodes['Node']:
        floodnode[i]=st.extract('GRA_files/'+filename+'.out',['node', i, 'Flow_lost_flooding'])

    for key, value in floodnode.items():
        value.rename(columns={'node_{}_Flow_lost_flooding'.format(key):'Flooding'},inplace=True)

    
    totalfloodvolume=pd.DataFrame()
    totalfloodvolume['Name']=nodes['Node']
    totalfloodvolume['Flood']=None

    for key,value in floodnode.items():
        totalfloodvolume.loc[totalfloodvolume['Name']==key,'Flood']=np.trapz(value['Flooding'])

    print('... Flooding obtained')


        #Hours flooded
        #Info from report
    nodeflood=get_flood('GRA_files/'+ filename + '.rpt')
    hoursflooded=nodeflood['HoursFlooded'].mean()
   
    print('...Hours Flooded obtained')

        #Resilience Index
    resindexsyst=1-(totalfloodvolume['Flood'].sum()/lateral_inflow_tot)*(hoursflooded/48)
    return [resindexsyst, lateral_inflow_tot, totalfloodvolume['Flood'].sum(), hoursflooded]



def resilienceindex_allnodes(filename):
    '''
    INPUT
    -----
    filname: filename as a string

    OUTPUT
    ------
    pandas dataframe with flood, inflow and res for subcatchments, accounting all the nodes within the subcatchment
    '''

    #Total Inflow at Nodes
    totalinflownode={}
    for i in nodes['Node']:
        totalinflownode[i]=st.extract('GRA_files/'+filename + '.out',['node', i, 'Total_inflow'])

    for key, value in totalinflownode.items():
        value.rename(columns={'node_{}_Total_inflow'.format(key):'TotalInflow'},inplace=True)

    totalinflowvolume=pd.DataFrame()
    totalinflowvolume['Name']=nodes['Node']
    totalinflowvolume['TInflowVolume']=None

    for key, value in totalinflownode.items():
        totalinflowvolume.loc[totalinflowvolume['Name']==key,'TInflowVolume']=np.trapz(value['TotalInflow'])
    
    inflow=nodes_subcat_clean.merge(totalinflowvolume, on='Name',how='inner')
    totalinflowvolume_subcat=inflow.groupby('name_subcat').sum()
    totalinflowvolume_subcat.drop(columns='Name',inplace=True)
    totalinflowvolume_subcat.reset_index(inplace=True)
    totalinflowvolume_subcat.rename(columns={'name_subcat':'Name'},inplace=True)
  
    print('...Total Inflow obtained')


    #Total Volume Flood at nodes
        #First, flood flow time series
    floodnode={}
    for i in nodes['Node']:
        floodnode[i]=st.extract('GRA_files/'+filename+'.out',['node', i, 'Flow_lost_flooding'])

    for key, value in floodnode.items():
        value.rename(columns={'node_{}_Flow_lost_flooding'.format(key):'Flooding'},inplace=True)

        #From flow to volume
    totalfloodvolume=pd.DataFrame()
    totalfloodvolume['Name']=nodes['Node']
    totalfloodvolume['Flood']=None

    for key,value in floodnode.items():
        totalfloodvolume.loc[totalfloodvolume['Name']==key,'Flood']=np.trapz(value['Flooding'])
    
    flood=nodes_subcat_clean.merge(totalfloodvolume,on='Name',how='inner')
    totalfloodvolume_subcat=flood.groupby('name_subcat').sum()
    totalfloodvolume_subcat.drop(columns='Name',inplace=True)
    totalfloodvolume_subcat.reset_index(inplace=True)
    totalfloodvolume_subcat.rename(columns={'name_subcat':'Name'},inplace=True)

    print('... Flooding obtained')


        #Hours flooded
        #Info from report
    nodeflood=get_flood('GRA_files/'+ filename + '.rpt')
    
    subcatflood=pd.DataFrame()
    subcatflood['Name']=subcat['Name']
    subcatflood['HoursFlooded']=0


    for index,row in nodeflood.iterrows():
        if row['Name'] in node_to_subcat_dict.keys():
            sub=node_to_subcat_dict[row['Name']]

            if row['HoursFlooded'] > subcatflood[subcatflood['Name']==sub]['HoursFlooded'].values[0]:
                subcatflood.loc[subcatflood['Name']==sub,'HoursFlooded']=row['HoursFlooded']

    print('...Hours Flooded obtained')

        #Resilience Index
    resindexsubcat=pd.DataFrame()
    resindexsubcat=totalinflowvolume_subcat.copy()
    resindexsubcat=resindexsubcat.merge(totalfloodvolume_subcat,on='Name')
    resindexsubcat=resindexsubcat.merge(subcatflood,on='Name',how='left')
    resindexsubcat=resindexsubcat.fillna(0)

    resindexsubcat['Res']=None
    resindexsubcat['Res']=1-(resindexsubcat['Flood']/resindexsubcat['TInflowVolume'])*((1/48)*resindexsubcat['HoursFlooded'])
    resindexsubcat=resindexsubcat.fillna(1)
    resindexsubcat=subcat.merge(resindexsubcat, on='Name', how='inner')

    return resindexsubcat


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
        totalinflownode[i]=st.extract('GRA_files/'+filename + '.out',['node', i, 'Total_inflow'])

    for key, value in totalinflownode.items():
        value.rename(columns={'node_{}_Total_inflow'.format(key):'TotalInflow'},inplace=True)

    totalinflowvolume=pd.DataFrame()
    totalinflowvolume['Name']=nodes['Node']
    totalinflowvolume['TInflowVolume']=None

    for key, value in totalinflownode.items():
        totalinflowvolume.loc[totalinflowvolume['Name']==key,'TInflowVolume']=np.trapz(value['TotalInflow'])

    print('...Total Inflow subcatchments obtained')
    
    lateral_inflow=st.extract('GRA_files/'+filename+'.out',['system', 'Total_lateral_inflow', 'Total_lateral_inflow'])
    lateral_inflow_tot=np.trapz(lateral_inflow['system__Total_lateral_inflow'])

    print('...Total Inflow system obtained')


    #Total Volume Flood at nodes
        #First, flood flow time series
    floodnode={}
    for i in nodes['Node']:
        floodnode[i]=st.extract('GRA_files/'+filename+'.out',['node', i, 'Flow_lost_flooding'])

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
    nodeflood=get_flood('GRA_files/'+ filename + '.rpt')
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


def resilienceindex_subsys(filename):
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
        totalinflownode[i]=st.extract('GRA_files/'+filename + '.out',['node', i, 'Total_inflow'])

    for key, value in totalinflownode.items():
        value.rename(columns={'node_{}_Total_inflow'.format(key):'TotalInflow'},inplace=True)

    #Total Inflows at Subcatchments (relates outlet node data with subcatchment)
    totalinflowsubcat={}

    for key, value in totalinflownode.items():
        if key in list(subtonode.keys()):
            totalinflowsubcat[subtonode[key]]=value

    totalinflowvolume=pd.DataFrame()
    totalinflowvolume['Name']=subcat['Name']
    totalinflowvolume['TInflowVolume']=None

    for key, value in totalinflowsubcat.items():
        totalinflowvolume.loc[totalinflowvolume['Name']==key,'TInflowVolume']=np.trapz(value['TotalInflow'])

    print('...Total Inflow subcatchments obtained')
    
    lateral_inflow=st.extract('GRA_files/'+filename+'.out',['system', 'Total_lateral_inflow', 'Total_lateral_inflow'])
    lateral_inflow_tot=np.trapz(lateral_inflow['system__Total_lateral_inflow'])

    print('...Total Inflow system obtained')


    #Total Volume Flood at nodes
        #First, flood flow time series
    floodnode={}
    for i in nodes['Node']:
        floodnode[i]=st.extract('GRA_files/'+filename+'.out',['node', i, 'Flow_lost_flooding'])

    for key, value in floodnode.items():
        value.rename(columns={'node_{}_Flow_lost_flooding'.format(key):'Flooding'},inplace=True)
        
    totalfloodvolume_sys=pd.DataFrame()
    totalfloodvolume_sys['Name']=nodes['Node']
    totalfloodvolume_sys['Flood']=None

    for key,value in floodnode.items():
        totalfloodvolume_sys.loc[totalfloodvolume_sys['Name']==key,'Flood']=np.trapz(value['Flooding'])

    print('... Flooding obtained system')

        #Translation to Subcatchment
    floodsubcat={}

    for key, value in floodnode.items():
        if key in list(subtonode.keys()):
            floodsubcat[subtonode[key]]=value

        #From flow to volume
    totalfloodvolume=pd.DataFrame()
    totalfloodvolume['Name']=subcat['Name']
    totalfloodvolume['Flood']=None

    for key,value in floodsubcat.items():
        totalfloodvolume.loc[totalfloodvolume['Name']==key,'Flood']=np.trapz(value['Flooding'])

    print('... Flooding obtained for subcatchments')


        #Hours flooded
        #Info from report
    nodeflood=get_flood('GRA_files/'+ filename + '.rpt')
    hoursflooded=nodeflood['HoursFlooded'].mean()
    
    nodeflood['sub']=None

        #Relates node to subcatchment
    for i , row in nodeflood.iterrows():
        if row['Name'] in subtonode.keys():
            nodeflood.loc[i,'sub']=subtonode[row['Name']]
        else:
            nodeflood.loc[i,'sub']='NO'

    nodeflood=nodeflood[nodeflood['sub']!='NO'].copy()
    nodeflood.drop(columns='Name',inplace=True)
    nodeflood.rename(columns={'sub':'Name'},inplace=True)
    

    print('...Hours Flooded obtained for system & subcatchment')

        #Resilience Index
    resindexsubcat=pd.DataFrame()
    resindexsubcat=totalinflowvolume.copy()
    resindexsubcat=resindexsubcat.merge(totalfloodvolume,on='Name')
    resindexsubcat=resindexsubcat.merge(nodeflood[['HoursFlooded','Name']],on='Name',how='left')
    resindexsubcat=resindexsubcat.fillna(0)

    resindexsubcat['Res']=None
    resindexsubcat['Res']=1-(resindexsubcat['Flood']/resindexsubcat['TInflowVolume'])*((1/48)*resindexsubcat['HoursFlooded'])
    resindexsubcat=resindexsubcat.fillna(1)
    resindexsubcat=subcat.merge(resindexsubcat, on='Name', how='inner')
    
    print('Resilience Index at subcatchment calculated')
    
    resindexsyst=1-(totalfloodvolume_sys['Flood'].sum()/lateral_inflow_tot)*(hoursflooded/48)

    return [resindexsubcat, [resindexsyst,lateral_inflow_tot, totalfloodvolume_sys['Flood'].sum(),hoursflooded]]  

def simul_gi(i,filename):
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
    
    LIDsubcat(filename,i)

    fin=filename+str(hash(''.join(i)))

    sim=Simulation('GRA_files/'+fin+'.inp')
    sim.execute()

    res=resilienceindex_subsys(fin)
    print('Resilience Index Calculated')

    os.remove('GRA_files/'+fin+'.inp')
    os.remove('GRA_files/'+fin+'.out')
    os.remove('GRA_files/'+fin+'.rpt')

    print('Files removed!')

    return res

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

    sim=Simulation('GRA_files/'+fin+'.inp')
    sim.execute()

    res=resilienceindex_nodes_sys(fin)
    print('Resilience Index Calculated')

    os.remove('GRA_files/'+fin+'.inp')
    os.remove('GRA_files/'+fin+'.out')
    os.remove('GRA_files/'+fin+'.rpt')

    print('Files removed!')

    return res

def simul_gi_area(i,filename):
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

    sim=Simulation('GRA_files/'+fin+'.inp')
    sim.execute()

    res=resilienceindex_subsys(fin)
    print('Resilience Index Calculated')

    os.remove('GRA_files/'+fin+'.inp')
    os.remove('GRA_files/'+fin+'.out')
    os.remove('GRA_files/'+fin+'.rpt')

    print('Files removed!')

    return res

def set_simul_unpack(args):
    return simul_gi(*args)

def set_simul_area_unpack(args):
    return simul_gi_area(*args)

def simul_nodes_unpack(args):
    return simul_nodes(*args)



def set_rs():
    '''
    Input
    ----
    NONE
    Output
    -----
    reutrns a list of the subcatchments picked randomly
    '''
    from random import sample
    rs=[]
    for i in range(1,226):
        rs.append(sample(list(subcat['Name']),i))
    return rs

def combinations(i):
    '''
    INPUT
    -----
    i: the number of subcatchments that will have GI per scenario
    
    OUTPUT
    ------
    sample: list with all the combinations of subcatchments with i 
    '''
    import itertools
    sample=[list(subset) for subset in itertools.combinations(subcat['Name'],i)]

    return sample


def set_simul(j,rs, num_processors,filename):
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
    output=p.map(set_simul_unpack,zip(rs,itertools.repeat(filename)))
    p.close()

    elapsed=start-time.time()
    print(f'GRA Simulation {j} finished at time {elapsed}.')

    return output

def set_simul_area(j,rs, num_processors,filename):
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
    output=p.map(set_simul_area_unpack,zip(rs,itertools.repeat(filename)))
    p.close()

    elapsed=start-time.time()
    print(f'GRA Simulation {j} finished at time {elapsed}.')

    return output

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
    print(f'GRA Simulation {j} finished at time {elapsed}.')

    return output

def save_results(j,rs,storm,output):
    ''' 
    Input
    ------
    j: simulation number
    rs: random sequence
    output: the result of the simulation j
    
    Output
    -------
    results saved in the GRA folder
    '''
    
    sa=pd.DataFrame()
    flood=pd.DataFrame()
    floodu=pd.DataFrame()
    for i in range(0,225):
        sa[i]=output[i]['Res']
        flood[i]=output[i]['Flood']
        floodu[i]=output[i]['HoursFlooded']
        
    sa.to_csv(f'GRA_files/{storm}/gra/gra{j}')
    flood.to_csv(f'GRA_files/{storm}/gra/flood{j}')
    floodu.to_csv(f'GRA_files/{storm}/gra/floodu{j}')
    rswrite=''
    for i in rs:
        rswrite=rswrite+'\n'+','.join(i)
    f=open(f'GRA_files/{storm}/rs/rs{j}','w')
    f.write(rswrite)
    f.close()
    print(f'Results saved for GRA {j}')
    
def save_results_2(j,rs,storm,output):
    
    res_sys=pd.DataFrame()
    res_sys=pd.DataFrame()
    res_sys['simulation']=range(0,len(output))
    res_sys['Res']=None
    res_sys['Inflow']=None
    res_sys['Flood']=None
    res_sys['HoursFlooded']=None

    
    for i in range(0, len(output)):
        output[i][0].to_csv(f'GRA_files/{storm}/simulation_{j}_{i}')
        
        res_sys.loc[res_sys['simulation']==i,'Res']=output[i][1][0]
        res_sys.loc[res_sys['simulation']==i,'Inflow']=output[i][1][1]
        res_sys.loc[res_sys['simulation']==i,'flood']=output[i][1][2]
        res_sys.loc[res_sys['simulation']==i,'HoursFlooded']=output[i][1][3]
                            
    res_sys.to_csv(f'GRA_files/{storm}/simulation_{j}_system')    
                            
    rswrite=''
                            
    for i in rs:
        rswrite=rswrite+'\n'+','.join(i)
    f=open(f'GRA_files/{storm}/rs{j}','w')
    f.write(rswrite)
    f.close()
    print(f'Results saved for GRA {j}')
                    
    
def save_results_geo(j,rs,storm, output):
    '''
    Input
    -------
    j: grid size
    rs: sequences of the intersected subcatchments
    output: results from the simulation with grid size j
    
    Output
    ------
    Results saved on the folder GRA
    '''
    sa=pd.DataFrame()
    flood=pd.DataFrame()
    floodu=pd.DataFrame()
    for i in range(0,len(rs)):
        sa[i]=output[i]['Res']
        flood[i]=output[i]['Flood']
        floodu[i]=output[i]['HoursFlooded']
        
    sa.to_csv(f'GRA_files/{storm}/geo/gra{j}')
    flood.to_csv(f'GRA_files/{storm}/geo/flood{j}')
    floodu.to_csv(f'GRA_files/{storm}/geo/floodu{j}')
    rswrite=''
    for i in rs:
        rswrite=rswrite+'\n'+','.join(i)
    f=open(f'GRA_files/{storm}/rs_geo/rs{j}','w')
    f.write(rswrite)
    f.close()
    print(f'Results saved for GRA {j}')
