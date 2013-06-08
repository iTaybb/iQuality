# Copyright (C) 2012-2013 Itay Brandes

'''
Module for Mp3 links grabbing.
'''

import sys
import urllib2
import json
import xml.dom.minidom
from urlparse import parse_qs, urlparse
import time
import itertools
import re
from bs4 import BeautifulSoup

sys.path.append('..') # for project top-level modules
from threadpool import ThreadPool
import Config; config = Config.config
from logger import log
from CustomExceptions import YoutubeException
import utils

@utils.decorators.retry(Exception, logger=log)
def parse(title, source, n = None):
	'''
	Function parses the source search page and returns the .mp3 links in it.
	@param title: Search string.
	@param source: Search website source. Value can be dilandau, mp3skull, youtube, seekasong.
	
	@return links: .mp3 url links generator.
	'''
	
	source = source.lower()
	if source == "dilandau":
		gen = parse_dilandau(title)
	elif source == "mp3skull":
		gen = parse_Mp3skull(title)
	elif source == "soundcloud":
		gen = parse_soundcloud_api2(title)
	elif source == 'bandcamp':
		gen = parse_bandcamp(title)
	elif source == "youtube":
		gen = parse_Youtube(title)
	else:
		log.error('no source "%s". (from parse function in WebParser)' % source)
		gen = (x for x in []) # empty generator
	if n:
		gen = itertools.islice(gen, n)
	return gen

def parse_dilandau(song, maxpages=10):
	"Function connects to Dilandau.eu and returns the .mp3 links in it"
	if not utils.isAscii(song): # Dilandau doesn't like unicode.
		log.warning("[Dilandau] Song is not ASCII. Skipping...")
		return
	
	song = urllib2.quote(song.encode("utf8"))
	
	for i in range(maxpages):
		# http://en.dilandau.eu/download-mp3/call-me-maybe-1.html
		url = 'http://en.dilandau.eu/download-mp3/%s-%d.html' % (song.replace('-','').replace(' ','-').replace('--','-').lower(), i+1)
		log.debug("[Dilandau] Parsing %s... " % url)
		obj = urllib2.urlopen(url)
		response = obj.read()
		
		links = []
		soup = BeautifulSoup(response)
		
		for link in soup.find_all('a', url=re.compile(r'\.mp3$')):
			url = link['href'] + link['url'] # dont ask me why. dilandabu decided to split their url addresses.
			links.append(url)
		
		log.debug("[Dilandau] found %d links" % len(links))
		
		if not links:
			break
		
		for link in links:
			yield utils.classes.MetaUrl(link, 'dilandau')

def parse_Mp3skull(song, maxpages=1):
	"Function connects to mp3skull.com and returns the .mp3 links in it"
	if utils.isHebrew(song): # Dilandau doesn't have hebrew
		log.warning("[Mp3skull] source has no hebrew songs. Skipping...")
		return
		
	song = urllib2.quote(song.encode("utf8"))
	
	for i in range(maxpages):
		# http://mp3skull.com/mp3/how_i_met_your_mother.html
		url = 'http://mp3skull.com/mp3/%s.html' % (song.replace('-','').replace(' ','_').replace('__','_').lower())
		log.debug("[Mp3skull] Parsing %s... " % url)
		obj = urllib2.urlopen(url)
		response = obj.read()
		
		links = []
		soup = BeautifulSoup(response)
		
		for link in soup.find_all('a', href=re.compile(r'\.mp3$')):
			links.append(link['href'])
		log.debug("[Mp3skull] found %d links" % len(links))
		
		if not links:
			break
		
		for link in links:
			yield utils.classes.MetaUrl(link, 'Mp3skull')
			
