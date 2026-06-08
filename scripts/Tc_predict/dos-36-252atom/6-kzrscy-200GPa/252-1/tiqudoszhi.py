import glob
files=glob.glob('./pdos_h/*.dat')
for file in files:
    with open(file) as f:
        lines=[i.strip() for i in f.readlines()]
        for i in range(len(lines)):
            if float(lines[i+1].split()[0]) > 0:
                x1=float(lines[i].split()[0])
                y1=float(lines[i].split()[-1])
                x2=float(lines[i+1].split()[0])
                y2=float(lines[i+1].split()[-1])
                fermi=(x1*y2-x2*y1)/(x1-x2)
                print(f'{file}  fermi:  {fermi}')
                break                                                        
