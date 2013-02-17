@echo off

py.test -v --pdb
REM py.test -v --pdb -k parse_sound
del /F /S /Q __pycache__ 1> NUL
pause