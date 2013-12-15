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

if True:
	# http://soundcloud.com/tracks/search?page=1&q%5Bfulltext%5D=naruto
	title = "Naruto"
	domain = "soundcloud.com"
	url = 'http://soundcloud.com/tracks/search?page=1&q%%5Bfulltext%%5D=%s' % title
	# log.debug("[SoundCloud] Parsing %s... " % url)
	obj = urllib2.urlopen(url)
	response = obj.read()
	soup = BeautifulSoup(response)
	
	pdb.set_trace()
	
	regex = re.compile("^/(?!(?:you|pages|premium|login|people|groups|tracks|tags)/)[^/]+/(?!.+(?:sets/|/share-options|/download))[^?]+$")
	tags = soup.find_all('a', href=regex)
	links = ["http://%s%s" % (domain, tag['href']) for tag in tags]