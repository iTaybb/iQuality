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
import bs4.element

sys.path.append(r'C:\Scripts\iQuality\code')
import utils
import WebParser

s = "soko kara nani ga mieru"

url = 'http://www.animelyrics.com/search.php?q=%s&t=romaji&searchcat=anime' % s.replace(' ', '+')
obj = urllib2.urlopen(url)
response = obj.read()

DOMAIN = "www.animelyrics.com"
CREDITS = "Lyrics from Animelyrics.com"
soup = BeautifulSoup(response)

for tag in soup.find_all(text=re.compile('RESULT ITEM START')):
	url = "http://%s%s" % (DOMAIN, tag.next_element['href'])
	title = tag.next_element.text
	artist = tag.previous_element.previous_element
	
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	soup = BeautifulSoup(response)
	lyrics = '\n'.join([x.text.replace(CREDITS,'').replace(u'\xa0',' ').replace('\r','\n').replace('  ',' ') for x in soup.find_all('td', class_='romaji')])
	lyrics += "\n\n [ Lyrics from %s ] " % url
	lyricsObj = utils.classes.LyricsData(lyrics, artist, title)
	
	yield lyricsObj

pdb.set_trace()
	
with open("test.txt", 'w') as f:
	for x in tracks:
		x = x.encode('utf-8')
		f.write("%s\n" % (x))

pdb.set_trace()