#!/bin/sh
for i in POSCAR-3 POSCAR-4 POSCAR-5
do
cd $i
mkdir scf
cp ../../../scf/* scf
cp POSCAR POTCAR scf
cd scf
sbatch vasp.sh
cd ../../
done
