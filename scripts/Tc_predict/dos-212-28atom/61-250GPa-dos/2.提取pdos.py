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
data=pd.DataFrame(columns=['compound','dos_m1','dos_m2','dos_m3','dos_m4','dos_H'])
with open('log','r') as f:
    lines=[i.strip() for i in f.readlines()]
    for line in lines:
        dos_files = glob.glob(f'{line}/PDOS_*.dat')
        total_dos_value = [line]
        for idx,file in enumerate(dos_files):
            if 'PDOS_H.dat' in file:
                continue
            else:
                dos_data = np.loadtxt(file)
                fermi_value = dos_data[np.argmin(np.abs(dos_data[:,0])),-1]
                total_dos_value.append(fermi_value)
        H_pdos = np.loadtxt(rf'{line}/PDOS_H.dat')
        H_fermi_value = H_pdos[np.argmin(np.abs(H_pdos[:,0])),-1]
        total_dos_value.append(H_fermi_value)
        data.loc[len(data)] = total_dos_value
print(data.head())
data.to_excel('data.xlsx',index=False)