def parse_soundcloud_api1(song, maxpages=1, numTries=2):
	'''
	Function connects to soundcloud.com and returns the .mp3 links in it
	
	API method 1: Looking for legitimate download links.
	'''
	song = urllib2.quote(song.encode("utf8"))
	
	# since you can't combine decorators and generators, we have to implement
	# a retry section here, instead of using the retry deco.
	if numTries <= 0:
		return
	
	for i in range(maxpages):
		# http://soundcloud.com/tracks/search?page-1&q%5Bfulltext%5D=naruto&q%5Bdownloadable%5D=true
		domain = "soundcloud.com"
		url = 'http://soundcloud.com/tracks/search?page=%d&q%%5Bfulltext%%5D=%s&q%%5Bdownloadable%%5D=true' % (i+1, song.replace('-','').replace(' ','_').replace('__','_').lower())
		log.debug("[SoundCloud] Parsing %s... " % url)
		obj = urllib2.urlopen(url)
		response = obj.read()
		soup = BeautifulSoup(response)
		
		hint = soup.find('div', class_='hint')
		if hint:
			if 'search is currently not available' in hint.text.lower():
				log.warning("soundcloud: search is currently not available!")
				time.sleep(1.5)
				parse_soundcloud_api1(song, maxpages, numTries-1)
			if "we couldn't find any tracks" in hint.text.lower():
				return
		
		links = soup.find_all('a', href=re.compile(r'/download$'))
		log.debug("[Mp3skull] found %d links" % len(links))
		for link in soup.find_all('a', href=re.compile(r'/download$')):
			url = "http://%s%s" % (domain, link['href'])
			track = link.find_parent('li').find('div', class_="info-header").h3.text
			# print track
			
			yield utils.classes.MetaUrl(url, 'SoundCloud', track)
			
def parse_soundcloud_api2(title):
	'''
	Function connects to soundcloud.com and returns the .mp3 links in it.
	
	API method 2: Parsing player's json data.
	'''
	links = search_soundcloud(title)
	
	pool = ThreadPool(max_threads=5, catch_returns=True, logger=log)
	for link in links:
		pool(get_soundcloud_dl_link)(link)
	
	return pool.iter()

@utils.decorators.memoize(config.memoize_timeout)
def search_soundcloud(title):
	"Function connects to soundcloud.com and returns the .mp3 links in it"
	title = urllib2.quote(title.encode("utf8")).replace('-','').replace(' ','_').replace('__','_').lower()

	# http://soundcloud.com/tracks/search?page=1&q%5Bfulltext%5D=naruto
	domain = "soundcloud.com"
	url = 'http://soundcloud.com/tracks/search?page=1&q%%5Bfulltext%%5D=%s' % title
	log.debug("[SoundCloud] Parsing %s... " % url)
	obj = urllib2.urlopen(url)
	response = obj.read()
	soup = BeautifulSoup(response)
	
	regex = re.compile("^/(?!(?:you|pages|premium|login|people|groups|tracks|tags)/)[^/]+/(?!.+(?:sets/|/share-options|/download))[^?]+$")
	tags = soup.find_all('a', href=regex)
	links = ["http://%s%s" % (domain, tag['href']) for tag in tags]
	return list(set(links))

@utils.decorators.memoize(config.memoize_timeout)
def get_soundcloud_dl_link(url):
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	soup = BeautifulSoup(response)
	json_tag = soup.find('script', text=re.compile('^[\r\n]*?window\.SC\.bufferTracks\.push'))
	if not json_tag:
		log.error("No soundcloud link has been found in get_soundcloud_dl_link.")
		return
	json_data = json_tag.text
	match = re.search(r"\{(.+)\}", json_data)
	if not match:
		log.error("No soundcloud link has been found in get_soundcloud_dl_link.")
		return
		
	data = json.loads(match.group())
	dl_url = "http://media.soundcloud.com/stream/%s?stream_token=%s" % (data['uid'], data['token'])
	return utils.classes.MetaUrl(dl_url, 'SoundCloud', data['title'], source_url=url)

@utils.decorators.memoize(config.memoize_timeout)
# @profile
def parse_bandcamp(title):
	links = search_bandcamp(title)
	max_result_parsing = 3
	i = 0
	
	pool = ThreadPool(max_threads=5, catch_returns=True, logger=log)
	for link in links:
		if '/album/' in link:
			pool(get_bandcamp_album_dl_links)(link)
			i += 1
			
		elif '/track/' in link:
			pool(get_bandcamp_dl_link)(link)
			i += 1
		
		if i >= max_result_parsing:
			break
			
	return pool.iter()
	
@utils.decorators.memoize(config.memoize_timeout)
# @profile
def search_bandcamp(title):
	title = urllib2.quote(title.encode("utf8")).replace('-','').replace(' ','_').replace('__','_').lower()
	
	url = "http://bandcamp.com/search?q=%s" % title
	log.debug("[Dilandau] Parsing %s... " % url)
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	links = []
	soup = BeautifulSoup(response)

	for tag in soup.find_all('a', class_='artcont'):
		links.append(tag['href'])
	log.debug("[Bandcamp] found %d links" % len(links))
		
	return links
	
