#!/bin/sh
mkdir pdos_h
for i in POSCAR-1  POSCAR-2  POSCAR-3  POSCAR-4   POSCAR-7
do
cd $i
Tefermi=`grep E-fermi scf/OUTCAR | cut -d' ' -f5`
cd dos
Fefermi=`sed -n '6p' DOSCAR | awk '{print $4}'`
sed -i "6s/"${Fefermi}"/"${Tefermi}"/" DOSCAR
#sed -i '6s/${Fefermi}/${Tefermi}/' DOSCAR
#cd ./001 && echo -e '1\n102\n2\n{k_spacing}\n' | vaspkit;
echo -e '11\n113\n' | vaspkit;
comp=`pwd | cut -d'/' -f8`
cp PDOS_H.dat ../../pdos_h/${comp}-${i}-PDOS_H-300GPa.dat
cd ../../
done
python3 tiqudoszhi.py > efdos.dat 
