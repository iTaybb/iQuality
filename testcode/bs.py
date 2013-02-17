# coding: utf-8
# Copyright (C) 2012 Itay Brandes

import sys
import urllib2
from difflib import SequenceMatcher
from urlparse import urlparse, parse_qs
import re
import httplib
import json
import pdb
from pprint import pprint as pp

from bs4 import BeautifulSoup

sys.path.append(r'C:\Scripts\iQuality\code')
import utils
import WebParser

url = 'http://www.youtube.com/playlist?p=SPv1EAqcvJFuG-CMLxveY7eNEcse3xXm1a'
obj = urllib2.urlopen(url)
response = obj.read()
soup = BeautifulSoup(response)

pdb.set_trace()

for link in soup.find_all('a', class_='yt-uix-tile-link yt-uix-sessionlink', href=re.compile('^/watch')):
	pdb.set_trace()
	url = link['href'] + link['url'] # dont ask me why. dilandabu decided to split their url addresses.
	
	utils.classes.MetaUrl(url, 'SoundCloud', track)

pdb.set_trace()
	
with open("test.txt", 'w') as f:
	for x in tracks:
		x = x.encode('utf-8')
		f.write("%s\n" % (x))

pdb.set_trace()