#!/bin/sh
for i in POSCAR-1 POSCAR-2 POSCAR-3 POSCAR-4 POSCAR-7
do
cd $i
mkdir dos
cp ../../../dos/* dos
cd scf
cp CHG CHGCAR POSCAR POTCAR ../dos
cd ../dos
sbatch vasp.sh
cd ../../
done
