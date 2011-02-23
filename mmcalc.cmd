:: This simple script allows you to type 'mmcalc' at the Windows command prompt to run MmCalc
@ECHO off
TITLE MmCalc (%CD%)
python mmcalc.py
if errorlevel 1 (ECHO.
ECHO MmCalc error! If you can reproduce this issue, please send the error messages,
ECHO along with a description of how to cause this problem to
ECHO mmcalc@andrewsteele.co.uk
ECHO.
PAUSE)