CD /D C:\Scripts\iQuality\code\WebParser
python C:\Scripts\iQuality\testcode\kernprof.py -l LinksGrabber.py

python -m line_profiler LinksGrabber.py.lprof > LinksGrabber.py.lprof.txt
del C:\Scripts\iQuality\code\WebParser\LinksGrabber.py.lprof
move C:\Scripts\iQuality\code\WebParser\LinksGrabber.py.lprof.txt C:\Scripts\iQuality\testcode\LinksGrabber.py.lprof.txt
notepad C:\Scripts\iQuality\testcode\LinksGrabber.py.lprof.txt

REM pause