@utils.decorators.memoize(config.memoize_timeout)
# @profile
def get_bandcamp_dl_link(url):
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	soup = BeautifulSoup(response)
	
	js_data = [x for x in soup.find_all('script') if x.text.strip().startswith('Control.registerController')][0].text
	json_data = [x for x in js_data.split('\n') if x.strip().startswith('trackinfo')][0].split('trackinfo', 1)[1].strip(' : ,\'')
	for song in json.loads(json_data):
		# print "%s: %s" % (song['title'], song['file'].values()[0])
		dl_link = song['file'].values()[0]
		title = song['title']
		
		return utils.classes.MetaUrl(dl_link, 'bandcamp', title, source_url=url)
	
@utils.decorators.memoize(config.memoize_timeout)
# @profile
def get_bandcamp_album_dl_links(url):
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	links = []
	soup = BeautifulSoup(response)
	
	js_data = [x for x in soup.find_all('script') if x.text.strip().startswith('Control.registerController')][0].text
	artist_name = [x for x in js_data.split('\n') if x.strip().startswith('artist')][0].split('artist', 1)[1].strip(' : ",\"')
	
	json_data = [x for x in js_data.split('\n') if x.strip().startswith('trackinfo')][0].split('trackinfo', 1)[1].strip(' : ,\'')
	for song in json.loads(json_data):
		if not song['file']:
			continue
		# print "%s: %s" % (song['title'], song['file'].values()[0])
		dl_link = song['file'].values()[0]
		title = "%s - %s" % (artist_name, song['title'])
		
		link = utils.classes.MetaUrl(dl_link, 'bandcamp', title, source_url=url)
		links.append(link)
	
	return links

def parse_Youtube(song, amount=10):
	'''
	Function searches a song in youtube.com and returns the download links for the
	videos.
	@param song: The search string.
	@param amount: Amount of clips to obtain.
	
	@return generator.
	'''
	
	videos = search_Youtube(song, amount)
	videoids = [parse_qs(urlparse(watchurl).query)['v'][0] for watchurl in videos]
	
	for videoid in videoids:
		yield get_youtube_dl_link(videoid)
		
def parse_Youtube_playlist(playlist_id):
	'''
	Function searches a playlist in youtube.com and returns the download links for the
	videos.
	@param playlist_id: The youtube playlist id.
	
	@return video_id_list.
	'''
	
	url = 'http://www.youtube.com/playlist?p=%s' % playlist_id
	obj = urllib2.urlopen(url)
	response = obj.read()
	
	videoids = []
	soup = BeautifulSoup(response)
	
	for tag in soup.find_all('a', class_='yt-uix-tile-link yt-uix-sessionlink', href=re.compile('^/watch')):
		videoids.append(parse_qs(urlparse(tag['href']).query)['v'][0])
	
	return videoids

@utils.decorators.memoize(config.memoize_timeout)
def search_Youtube(song, amount):
	'''
	Function searches a song in youtube.com and returns the video watch-urls in it
	using Youtube API.
	'''
	
	song = urllib2.quote(song.encode("utf8"))
	url = r"http://gdata.youtube.com/feeds/api/videos?q=%s&max-results=%d&v=2" % (song.replace(' ', '+'), amount)
	urlObj = urllib2.urlopen(url, timeout=4)
	data = urlObj.read()
	videos = xml.dom.minidom.parseString(data).getElementsByTagName('feed')[0].getElementsByTagName('entry')
	
	youtube_watchurls = [video.getElementsByTagName('link')[0].attributes.item(0).value for video in videos]
	return youtube_watchurls

def get_youtube_dl_link(video_id, q_priority=config.youtube_quality_priority,
										fmt_priority=config.youtube_formats_priority):
	'''
	Function returns the highest quality link for a specific youtube clip.
	@param video_id: Youtube Video ID.
	@param priority: A list represents the qualities priority.
	
	@return MetaUrlObj: MetaUrl Object.
	'''
	
	data = get_youtube_dl_links_api1(video_id)
	for q_p in q_priority:
		for fmt_p in fmt_priority:
			for stream in data['fmt_stream_map']:
				itagData = utils.classes.ItagData(stream['itag'])
				if itagData.quality == q_p and itagData.format == fmt_p:
					source_url = "http://www.youtube.com/watch?v=%s" % video_id
					return utils.classes.MetaUrl(stream['url'], 'youtube', data['title'], int(data['length_seconds']), \
							itagData, video_id, source_url, int(data['view_count']))
	log.error("No youtube link has been found in get_youtube_dl_link.")
	return

