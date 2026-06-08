import numpy as np
import glob
from pymatgen.core import Structure
import pandas as pd
import re
import matplotlib.pyplot as plt
pd.set_option('display.max_columns',None)
pd.set_option('display.max_rows',None)
pd.set_option('display.width',None)


def count_elements(lst):
    count_dict = {}
    for element in lst:
        element = np.floor(element * 1000) / 1000  # 截取小数后三位, 不四舍五入
        if element in count_dict:
            count_dict[element] += 1
        else:
            count_dict[element] = 1

    return count_dict

def refine_dict(dic,super_cell):
    for k in dic.keys():
        dic[k]=dic[k]/super_cell
    dic=dict(sorted(dic.items()))
    return dic


data=np.load('traindata.npz',allow_pickle=True)
data=list(data['data'])

compound = [i['compound'] for i in data]
atoms = [i['h_atoms'] for i in data]
super_cell = [i['super_cell'] for i in data]
dos_H = [i['dos_H'] for i in data]
dos_m1 = [i['dos_m1'] for i in data]
dos_m2 = [i['dos_m2'] for i in data]
dos_m3 = [i['dos_m3'] for i in data]
dos_m4 = [i['dos_m4'] for i in data]
bonds = [i['bonds'] for i in data]
bonds_mean = [np.mean(i['bonds']) for i in data]
bonds_var = [np.var(i['bonds']) for i in data]
bonds = [count_elements(i) for i in bonds]
for i in range(len(bonds)):
    bonds[i]=refine_dict(bonds[i],atoms[i])
dos_H_atom = [dos_H[i]/atoms[i] for i in range(len(dos_H))]

d=pd.DataFrame()
d['compound']=compound
d['super_cell']=super_cell
d['H_atoms']=atoms
d['dos_H']=dos_H
d['dos_m1']=dos_m1
d['dos_m2']=dos_m2
d['dos_m3']=dos_m3
d['dos_m4']=dos_m4
# d['dos_m2']=d['dos_m2'].fillna(0)
d['dos_H_atom']=d['dos_H']/d['H_atoms']  # > 0.0149
d['dos_H_fu']=d['dos_H']/d['super_cell']
d['bonds_num_atom']=[sum(i.values()) for i in bonds]
# d['bonds_num_atom']=d['bonds_num_fu']*d['super_cell']/d['H_atoms']
d['dos_H_atom_bond']=d['dos_H_atom']/d['bonds_num_atom']
d['dos_H_ratio']=d['dos_H']/(d['dos_H']+d['dos_m1']+d['dos_m2']+d['dos_m3']+d['dos_m4'])  # > 0.33
d['bonds_mean']=bonds_mean
d['bonds_var']=bonds_var
d['bonds']=bonds


def get_f2(bl,br,d):
    # bond_right=1.28
    a=0
    b=1
    couples=[]
    for i in range(len(bonds)):
        couple=0
        bd=bonds[i]
        # dos=dos_H_atom[i]
        dos=d['dos_H_atom_bond'][i]
        for k in bd.keys():
            bd_num=bd[k]
            if k < bl or k > br:
                couple+=k*bd_num*dos*a
            elif k >=bl and k <= br:
                couple+=k*bd_num*dos*b
        couples.append(couple)
    d['couple']=couples

    d['f1']=(d['dos_H_atom_bond']+(d['couple'])**2)/(d['dos_H_ratio']+(1/d['dos_H_ratio']))
    d['f1']=((d['dos_H_atom_bond']*d['dos_H_ratio'])/(1+d['dos_H_ratio']**2)) + ((d['dos_H_ratio']*d['couple'])/(1+d['dos_H_ratio']**2))
    d['f1']=((d['dos_H_atom_bond']*d['dos_H_ratio'])/(1+d['dos_H_ratio']**2))  # 文章用这个, 只和dosH有关
    d['f2']=((d['dos_H_ratio']*d['couple'])/(1+d['dos_H_ratio']**2))  # 加了键长的耦合部分
    # d['f3']=d['f1']+d['f2']  # 这个更好看
    # d['f3']=11052.48523705*d['f3']+23.68293387


    # d=pd.read_excel('temp.xlsx')

    # plt.scatter(d['couple'],d['Tc'])
    # plt.show()

    # slop=np.polyfit(d['f2'],d['Tc'],deg=1)  # [1.0-1.28] [16418.51238727    25.15965924]
    # print(slop)  # [1.0-1.27] [16156.06704906    29.49445232]
    slop1, slop2 = 16370.6, 24.7
    d['f2_Tc']=slop1*d['f2']+slop2
    d.to_excel('predict_result.xlsx',index=False)

bl=1.0
br=1.28
get_f2(0.98,1.28,d)
