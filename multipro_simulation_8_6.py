import GRA
from tqdm import tqdm

# arr=['M2_10','M2_30','M2_60','M10_10','M10_30','M10_60','M50_10','M50_30','M50_60','M100_10','M100_30','M100_60']
arr=['M2_10']

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
    
    area=200
    
    GRA.LIDsubcat_area(filename,i, area)

    fin=filename+str(hash(''.join(i)))

    sim=Simulation('GRA_files/'+fin+'.inp')
    sim.execute()

    res=GRA.resilienceindex_subsys(fin)
    print('Resilience Index Calculated')

    os.remove('GRA_files/'+fin+'.inp')
    os.remove('GRA_files/'+fin+'.out')
    os.remove('GRA_files/'+fin+'.rpt')

    print('Files removed!')

    return res

def set_simul_unpack(args):
    return simul_gi(*args)

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
    output=p.map(set_simul_unpack,tqdm(zip(rs,itertools.repeat(filename))))
    p.close()

    elapsed=start-time.time()
    print(f'GRA Simulation {j} finished at time {elapsed}.')

    return output

for i in tqdm(arr):
    sample=GRA.set_rs()
    file=f'Topsham{i}'
    output=set_simul(1,sample,6,file)
    GRA.save_results_2('area_200',sample,i,output)
        
