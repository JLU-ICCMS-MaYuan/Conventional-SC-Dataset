#!/bin/sh 

#pot_PATH=/work/home/zhangpy/workplace/HEA/SQS/7/pot
#pot_PATH=/work/home/zhangpy/workplace/HEA/SQS/8-ReW/2/pot
#pot_PATH=/work/home/zhangpy/workplace/HEA/SQS/pot
pot_PATH=/public/home/bys/work/opt/pot
ls stru > ls.log
for aa in $(cat ls.log)
do
mkdir $aa
cp INCAR_* $aa
cp vasp.sh $aa
cp stru/$aa $aa
cd $aa 
cp $aa POSCAR
#sed -i 's/Ca/K/g' POSCAR
sed -i 's/Sr/Na/g' POSCAR
sed -i 's/Y/Mg/g' POSCAR
sed -i 's/Ce/Zr/g' POSCAR
els=`sed -n '6p' POSCAR`
rm -rf POTCAR
for el in $els
do
    if [ $el = 'Re' ]; then
        cat $pot_PATH/POTCAR_${el} >> POTCAR
    elif [ $el = 'W' ]; then
        cat $pot_PATH/POTCAR_${el} >> POTCAR
    else
        cat $pot_PATH/POTCAR_${el} >> POTCAR
    fi
done
#sbatch vasp.sh
cd ..
done
