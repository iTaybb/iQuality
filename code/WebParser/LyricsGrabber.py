# coding: utf-8
# Copyright (C) 2012-2013 Itay Brandes

'''
Module for lyrics grabbing and parsing.
'''

import sys
import urllib2
import xml.dom.minidom
import socket
from difflib import SequenceMatcher
import string
import time
import re

from bs4 import BeautifulSoup

sys.path.append('..') # for project top-level modules
import Config; config = Config.config
from logger import log
import utils

def parse(song, artist):
	"Function searches the web for song lyrics. returns a generator."
	s = '%s - %s' % (artist.strip(), song.strip())
	
	if utils.isHebrew(song) or utils.isHebrew(artist):
		log.debug("Grabbing lyrics for %s from shironet.co.il..." % s)
		gen = parse_shironet(s)
		for lyrics in gen:
			yield lyrics

	else: # if english
		log.debug("Grabbing lyrics for %s from LyricsMode..." % song)
		gen = parse_LyricsMode(song, artist)
		for lyrics in gen:
			yield lyrics
		
		# lets try trim the ()'s or []'s
		_song = song
		_artist = artist
		
		song = utils.trim_between(_song)
		song = utils.trim_between(song, '[', ']')
		if song != _song:
			log.debug("Trimming %s --> %s" % (_song, song))
			
		artist = utils.trim_between(_artist)
		artist = utils.trim_between(artist, '[', ']')
		if artist != _artist:
			log.debug("Trimming %s --> %s" % (_artist, artist))
			
		'''
		The following situation may happen:
		>>> song = "Train - 50 Ways To Say Goodbye"
		>>> artist = "Train"
		'''
		x, y = utils.parse_title_from_filename(song)
		if artist:
			if artist.lower() == x.lower():
				log.debug("Trimming %s --> %s" % (song, y))
				song = y
			if artist.lower() == y.lower():
				log.debug("Trimming %s --> %s" % (song, x))
				song = x
		else:
			log.debug("Setting artist name from nothing to %s" % y)
			song, artist = x, y
		
		if artist != _artist or song != _song:
			s = '%s - %s' % (artist.strip(), song.strip())
			log.debug("Grabbing lyrics for %s from LyricsMode..." % song)
			gen = parse_LyricsMode(song, artist)
			for lyrics in gen:
				yield lyrics
							
		log.debug("Grabbing lyrics for %s from OnlyLyrics..." % song)
		try:
			gen = parse_onlylyrics(song, artist)
		except socket.error:
			return
		for lyrics in gen:
			yield lyrics
			
		if len(artist.split()) == 2:
			flipped_artist = " ".join(artist.split(' ')[::-1])
			log.debug("Grabbing lyrics for %s from OnlyLyrics (flipping last and first name)..." % song)
			try:
				gen = parse_onlylyrics(song, flipped_artist)
			except socket.error:
				return
			for lyrics in gen:
				yield lyrics
			
		log.debug("Grabbing lyrics for %s from ChartLyrics..." % song)
		try:
			gen = parse_ChartLyrics(song, artist)
		except socket.error:
			return
		for lyrics in gen:
			yield lyrics
			
	return

@utils.decorators.retry(socket.error, delay=1, tries=2, logger=log)
def parse_LyricsMode(title, artist):
	"Uses LyricsMode for lyrics grabbing"
	url = "http://www.lyricsmode.com/search.php?search=%s" % urllib2.quote(title.encode("utf8"))
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	domain = "www.lyricsmode.com"
	links = []
	soup = BeautifulSoup(response)
	
	for link in soup.find_all('a', href=re.compile('/lyrics/'), class_='b'):
		links.append("http://%s%s" % (domain, link['href']))
	if not links:
		return
	
	# Sorting lyrics by the artist name
	artist_mod = artist.lower().replace(' ','_')
	links = sorted(links, key=lambda x: SequenceMatcher(lambda t: t == " ", x.split('/')[-2],
					artist_mod).ratio(), reverse=True)
	
	# fetching all the urls and yielding their parsed data
	for url in links:
		log.debug('Fetching %s...' % url)
		try:
			obj = urllib2.urlopen(url)
			response = obj.read()
		except socket.error, e:
			if "Errno 10054" in str(e):
				time.sleep(3)
				gen = parse_LyricsMode(title, artist)
				for x in gen:
					yield x
				return
			else:
				raise e
		obj.close()
			
		soup = BeautifulSoup(response)

		div = soup.find('p', id='lyrics_text')
		if not div:
			return
			
		lyrics = div.text
		if soup.find('p', id='lyrics_signature'): # credits block
			credits = soup.find('p', id='lyrics_signature').text
			lyrics += "\n\n%s" % credits
			
		artist = string.capwords(url.split('/')[-2].replace('_',' '))
		title = string.capwords(url.split('/')[-1].split('.htm')[0].replace('_',' '))
		
		lyricsObj = utils.cls.LyricsData(lyrics, artist, title)
		yield lyricsObj
	return
	
