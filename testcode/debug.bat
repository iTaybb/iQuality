exit()
cd c:\scripts\iQuality\code
python
import WebParser
w = WebParser.LinksGrabber
o = w.search_soundcloud('naruto')
w.get_soundcloud_dl_link(o[0])