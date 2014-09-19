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

i = 1
song = "naruto shippuden"

# http://www.musicaddict.com/mp3/naruto-shippuden/page-2.html
url = 'http://www.musicaddict.com/mp3/%s/page-%d.html' % (song.replace('-','').replace('_','').replace(' ','-').lower(), i)
# log.debug("[MusicAddict] Parsing %s... " % url)
obj = urllib2.urlopen(url)
response = obj.read()

DOMAIN = 'http://www.musicaddict.com/'
t_links = []
links = []
soup = BeautifulSoup(response)

for span in soup.find_all('span', class_='dl_link'):
	url = DOMAIN + span.a['href']
	t_links.append(url)
	
for link in t_links:
	obj = urllib2.urlopen(link)
	response = obj.read()
	soup = BeautifulSoup(response)
	js = soup.find('script', src=re.compile(r"js3/\d+.js"))
	jsUrl = DOMAIN + js['src']
	
	obj = urllib2.urlopen(jsUrl)
	response = obj.read()
	url = re.search('src="(.+?)"', response).group(1)
	print url
	links.append(url)
	
# log.debug("[MusicAddict] found %d links" % len(links))

# if not links:
	# break

# for link in links:
	# yield utils.cls.MetaUrl(link, 'MusicAddict')