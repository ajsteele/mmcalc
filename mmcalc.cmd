@ECHO off
TITLE MmCalc
python mmcalc.py
if errorlevel 1 (ECHO MmCalc error! If you can reproduce this issue, please send the Python error messages along with a description of how to cause this problem to mmcalc@andrewsteele.co.uk)