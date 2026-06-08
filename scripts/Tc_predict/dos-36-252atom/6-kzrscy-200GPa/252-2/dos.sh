#!/bin/sh
for i in POSCAR-3 POSCAR-4 POSCAR-5
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
