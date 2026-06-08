import numpy as np
import glob
from pymatgen.core import Structure
import pandas as pd
import re
import matplotlib.pyplot as plt
pd.set_option('display.max_columns',None)
pd.set_option('display.max_rows',None)
pd.set_option('display.width',None)

"获取边长ver2, 保存所有边长, 在字典里"
data=[]



with open('log','r') as f:
    lines=[i.strip() for i in f.readlines()]
    for line in lines:
        # dos_files = glob.glob(rf'{line}/PDOS_*.dat')
        # for dos_file in dos_files:
        # dos_Ca = rf'{line}\PDOS_Ca.dat'
        # dos_H = rf'{line}\PDOS_H.dat'
        # dos_Mg = rf'{line}\PDOS_Mg.dat'
        stru = Structure.from_file(rf'{line}\CONTCAR')
        ff={}
        bonds=[]
        compound=line
        f1=stru.composition.reduced_composition.alphabetical_formula
        h_number=re.search(r'H(\d+)', f1).group(1)
        h_number = int(h_number)
        species = list(stru.symbol_set)
        atoms_num = stru.num_sites
        stru.remove_species([i for i in species if i != 'H'])
        dist_mat = stru.distance_matrix

        super_cell=dist_mat.shape[0]/h_number
        print(compound, f1, dist_mat.shape[0],h_number)
        if not super_cell.is_integer():
            print('super_cell',super_cell)
            break
        for i in range(dist_mat.shape[0]):
            for j in range(dist_mat.shape[1]):
                if j >= i:
                    break
                temp_bond=dist_mat[i][j]
                if temp_bond <= 1.4:
                    bonds.append(temp_bond)
        ff['h_atoms']=dist_mat.shape[0]
        ff['compound']=compound
        ff['bonds']=bonds
        ff['super_cell']=super_cell
        data.append(ff)
np.savez('bonds_data.npz',data=data)