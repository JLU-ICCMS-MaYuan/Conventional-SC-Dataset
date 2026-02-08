import numpy as np
import glob
from pymatgen.core import Structure
import pandas as pd
import re
import matplotlib.pyplot as plt
pd.set_option('display.max_columns',None)
pd.set_option('display.max_rows',None)
pd.set_option('display.width',None)

data=pd.read_excel('data.xlsx')
npz_data = np.load('bonds_data.npz',allow_pickle=True)
temp_np = list(npz_data['data'])
total_data=[]
for i in range(len(data)):
    temp_com = data.loc[i,'compound']
    for j in temp_np:
        temp_com2 = j['compound']
        if temp_com2 == temp_com:
            temp_data = {}
            temp_data['compound'] = data.loc[i, 'compound']
            temp_data['dos_m1'] = data.loc[i, 'dos_m1']
            temp_data['dos_m2'] = data.loc[i, 'dos_m2']
            temp_data['dos_m3'] = data.loc[i, 'dos_m3']
            temp_data['dos_m4'] = data.loc[i, 'dos_m4']
            temp_data['dos_H'] = data.loc[i, 'dos_H']
            temp_data['bonds']=j['bonds']
            temp_data['super_cell']=j['super_cell']
            temp_data['h_atoms']=j['h_atoms']
            total_data.append(temp_data)
            break

np.savez('traindata.npz',data=total_data)
