exit()
cd c:\scripts\iQuality\code
python
import pdb
import Main
from Main import utils
import WebParser

w = WebParser.LyricsGrabber
o = w.parse_LyricsMode('naruto', "shippuden")
o.next()