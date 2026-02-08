#!/bin/sh
for i in POSCAR-1 POSCAR-2 POSCAR-3 POSCAR-4 POSCAR-7
do
cd $i
mkdir scf
cp ../../../scf/* scf
cp POSCAR POTCAR scf
cd scf
sbatch vasp.sh
cd ../../
done
