# coding: utf-8
# Copyright (C) 2012-2013 Itay Brandes

'''
Module for project's Web Services that are not lyrics or links grabbing.
'''

import sys
import urllib2, json
import httplib, xml.dom.minidom
import re
import json
from collections import OrderedDict

from bs4 import BeautifulSoup

sys.path.append('..') # for project top-level modules
import Config; config = Config.config
from logger import log
import utils

__all__ = ['spell_fix', 'googleImageSearch']

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def spell_fix(s):
	"Uses google API to fix spelling"
	data = u"""
	<spellrequest textalreadyclipped="0" ignoredups="1" ignoredigits="1" ignoreallcaps="0">
	<text>%s</text>
	</spellrequest>
	"""
	data = data % s
	data_octets = data.encode('utf-8')
	new_s = s
	
	if log:
		log.debug("Checking spell suggestions for '%s'..." % s)
	
	if utils.isHebrew(s):
		log.debug("Search string is hebrew. Skipping on spell checking...")
		return s
	
	con = httplib.HTTPConnection("www.google.com", timeout=config.webservices_timeout)
	con.request("POST", "/tbproxy/spell?lang=en", data_octets, {'content-type': 'text/xml; charset=utf-8'})
	response = con.getresponse().read()
	
	if log:
		log.debug("Response: %s" % response)
	
	dom = xml.dom.minidom.parseString(response)
	dom_data = dom.getElementsByTagName('spellresult')[0]

	for i, node in enumerate(dom_data.childNodes):
		att_o = int(node.attributes.item(2).value) # The offset from the start of the text of the word
		att_l = int(node.attributes.item(1).value) # Length of misspelled word
		att_s = int(node.attributes.item(0).value) # Confidence of the suggestion
		if not node.firstChild: # no suggestions
			return s
		text = node.firstChild.data.split("\t")[0]
		
		# print "%s --> %s (s: %d)" % (s[att_o:att_o+att_l], text, att_s)
		if att_s: # if suggestion is confident
			new_s = new_s.replace(s[att_o:att_o+att_l], text)
	
	if log:
		if s == new_s:
			log.debug("No suggestions were accepted.")
		else:
			log.debug("Suggestions were accepted: %s --> %s." % (s, new_s))
		
	return new_s
	
