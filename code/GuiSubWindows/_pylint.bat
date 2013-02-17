REM @echo off
cd /d %0\.. 
c:\Python27\Scripts\pylint --disable C0301,W0312,C0103 %~dpnx1 > pylint.txt