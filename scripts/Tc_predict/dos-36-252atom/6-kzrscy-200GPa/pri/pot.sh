#!/bin/sh
pot_PATH=/public/home/bys/work/opt/pot
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
