exit()
cd c:\scripts\iQuality\code
python
import Main
from Main import utils
import WebParser

w = WebParser.LinksGrabber
o = w.parse_bandcamp('naruto')
print o.next()
print o.next()
print o.next()