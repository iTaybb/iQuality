import sys
sys.path.append(r'C:\Scripts\iQuality\code')

import Main
from Main import utils
import WebParser

# @profile
def main():
	w = WebParser.LyricsGrabber
	o = w.search('nicki minaj', 15)
	
main()