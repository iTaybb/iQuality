@echo off

REM py.test -v --pdb
 py.test -v --pdb -k test_parse_Youtube_playlist
del /F /S /Q __pycache__ 1> NUL
pause