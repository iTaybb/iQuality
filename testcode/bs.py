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

"Parses the top 100 songs from billboard.com rss feed"
url = 'http://www.billboard.com/rss/charts/hot-100'
obj = urllib2.urlopen(url)
response = obj.read()
obj.close()

songs = []
soup = BeautifulSoup(response)
for item in soup.find_all('item'):
	artist = item.artist.text.split('Featuring')[0]
	title = item.chart_item_title.text
	
	song = "%s - %s" % (artist, title)
	song = song.replace('  ', ' ')
	
	songs.append(song)
	

pdb.set_trace()
songs = [x.text for x in soup.find_all('title')][1:]
songs = [x.split(': ', 1)[1] for x in songs]
songs = ["%s - %s" % (x.split(', ', 1)[1].split('Feat', 1)[0], x.split(', ', 1)[0]) for x in songs]
songs = [x.replace('  ', ' ') for x in songs]

sys.exit()

# s = "soko kara nani ga mieru"

# url = 'http://www.animelyrics.com/search.php?q=%s&t=romaji&searchcat=anime' % s.replace(' ', '+')
url = "http://bandcamp.com/search?q=naruto"
obj = urllib2.urlopen(url)
response = obj.read()

links = []
soup = BeautifulSoup(response)

for tag in soup.find_all('a', class_='artcont'):
	links.append(tag['href'])
	

pdb.set_trace()

js_data = [x for x in soup.find_all('script') if x.text.strip().startswith('Control.registerController')][0].text
json_data = [x for x in js_data.split('\n') if x.strip().startswith('trackinfo')][0].split('trackinfo', 1)[1].strip(' : ,\'')
for song in json.loads(json_data):
	print "%s: %s" % (song['title'], song['file'].values()[0])

pdb.set_trace()

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
	
	print lyricsObj

pdb.set_trace()
	
with open("test.txt", 'w') as f:
	for x in tracks:
		x = x.encode('utf-8')
		f.write("%s\n" % (x))

pdb.set_trace()