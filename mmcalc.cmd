:: This simple script allows you to type 'mmcalc' at the Windows command prompt to run MmCalc
@ECHO off
TITLE MmCalc (%CD%)
python mmcalc.py
if errorlevel 1 (ECHO MmCalc error! If you can reproduce this issue, please send the error messages along with a description of how to cause this problem to mmcalc@andrewsteele.co.uk
PAUSE)