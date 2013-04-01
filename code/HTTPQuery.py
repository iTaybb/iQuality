# Copyright (C) 2012-2013 Itay Brandes

'''
This module contain functions that fetches data over HTTP.
'''

import urllib2
from cStringIO import StringIO

import mutagen.id3
from mutagen.id3 import TIT2, TPE1
import mutagen.mp3
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

import Config; config = Config.config
from logger import log
import utils

def get_file_details(urlObj):
	'''
	Function fetches information about media files.
	The output may be used as init parameters for a Main.Song object.
	
	@param urlObj: A metaUrl Object.
	@return url, filesize, SupportsHTTPRange, bitrate, title, artist, source, quality, youtube_videoid
	'''
	if urlObj.source.lower() == "youtube":
		SupportsHTTPRange = True
		
		title, artist = utils.parse_title_from_filename(urlObj.videoName)
		
		ID3TagsToEdit = {}
		ID3TagsToEdit['TIT2'] = TIT2(encoding=3, text=title)
		ID3TagsToEdit['TPE1'] = TPE1(encoding=3, text=artist)
		dummyMP3 = utils.makeDummyMP3(config.temp_dir)
		utils.setID3Tags(ID3TagsToEdit, dummyMP3)
			
		ID3Info = [config.youtube_audio_bitrates[urlObj.itag.quality], title, artist, dummyMP3]
	elif urlObj.source.lower() == "soundcloud":
		SupportsHTTPRange = True
		
		ID3Info = get_id3info(urlObj.url)
		if not ID3Info[1] and not ID3Info[2]: # if there is no title and artist data in ID3
			title, artist = utils.parse_title_from_filename(urlObj.videoName)
			
			ID3TagsToEdit = {}
			ID3TagsToEdit['TIT2'] = TIT2(encoding=3, text=title)
			ID3TagsToEdit['TPE1'] = TPE1(encoding=3, text=artist)
			dummyMP3 = utils.makeDummyMP3(config.temp_dir)
			utils.setID3Tags(ID3TagsToEdit, dummyMP3)
			ID3Info = [ID3Info[0], title, artist, dummyMP3]
	else:
		SupportsHTTPRange = is_ServerSupportHTTPRange(urlObj.url)
		ID3Info = get_id3info(urlObj.url)
		
	filesize = get_filesize(urlObj.url)
	bitrate, title, artist, ID3File = ID3Info
	
	# if file didn't have id3 tags, or if the 'title' and 'artist' values were empty
	if not ID3File or (not title and not artist):
		fn = ".".join(urlObj.url.split('/')[-1].split('.')[:-1])
		title, artist = utils.parse_title_from_filename(fn)
	
		ID3TagsToEdit = {}
		ID3TagsToEdit['TIT2'] = TIT2(encoding=3, text=title)
		ID3TagsToEdit['TPE1'] = TPE1(encoding=3, text=artist)
		ID3File = utils.makeDummyMP3(config.temp_dir)
		utils.setID3Tags(ID3TagsToEdit, ID3File)
		
	return urlObj.url, filesize, SupportsHTTPRange, bitrate, title, artist, ID3File, \
			urlObj.source, urlObj.length_seconds, urlObj.itag, urlObj.youtube_videoid, \
			urlObj.view_count

@utils.decorators.memoize(config.memoize_timeout)
def get_id3info(url):
	'''
	Function fetches data about mp3 files over HTTP.
	@param url: mp3 file address.
	
	@return bitrate, title, artist, id3tags_file
	'''
	
	if not is_ServerSupportHTTPRange(url):
		log.warning("Server does not support HTTPRANGE! [%s]" % url)
		return [0, "", "", ""]
	
	url = url.replace(' ', '%20') # may not be needed	
	req = urllib2.Request(url, headers=config.generic_http_headers)
	urlObj = urllib2.urlopen(req, timeout=config.get_id3info_timeout)
	tmpfile = utils.get_rand_filename(config.temp_dir)
	
	stringIO = StringIO()
	while True:
		stringIO.write(urlObj.read(8192))
		with open(tmpfile, 'wb') as f:
			f.write(stringIO.getvalue())
		try:
			audio = MP3(tmpfile)
			break
		except EOFError: # We still didn't fetch all the ID3 data.
			pass
			# log.debug("metadata is not in this %d KB chunk or not supported." % len(stringIO.getvalue()))
		except mutagen.mp3.HeaderNotFoundError:
			log.debug("HeaderNotFoundError: can't sync to an MPEG frame")
			stringIO.close()
			return [0, "", "", ""]
	stringIO.close()
	
	try:
		audioID3 = EasyID3(tmpfile)
	except mutagen.id3.ID3NoHeaderError:
		log.debug("no ID3data found (mutagen.id3.ID3NoHeaderError).")
		return [audio.info.bitrate, "", "", ""]
	except mutagen.id3.ID3BadUnsynchData:
		log.debug("Bad ID3 Unsynch Data (mutagen.id3.ID3BadUnsynchData)")
		return [audio.info.bitrate, "", "", ""]
		
	title = utils.fix_faulty_unicode(audioID3.get('title')[0]) if audioID3.get('title') else ""
	artist = utils.fix_faulty_unicode(audioID3.get('artist')[0]) if audioID3.get('artist') else ""
		
	return [audio.info.bitrate, title, artist, tmpfile]

@utils.decorators.memoize(config.memoize_timeout)
def is_ServerSupportHTTPRange(url, timeout=config.is_ServerSupportHTTPRange_timeout):
	'''
	Function checks if a server allows HTTP Range.
	@param url: url address.
	@param timeout: Timeout in seconds.
	
	@return bool: Does server support HTTPRange?
	
	May raise urllib2.HTTPError, urllib2.URLError.
	'''
	url = url.replace(' ', '%20')
	
	fullsize = get_filesize(url)
	if not fullsize:
		return False
	
	headers = {'Range': 'bytes=0-3'}
	req = urllib2.Request(url, headers=headers)
	urlObj = urllib2.urlopen(req, timeout=timeout)
		
	meta = urlObj.info()
	filesize = int(meta.getheaders("Content-Length")[0])
	
	urlObj.close()
	return (filesize != fullsize)

@utils.decorators.memoize(config.memoize_timeout)
def get_filesize(url, timeout=config.get_filesize_timeout):
	'''
	Function fetches filesize of a file over HTTP.
	@param url: url address.
	@param timeout: Timeout in seconds.
	
	@return bool: Size in bytes.
	'''
	if isinstance(url, utils.classes.MetaUrl):
		url = url.url
		
	url = url.replace(' ', '%20')
	try:
		u = urllib2.urlopen(url, timeout=timeout)
	except (urllib2.HTTPError, urllib2.URLError) as e:
		log.error(e)
		return 0
	meta = u.info()
	try:
		file_size = int(meta.getheaders("Content-Length")[0])
	except IndexError:
		return 0
		
	return file_size