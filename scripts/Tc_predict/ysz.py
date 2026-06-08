import pandas as pd

data=pd.read_excel('total.xlsx')
data['flag'] = data['compound'].str.replace('H24','')
data['flag'] = data['flag'].str.lower() + '-' +data['pressure'].astype(str)
print(data.head())

a=pd.read_excel('dos-36-252atom/predict_result.xlsx')
a=a[['compound','f2_Tc']]
a['compound'] = a['compound'].str.replace('^\d+-','',regex=True)
a['compound'] = a['compound'].str.replace('GPa','',regex=False)


b=pd.read_excel('dos-212-28atom/32-200GPa-dos/predict_result.xlsx')
b=b[['compound','f2_Tc']]
b['compound'] = b['compound'].str.lower()
b['compound'] = b['compound'] + '-200'


c=pd.read_excel('dos-212-28atom/61-250GPa-dos/predict_result.xlsx')
c=c[['compound','f2_Tc']]
c['compound'] = c['compound'].str.lower()
c['compound'] = c['compound'] + '-250'

d=pd.read_excel('dos-212-28atom/119-300GPa-dos/predict_result.xlsx')
d=d[['compound','f2_Tc']]
d['compound'] = d['compound'].str.lower()
d['compound'] = d['compound'] + '-300'

aa=pd.concat([a,b,c,d])
data=pd.merge(left=data,right=aa,how='left',left_on='flag',right_on='compound')
print(data.head())
data.to_excel('total-new.xlsx')