@utils.decorators.retry(Exception, logger=log)
def google_autocomplete(s):
	"Uses google autocomplete API"
	url = "http://suggestqueries.google.com/complete/search?client=firefox&q=%s" % urllib2.quote(s.encode("utf8"))
	obj = urllib2.urlopen(url, timeout=config.webservices_timeout)
	response = obj.read()
	data = json.loads(response)
	
	return data[1]

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def googleImageSearch(s):
	"Uses google API to image grabbing"
	s = urllib2.quote(s.encode("utf8"))
	url = "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=%s" % s
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.webservices_timeout)
	json_data = obj.read()
	data = json.loads(json_data)
	if data['responseData'] == 'null':
		return "Response %s: %s" % (data['responseStatus'], data['responseDetails'])
	
	images = [image_info['unescapedUrl'] for image_info in data['responseData']['results']]
	log.debug('Got images: %s' % str(images))
	return images

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_billboard():
	"Parses the top 100 songs from billboard.com rss feed"
	url = 'http://www.billboard.com/rss/charts/hot-100'
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.webservices_timeout)
	response = obj.read()
	obj.close()
	
	soup = BeautifulSoup(response)
	songs = [x.text for x in soup.find_all('title')][1:]
	songs = [x.split(': ', 1)[1] for x in songs]
	songs = ["%s - %s" % (x.split(', ', 1)[1].split('Feat', 1)[0], x.split(', ', 1)[0]) for x in songs]
	songs = [x.replace('  ', ' ') for x in songs]
	
	# dom = xml.dom.minidom.parseString(response)
	# items = dom.getElementsByTagName('rss')[0].getElementsByTagName('channel')[0].getElementsByTagName('item')
	# songs = [x.getElementsByTagName('title')[0].childNodes[0].data for x in items]
	# songs = [x.split(':', 1)[1].strip() for x in songs]
	# songs = ["%s - %s" % (x.split(', ', 1)[1].split('Feat', 1)[0], x.split(', ', 1)[0]) for x in songs]
	
	return songs
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_uktop40():
	"Parses the top 40 songs from uktop40.com rss feed"
	url = r'http://www.uktop40.co.uk/official_top_40.rss'
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.webservices_timeout)
	response = obj.read()
	obj.close()
	
	soup = BeautifulSoup(response)
	songs = [x.text for x in soup.find_all('title')][2:]
	songs = [x.split(') ', 1)[1] for x in songs]
	songs = [utils.trim_between(utils.trim_between(x), '[', ']') for x in songs]
	songs = [utils.convert_html_entities(x) for x in songs]
	songs = [x.strip() for x in songs]
	
	return songs

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_glgltz():
	"Parses the top songs from glgltz"
	url = "http://www.glgltz.co.il/default.asp"
	obj = urllib2.urlopen(url, timeout=config.webservices_timeout)
	response = obj.read()

	parardeIDs = []
	soup = BeautifulSoup(response)

	for link in soup.find_all('a', href=re.compile('paradeID')):
		parardeID = link['href'].split('paradeID=')[-1].split('&')[0]
		parardeIDs.append(parardeID)
	
	for parardeID in parardeIDs:
		data_octets = "p=%s&" % parardeID
		data_octets += 'iint=0&iann=0&pt=%D7%94%D7%9E%D7%A6%D7%A2%D7%93+%D7%94%D7%99%D7%A9%D7%A8%D7%90%D7%9C%D7%99&nos=2&submit1=%D7%9C%D7%AA%D7%97%D7%99%D7%9C%D7%AA+%D7%94%D7%93%D7%99%D7%A8%D7%95%D7%92+%D7%A0%D7%90+%D7%9C%D7%9C%D7%97%D7%95%D7%A5+%D7%9B%D7%90%D7%9F'
		
		con = httplib.HTTPConnection("www.glgltz.co.il")
		con.request("POST", "/voteSong1.asp", data_octets, {'content-type': 'application/x-www-form-urlencoded'})
		response = con.getresponse().read()
		
		excluded_words = [u'דרגו את', u'המצעד הישראלי', u'שלב 1 מתוך 2']
		songs = []
		soup = BeautifulSoup(response)

		for link in soup.find_all('tr', class_="trItem"):
			song = link.contents[5].text
			if utils.isHebrew(song) and not song in excluded_words:
				song = "%s - %s" % (song.split(' - ', 1)[1], song.split(' - ', 1)[0])
				songs.append(song)
		if songs: break
	else:
		return []
	return songs
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_chartscoil():
	"Parses the top songs from charts.co.il"
	url = r"http://www.charts.co.il/chartsvote.asp?chart=1"
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.webservices_timeout)
	response = obj.read()
	obj.close()
	
	l = []
	soup = BeautifulSoup(response)
	
	for link in soup.find_all('img', src=re.compile('/charts-co-il/singles-heb-pic')):
		l.append(link['alt'])
	return l

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def get_currentusers():
	"Function queries the iQuality website for the current application users counter"
	obj = urllib2.urlopen(config.online_users_counter_webpage, timeout=config.webservices_timeout)
	x = obj.read(1024)
	obj.close()
	return int(x)

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def get_newestversion():
	"Function queries the iQuality website for the the newest version available"
	obj = urllib2.urlopen(config.newest_version_API_webpage, timeout=config.webservices_timeout)
	x = obj.read(1024)
	obj.close()
	return float(x)
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def get_components_data():
	"Function queries the iQuality website for components json data"
	obj = urllib2.urlopen(config.components_json_url, timeout=config.webservices_timeout)
	data = obj.read()
	obj.close()
	obj = urllib2.urlopen("%s.sign" % config.components_json_url, timeout=config.webservices_timeout)
	sign = obj.read()
	obj.close()
	
	if utils.verify_signature(data, sign, config.pubkey_path):
		log.debug('components_json_url signature check passed')
		return json.loads(data, object_pairs_hook=OrderedDict)
	log.error('components_json_url signature check FAILED')
	return {}