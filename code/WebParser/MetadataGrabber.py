# coding: utf-8
# Copyright (C) 2012-2013 Itay Brandes

'''
MetadataGrabber: Module for project's metadata grabbers.
Tracks data, Albums data, Artists data - it's all goes here.
'''

import sys
import urllib2
import xml.dom.minidom
import re
from difflib import SequenceMatcher

from bs4 import BeautifulSoup

sys.path.append('..') # for project top-level modules
import Config; config = Config.config
from logger import log
import utils

import LyricsGrabber

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_musicBrainz(title, artist):
	"Uses musicBrainz API for releases data grabbing"
	url = 'http://www.musicbrainz.org/ws/2/recording?query="%s" AND artist:"%s"' % (urllib2.quote(title.encode("utf8")), urllib2.quote(artist.encode("utf8")))
	url = utils.url_fix(url)
	
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	dom = xml.dom.minidom.parseString(response)
	
	try:
		tag = dom.getElementsByTagName('metadata')[0].getElementsByTagName('recording-list')[0] \
							.getElementsByTagName('recording')[0].getElementsByTagName('tag-list')[0] \
							.getElementsByTagName('tag')[0].getElementsByTagName('name')[0].childNodes[0].data
	except IndexError:
		tag = ""
	
	try:
		artist = dom.getElementsByTagName('metadata')[0].getElementsByTagName('recording-list')[0] \
							.getElementsByTagName('recording')[0].getElementsByTagName('artist-credit')[0] \
							.getElementsByTagName('name-credit')[0].getElementsByTagName('artist')[0] \
							.getElementsByTagName('name')[0].childNodes[0].data
	except IndexError:
		artist = ""
		
	try:
		release_list_dom = dom.getElementsByTagName('metadata')[0].getElementsByTagName('recording-list')[0] \
							.getElementsByTagName('recording')[0].getElementsByTagName('release-list')[0] \
							.getElementsByTagName('release')
	except IndexError:
		return None
	
	release_dict = {}						
	for dom in release_list_dom:
		d = {}
		d['title'] = dom.getElementsByTagName('title')[0].childNodes[0].data if dom.getElementsByTagName('title') else ""
		d['date'] = dom.getElementsByTagName('date')[0].childNodes[0].data if dom.getElementsByTagName('date') else ""
		d['country'] = dom.getElementsByTagName('country')[0].childNodes[0].data if dom.getElementsByTagName('country') else ""
		d['artist'] = artist
		d['tag'] = tag
		release_dict[dom.attributes.values()[0].value] = d
		
	return release_dict

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_songlyrics_songs_by_lyrics(searchString):
	'''
	Uses songlyrics.com for searching songs by a line of it's lyrics.
	
	Returns list of songs.
	'''
	log.debug("Searching for a song that contains the line '%s' on songlyrics.com..." % searchString)
	url = "http://www.songlyrics.com/index.php?section=search&searchW=%s&submit=Search&searchIn4=lyrics" % urllib2.quote(searchString.encode("utf8"))
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	
	remove_strings = ['(remix)', '(Remix)', '(live)', '(Live)', '(single)', '(Single)']
	chars_to_trim = ['\n', '\r', ' ', ',', "'", '.', '?', '!']
	searchString = searchString.lower()
	track = ""
	soup = BeautifulSoup(response)

	for div in soup.find_all('div', class_='serpresult'):
		if 'cover)' in div.text.lower() or 'cover]' in div.text.lower():
			continue
		if not div.a:
			continue
			
		artist = div.a.img['alt']
		title = div.a['title']
		for s in remove_strings:
			title.replace(s, '')
		title = title.strip()
		
		gen = LyricsGrabber.parse(title, artist)
		if gen:
			lyrics = gen.next()
			if lyrics:
				lyrics = lyrics.lyrics.lower()
				for c in chars_to_trim:
					lyrics = lyrics.replace(c, '')
				matching_blocks = SequenceMatcher(None, lyrics, searchString.replace(' ','')).get_matching_blocks()
				biggest_match_block_size = sorted(matching_blocks, key=lambda x:x.size, reverse=True)[0].size
				if 1.0*biggest_match_block_size/len(searchString) > 0.70:
					track = "%s - %s" % (artist, title)
					
		break
		
	return track
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_animelyrics_songs_by_lyrics(searchString):
	"Uses AnimeLyrics.com for lyrics grabbing by a line of it's lyrics"
	log.debug("Searching for a song that contains the line '%s' on AnimeLyrics.com..." % searchString)
	url = 'http://www.animelyrics.com/search.php?q=%s&t=romaji&searchcat=anime' % urllib2.quote(searchString.encode("utf8"))
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	DOMAIN = "www.animelyrics.com"
	CREDITS = "Lyrics from Animelyrics.com"
	soup = BeautifulSoup(response)

	for tag in soup.find_all(text=re.compile('RESULT ITEM START')):
		# url = "http://%s%s" % (DOMAIN, tag.next_element['href'])
		title = tag.next_element.text
		artist = tag.previous_element.previous_element
		
		return "%s - %s" % (artist, title)
		
		# obj = urllib2.urlopen(url)
		# response = obj.read()
		
		# soup = BeautifulSoup(response)
		# lyrics = '\n'.join([x.text.replace(CREDITS,'').replace(u'\xa0',' ').replace('\r','\n').replace('  ',' ') for x in soup.find_all('td', class_='romaji')])
		# lyrics += "\n\n [ Lyrics from %s ] " % url
		# lyricsObj = utils.cls.LyricsData(lyrics, artist, title)
		
		# yield lyricsObj
		
	return ""

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def musicbrainz_artist_search(s):
	'''
	Uses musicbrainz for english artist searching.
	
	Returns a list of MetadataArtist.
	'''
	log.debug("Searching for %s in the artists list on musicbrainz..." % s)
	url = 'http://www.musicbrainz.org/ws/2/artist?query=artist:"%s"&limit=5' % utils.url_fix(s)
	log.debug('Fetching %s...' % url)

	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	l = []
	soup = BeautifulSoup(response, 'xml')
	for artist in soup.find_all('artist'):
		if int(artist.attrs['ext:score']) > 94:
			id_ = artist['id']
			type_ = artist['type'] if artist.has_key('type') else ""
			name = artist.find('name').text
			score = artist.attrs['ext:score']
			disambiguation = artist.find('disambiguation').text if artist.find('disambiguation') else ""
			obj = utils.cls.MetadataArtist(id_, name, 'musicbrainz', type_, score, disambiguation=disambiguation)
			l.append(obj)
	return l

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def musicbrainz_release_search(arid):
	'''
	Uses musicbrainz for english releases.
	
	Returns a three objects of MetadataRelease lists: albums, singles, others.
	'''
	log.debug("Searching for artist %s in the releases list on musicbrainz..." % arid)
	url = 'http://www.musicbrainz.org/ws/2/release/?query=arid:"%s" AND status :"official"' % arid
	log.debug('Fetching %s...' % url)
	url = utils.url_fix(url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	release_groups = {}
	final_releases = []
	soup = BeautifulSoup(response, 'xml')

	for release in soup.find_all('release'):
		group = release.find('release-group')
		reid = release['id']
		rgid = group['id']
		
		if not rgid in release_groups.keys():
			release_groups[rgid] = {}
			release_groups[rgid]['releases'] = {}
			release_groups[rgid]['type'] = group['type'] if group.has_key('type') else ""
		
		d = {}
		d['date'] = release.date.text if release.date else ""
		d['title'] = release.title.text
		d['count'] = release.find('medium-list').find('track-count').text
		d['artistname'] = release.artist.name
		release_groups[rgid]['releases'][reid] = d

	for rgid, d in release_groups.items():
		list_of_rids = d['releases'].items()
		if list_of_rids:
			sorted(list_of_rids, key=(lambda x:x[1]['count']))
			reid, d2 = list_of_rids[0]
			
			obj = utils.cls.MetadataRelease(reid, d2['title'], 'musicbrainz', d['type'], d2['date'], d2['count'], arid, d2['artistname'])
			final_releases.append(obj)
	
	final_releases = sorted(final_releases, key=lambda x:x.date)
	albums = [x for x in final_releases if x.type == 'Album']
	singles = [x for x in final_releases if x.type == 'Single']
	others = [x for x in final_releases if x.type not in ['Album', 'Single']]
	
	# for album in albums:
		# print "Album %s (%s tracks, out at %s)" % (album.title, album.count, album.date)
	# for single in singles:
		# print "Single %s (%s tracks)" % (single.title, single.count)
	# for other in others:
		# print "Other %s (%s tracks)" % (other.title, other.count)
		
	return albums, singles, others

@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def musicbrainz_recording_search(reid):
	'''
	Uses musicbrainz for english recording by reid search.
	
	Returns a list of tracks.
	'''
	log.debug("Searching for album %s in the tracks list on musicbrainz..." % reid)
	
	url = 'http://www.musicbrainz.org/ws/2/recording/?query=reid:"%s"' % reid
	log.debug('Fetching %s...' % url)
	url = utils.url_fix(url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	tracks = []
	def sort_key(x):
		"Sort key by a release's track amount"
		num = x.find('release-list').find('medium-list').medium.find('track-list').track.number.text
		non_decimal = re.compile(r'[^\d.]+')
		num = non_decimal.sub('', num)
		num = int(num) if num else 0
		return num
		
	soup = BeautifulSoup(response, 'xml')

	for track in sorted(soup.find_all('recording'), key=sort_key):
		name = track.title.text.replace(u'\u2019', "'")
		tracks.append(name)
		
	return tracks
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def shironet_artist_search(s):
	'''
	Uses shironet.co.il for hebrew artist searching.
	
	Returns a list of MetadataArtists.
	'''
	log.debug("Searching for %s in the artists list in shironet.co.il..." % s)
	url = "http://shironet.mako.co.il/searchArtists?q=%s" % urllib2.quote(s.encode("utf8"))
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	# Setting vars
	l = []
	
	# Checks if an artist that matches by at least 94% exist. Sets artist_id.
	soup = BeautifulSoup(response)
	for link in soup.find_all('a', class_="search_link_name_big", href=True):
		if SequenceMatcher(lambda x: x == " ", s, link.text).ratio() > 0.94:
			artist_id = link['href'].split('prfid=')[-1].split('&')[0]
			obj = utils.cls.MetadataArtist(artist_id, s, 'shironet', has_albums=False)
			l.append(obj)
		
	for link in soup.find_all('a', href=re.compile('discography')):
		for artist in l:
			if 'prfid=%s' % artist.id in link['href']:
				artist.has_albums = True
				break
	
	return l
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def shironet_artist_songs(artist_id):
	'''
	Uses shironet.co.il for artist's songs search.
	
	Returns list of songs.
	'''
	log.debug("Searching for ArtistID %s's songs in shironet.co.il..." % artist_id)
	url = "http://shironet.mako.co.il/artist?type=works&lang=1&prfid=%s" % artist_id
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	soup = BeautifulSoup(response)
	l = []

	for link in soup.find_all('a', class_="artist_player_songlist"):
		text = link.text.strip()
		if text != u"לרשימה המלאה...":
			l.append(text)
	l = utils.delete_duplicates_ordered(l)
	
	for i, v in enumerate(l):
		l[i] = utils.cls.MetadataRelease('0', v, 'shironet', arid=artist_id)
	
	return l
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def shironet_artist_albums(artist_id):
	'''
	Uses shironet.co.il for artist's albums search.
	
	Returns list of MetadataRelease
	'''
	log.debug("Searching for ArtistID %s's albums in shironet.co.il..." % artist_id)
	url = "http://shironet.mako.co.il/artist?type=discography&lang=1&prfid=%s" % artist_id
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	l = []
	soup = BeautifulSoup(response)
	
	for link in soup.find_all('a', class_="artist_more_link"):
		album_id = link['href'].split('discid=')[-1].split('&')[0]
		album_text = link.text
		album_year = str(link.parent.span.text.strip(' ()'))
		
		obj = utils.cls.MetadataRelease(album_id, album_text, 'shironet', date=album_year, arid=artist_id)
		l.append(obj)
	
	return l
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def shironet_album_songs(artist_id, album_id):
	'''
	Uses shironet.co.il for album's songs search.
	
	Returns list of songs.
	'''
	log.debug("Searching for ArtistID %s, AlbumID %s's songs in shironet.co.il..." % (artist_id, album_id))
	url = "http://shironet.mako.co.il/artist?type=disc&lang=1&prfid=%s&discid=%s" % (artist_id, album_id)
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	l = []
	soup = BeautifulSoup(response)

	for link in soup.find_all('td', class_="artist_normal_txt"):
		if u'\xa0' in link.text:
			x = link.text.split(u'\xa0')[1].strip()
		else:
			x = ".".join(link.text.split('.')[1:]).strip()
		if x:
			l.append(x)
			
	return l
	
@utils.decorators.retry(Exception, logger=log)
@utils.decorators.memoize(config.memoize_timeout)
def parse_shironet_songs_by_lyrics(searchString):
	'''
	Uses shironet.co.il for searching songs by a line of it's lyrics.
	
	Returns list of songs.
	'''
	log.debug("Searching for a song that contains the line '%s' in shironet.co.il..." % searchString)
	url = "http://shironet.mako.co.il/searchSongs?q=%s&type=lyrics" % urllib2.quote(searchString.encode("utf8"))
	log.debug('Fetching %s...' % url)
	obj = urllib2.urlopen(url, timeout=config.metadata_timeout)
	response = obj.read()
	obj.close()
	
	chars_to_trim = ['\n', '\r', ' ', ',', "'", '.', '?', '!']
	searchString = searchString.lower()
	track = ""
	soup = BeautifulSoup(response)

	for link in soup.find_all('a', class_="search_link_name_big", href=re.compile('wrkid=')):
		title = link.text.strip()
		artist = link.find_next_sibling('a').text.strip()
		
		gen = LyricsGrabber.parse(title, artist)
		if gen:
			lyrics = gen.next()
			if lyrics:
				lyrics = lyrics.lyrics.lower()
				for c in chars_to_trim:
					lyrics = lyrics.replace(c, '')
				matching_blocks = SequenceMatcher(None, lyrics, searchString.replace(' ','')).get_matching_blocks()
				biggest_match_block_size = sorted(matching_blocks, key=lambda x:x.size, reverse=True)[0].size
				if 1.0*biggest_match_block_size/len(searchString) > 0.70:
					track = "%s - %s" % (artist, title)
		
		break
		
	return track