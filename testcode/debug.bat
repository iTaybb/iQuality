exit()
cd c:\scripts\iQuality\code
python
import Main
from Main import utils

o = utils.classes.MetaUrl(r'http://treeswingers.files.wordpress.com/2012/05/07-harlem-shake.mp3')
Main.HTTPQuery.get_file_details(o)

w = WebParser.LinksGrabber
o = w.search_soundcloud('naruto')
w.get_soundcloud_dl_link(o[0])