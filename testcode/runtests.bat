@echo off

py.test -v --pdb
REM py.test -v --pdb -k test_MetadataGrabber_songlyrics_songs_by_lyrics
del /F /S /Q __pycache__ 1> NUL
pause