@utils.decorators.memoize(config.memoize_timeout)
@utils.decorators.retry(urllib2.HTTPError, delay=0.3, tries=3, logger=log)
def get_youtube_dl_links_api1(video_id):
	'''
	Function gets the video_ids for a videoclip
	This function parses the get_video_info format of youtube.
	
	@param video_id: Youtube Video ID.
	@return data: dictonary with args about the specific video_id.
	
	Usage example:
	title: data['title']
	length_seconds: data['length_seconds']
	videos: data['fmt_stream_map']
	specific video: data['fmt_stream_map'][0]
	specific video url: data['fmt_stream_map'][0]['url']
	specific video itag: data['fmt_stream_map'][0]['itag']
	'''
	
	d = {}
	url = r"http://www.youtube.com/get_video_info?video_id=%s&el=vevo" % video_id

	# Fetching data
	req = urllib2.Request(url, None, config.generic_http_headers)
	urlObj = urllib2.urlopen(req, timeout=8)
	_data = urlObj.read()
	data = {x.split('=', 2)[0]: urllib2.unquote(x.split('=', 2)[1]) for x in _data.split('&')}
	
	if data['status'] == 'fail':
		raise YoutubeException(data['errorcode'], data['reason'].replace('+', ' '))
	
	# Parsing youtube download links
	url_encoded_fmt_stream_map = data['url_encoded_fmt_stream_map'].split(',')
	fmt_stream_map = []
	for fmt in url_encoded_fmt_stream_map:
		d = {x.split('=', 2)[0]: urllib2.unquote(x.split('=', 2)[1]) for x in fmt.split('&')}
		
		# Inject signature code, in case it doesn't exist in the url
		if not 'signature=' in d['url']:
			d['url'] += "&signature=%s" % d['sig']
			
		fmt_stream_map.append(d)
	data['fmt_stream_map'] = fmt_stream_map
	
	# Fixing leftovers
	data['title'] = unicode(data['title'], 'utf-8').replace('+',' ').replace('--','-')
	
	return data

@utils.decorators.memoize(config.memoize_timeout)
@utils.decorators.retry(urllib2.HTTPError, delay=0.3, tries=3, logger=log)
def get_youtube_dl_links_api2(video_id):
	'''
	same as get_youtube_dl_links, but uses the watch?v=xxx API instead of get_video_info.
	'''
	
	d = {}
	url = r"http://www.youtube.com/watch?v=%s&hl=en-GB" % video_id

	# Fetching data
	req = urllib2.Request(url, None, config.generic_http_headers)
	urlObj = urllib2.urlopen(req, timeout=11)
	_data = urlObj.read()
	_playerConfig = [x for x in _data.split('\n') if 'yt.playerConfig = ' in x]
	if not _playerConfig:
		return "Error: no yt.playerConfig found."
	json_data = _playerConfig[0].split(' = ')[1].rstrip(';')
	data = json.loads(json_data)['args']
	
	# Parsing youtube download links
	url_encoded_fmt_stream_map = data['url_encoded_fmt_stream_map'].split(',')
	fmt_stream_map = []
	for fmt in url_encoded_fmt_stream_map:
		d = {x.split('=', 2)[0]: urllib2.unquote(x.split('=', 2)[1]) for x in fmt.split('&')}
		
		# Inject signature code, in case it doesn't exist in the url
		if not 'signature=' in d['url']:
			d['url'] += "&signature=%s" % d['sig']
			
		fmt_stream_map.append(d)
	data['fmt_stream_map'] = fmt_stream_map
	
	return data

def search(song, n, processes=config.search_processes, returnGen=False):
	'''
	Function searches song and returns n valid .mp3 links.
	@param song: Search string.
	@param n: Number of songs.
	@param processes: Number of processes to launch in the subprocessing pool.
	@param returnGen: If true, a generator of the links will be returned,
						and not the calculated list itself.
	'''
	sources_list = [x for x in config.search_sources_const if config.search_sources[x]]
	log.debug("Using sources: %s" % sources_list)
	
	# IMPROVE: better handeling of slicing.
	pool = ThreadPool(max_threads=min(processes, len(sources_list)), catch_returns=True, logger=log)
	args_list = []
	for source in sources_list:
		args_list.append([song, source, n/len(sources_list)])
	if n % len(sources_list):
		args_list[-1][2] += 1
	
	for args in args_list:
		pool(parse)(*args)
	
	gen = pool.iter()

	if returnGen:
		return gen
	return list(gen)
	
if __name__ == '__main__':
	import time
	t1 = time.time()
	
	o = search('naruto', 15, returnGen=True)
	for i in range(15):
		print i+1
		print repr(o.next())
		print "\n\n"
	
	t2 = time.time()
	print "took %ss" % (t2-t1)