@utils.decorators.retry(socket.error, delay=1, tries=2, logger=log)
def parse_onlylyrics(title, artist):
	"Uses OnlyLyrics.com for lyrics grabbing"
	log.debug("Grabbing lyrics for %s - %s from OnlyLyrics.com..." % (artist, title))
	url = 'http://www.onlylyrics.com/search.php?search=%s&metode=artist&x=0&y=0' % urllib2.quote(artist.encode("utf8"))
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	DOMAIN = "www.onlylyrics.com"
	song_url = ""
	soup = BeautifulSoup(response)

	for link in soup.find_all('a', href=re.compile(r'.+-lyrics-[0-9]+.php')):
		link_artist, link_title = link.text.split(' :: ')
		if title.lower() == link_title.lower():
			song_url = "http://%s%s" % (DOMAIN, link['href'])
			break
	
	if not song_url:
		return ""
	
	obj = urllib2.urlopen(song_url)
	response = obj.read()
	soup = BeautifulSoup(response)
	
	div = soup.find('div', style='width:90%;margin:0 auto;')
	if not div:
		return ""
	
	lyrics = ""
	for tag in div.contents:
		tag = unicode(tag)
		if tag.startswith('<br'):
			tag = "\n"
		lyrics += tag
		
	lyrics += "\n\n [ Lyrics from %s ] " % song_url
	lyricsObj = utils.cls.LyricsData(lyrics, artist, title)
	return (x for x in [lyricsObj])

@utils.decorators.retry(socket.error, delay=1, tries=2, logger=log)
def parse_ChartLyrics(song, artist):
	"Uses ChartLyrics API for lyrics grabbing."
	artist = urllib2.quote(artist.encode("utf8"))
	song = urllib2.quote(song.encode("utf8"))
	url = "http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect?artist=%s&song=%s" % (artist, song)
	log.debug('Fetching %s...' % url)
	try:
		obj = urllib2.urlopen(url)
		response = obj.read()
	except urllib2.HTTPError:
		# lyricsGrabber_ChartLyrics: HTTP Error 500
		return (x for x in [])
	obj.close()
	
	dom = xml.dom.minidom.parseString(response)
	try:
		dom_GetLyricResult = dom.getElementsByTagName('GetLyricResult')[0]
		lyrics = dom_GetLyricResult.getElementsByTagName('Lyric')[0].childNodes[0].data
		artist = dom_GetLyricResult.getElementsByTagName('LyricArtist')[0].childNodes[0].data
		title = dom_GetLyricResult.getElementsByTagName('LyricSong')[0].childNodes[0].data
		
	except IndexError:
		return (x for x in [])
		
	lyrics += "\n\n [ Lyrics from ChartLyrics ] "
	lyricsObj = utils.cls.LyricsData(lyrics, artist, title)
	return (x for x in [lyricsObj])
	
@utils.decorators.retry(socket.error, delay=1, tries=2, logger=log)
def parse_shironet(s):
	"Uses shironet.co.il for hebrew lyrics grabbing"
	log.debug("Grabbing lyrics for %s from shironet.co.il..." % s)
	url = "http://shironet.mako.co.il/searchSongs?q=%s&type=lyrics" % urllib2.quote(s.encode("utf8"))
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	domain = "shironet.mako.co.il"
	links = []
	soup = BeautifulSoup(response)
	
	for link in soup.find_all('a', href=re.compile('artist\?type=lyrics&lang=1')):
		if 'play=true' not in link['href']:
			links.append("http://%s%s" % (domain, link['href']))
	
	# fetching all the urls and yielding their parsed data
	for url in links:
		log.debug('Fetching %s...' % url)
		obj = urllib2.urlopen(url)
		response = obj.read()
		soup = BeautifulSoup(response)

		try:
			lyrics = soup.find(class_="artist_lyrics_text").text
			lyrics += u'\n\n[ נלקח מאתר שירונט: %s ] ' % url
			artist = soup.find(class_="artist_singer_title").text
			title = soup.find(class_="artist_song_name_txt").text.strip()
		except AttributeError:
			return
			
		lyricsObj = utils.cls.LyricsData(lyrics, artist, title)
		yield lyricsObj
	return 