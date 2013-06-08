# coding: utf-8
# Copyright (C) 2012-2013 Itay Brandes

'''
Project-wide classes go here
'''

import os.path
from difflib import SequenceMatcher
import urllib
import urlparse

# sys.path.append('..') # for project top-level modules
from logger import log2 as log
import core

class ItagData(object):
	'''
	An itag structure data.
	'itag' is the parameter used by YouTube to differentiate between quality profiles.
	
	Data members are itag, format, quality, bitrate.
	Updates up to 26/07/12.
	'''
	def __init__(self, itag):
		self.itag = int(itag)
		self.res = self.getResolution() # res is for the video resolution (480p, 720p, etc)
		self.format = self.getFormat()
		self.quality = self.getQuality() # must be called somewhere AFTER self.res is initialized
	
	def __int__(self):
		return self.itag
		
	def __repr__(self):
		return "<ItagData %s (%sp) | %s @ %s>" % (self.itag, self.res, self.format, self.quality)
		
	def getFormat(self):
		if self.itag in [5, 6, 34, 35]:
			return 'flv'
		if self.itag in [13, 17, 36]:
			return '3gp'
		if self.itag in [18, 22, 37, 38, 82, 83, 84, 85]:
			return 'mp4'
		if self.itag in [43, 44, 45, 46, 100, 101, 102]:
			return 'webm'
		return 'unknown'
	
	def getQuality(self):
		if self.res < 240:
			return 'x-small'
		if self.res < 360:
			return 'small'
		if self.res < 480:
			return 'medium'
		if self.res < 520:
			return 'large'
		if self.res <= 720:
			return 'hd720'
		if self.res <= 1080:
			return 'hd1080'
		if self.res <= 3072:
			return 'hd3072'
		return 'unknown'
	
	def getResolution(self):
		if self.itag in [13]:
			return 0
		if self.itag in [45, 22, 84, 102]:
			return 720
		if self.itag in [85]:
			return 85
		if self.itag in [44, 35]:
			return 480
		if self.itag in [82, 18, 34, 101, 43, 100]:
			return 360
		if self.itag in [38]:
			return 3072
		if self.itag in [6]:
			return 270
		if self.itag in [83, 36, 5]:
			return 240
		if self.itag in [17]:
			return 144
		if self.itag in [46, 37]:
			return 1080
		return 'unknown'

class MetaUrl(object):
	"a url structure data with extra metadata"
	def __init__(self, url, source="", trackName="", length_seconds=0, itag="", youtube_videoid="", source_url="", view_count=0):
		self.url = str(url) if core.isAscii(url) else core.url_fix(url)
		self.source = source
		self.title = trackName # Youtube&SoundCloud&Bandcamp Links Only
		self.length_seconds = length_seconds # Youtube Links Only
		self.itag = itag # Youtube Links Onlys
		self.youtube_videoid = youtube_videoid # Youtube Links Onlys
		self.source_url = source_url
		self.view_count = view_count # Youtube Links Onlys
	
	def __repr__(self):
		return "<MetaUrl '%s' | %s>" % (self.url, self.source)
		
	def __str__(self):
		return self.url

class LyricsData(object):
	'''
	A lyrics data struct. Will show only the lyrics on __str__.
	Also have metadata of the artist and the song name.
	'''
	def __init__(self, lyrics, artist="", title=""):
		self.lyrics = lyrics
		self.artist = artist
		self.title = title
		
	def __str__(self):
		return self.lyrics
		
	def __repr__(self):
		return "<LyricsData '%s' | %s | %s>" % (self.lyrics, self.artist, self.title)
		
class MetadataArtist(object):
	"An artist metadata struct."
	def __init__(self, id_, name, source, type_="", score=0, has_albums=True, disambiguation=""):
		self.id = id_
		self.name = name
		self.source = source
		self.type = type_
		self.score = score
		self.has_albums = has_albums
		self.disambiguation = disambiguation
		
	def __str__(self):
		return self.name
		
	def __repr__(self):
		return "<MetadataArtist '%s' (id: %s @ %s)>" % (self.name.encode('ascii', 'ignore'), self.id, self.source)
		
class MetadataRelease(object):
	"An artist metadata struct."
	def __init__(self, id_, title, source, type_="", date="", count=0, arid="", artist_name=""):
		self.id = id_
		self.title = title
		self.source = source
		self.type = type_
		self.date = date
		self.count = count
		self.arid = arid
		self.artist_name = artist_name
		
	def __str__(self):
		return self.title
		
	def __repr__(self):
		return "<MetadataRelease '%s' (id: %s @ %s)>" % (self.title.encode('ascii', 'ignore'), self.id, self.source)
		
class Song(object):
	"A class defining a song."
	def __init__(self, url, filesize, SupportsHTTPRange, bitrate=-1, title="",
					artist="", id3tags_file="", source="", length_seconds="", video_itag="",
					youtube_videoid="", source_url="", youtube_views_count=0, searchString="", constantFileName=None):
		self.url = url
		self.filename = url.split('/')[-1].split('?')[0]
		self.filesize = filesize
		self.SupportsHTTPRange = SupportsHTTPRange
		self.bitrate = bitrate
		self.title = title.strip()
		self.artist = artist.strip()
		self.id3tags_file = id3tags_file # empty mp3 file with an id3 header
		self.source = source.lower()
		self.length_seconds = length_seconds # youtube only
		self.video_itag = video_itag # youtube only
		self.source_url = source_url
		self.youtube_videoid = youtube_videoid # youtube only
		self.youtube_views_count = youtube_views_count # youtube only
		self.searchString = searchString.lower()
		self.constantFileName = constantFileName # If set, this will be the name of the file.

		# self.ext saves the video format. if not a video, saved as a .mp3 file.
		if self.source == "youtube":
			self.ext = self.video_itag.format
		elif 'non-multimedia' in self.source:
			self.ext = ""
			self.constantFileName = self.filename
		else:
			self.ext = "mp3"
			
		# Handles url's unicode.
		s = self.url
		try:
			s.decode('ascii')
		except (UnicodeEncodeError, UnicodeDecodeError):
			if isinstance(s, unicode):
				s = s.encode('utf-8', 'ignore')
			scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
			path = urllib.quote(path, '/%')
			qs = urllib.quote_plus(qs, ':&=')
			s = urlparse.urlunsplit((scheme, netloc, path, qs, anchor))
		self.url = s

		self.mediaLength = self.calcLength()
		self.score = self.calcScore() if self.searchString else 5.00
		self.final_filesize = self.calcFinalFilesize()
		
	def __repr__(self):
		return "<Song '%.60s'>" % self.url
	
	def GetProperFilename(self, ext=None):
		if not ext:
			ext = self.ext
		if self.constantFileName:
			t_ext = self.constantFileName.split('.')[-1]
			if t_ext in ['mp3', 'mp4', 'webm', 'flv']: # if the ext is a known extension
				fn = "%s.%s" % (".".join(self.constantFileName.split('.')[:-1]).strip(), ext)
			elif not ext:
				fn = self.constantFileName
			else:
				fn = "%s.%s" % (self.constantFileName.strip(), ext)
				
		elif self.artist and self.title:
			fn = "%s - %s.%s" % (self.artist.strip(), self.title.strip(), ext)
		elif self.title:
			fn = "%s.%s" % (self.title.strip(), ext)
		else:
			fn = self.filename
		
		chars_to_delete = r'*:<>?\/|"'
		for c in chars_to_delete:
			fn = fn.replace(c, '')
		
		fn = os.path.normpath(fn)
		return fn
		
	def calcFinalFilesize(self):
		if self.source == "youtube":
			return self.bitrate/8.0 * self.mediaLength
		return self.filesize
		
	def calcLength(self):
		"Calculates the media stream length in seconds."
		# formula: filesize-of-stream-in-bytes/1024 / (bitrate-in-bits-per-second/1024/8)
		# the stream is the audio file WITHOUT the id3 headers (found at self.id3tags_file)
		# The length has some error rate, as we can see in the following chart:
		#	 bitrate	est		atcual	error
		#	 48			21:30	18:21	17.1%
		#	 64			2:06	1:53	11.5%
		#	 96			2:49	2:39	6.3%
		#	 128		1:32	1:28	4.5%
		#	 128		3:45	3:36	4.1%
		#	 128		4:35	4:24	4.1%
		#	 160		4:07	4:00	2.9%
		#	 192		4:07	4:02	2.0%
		#	 224		3:22	3:20	1.1%
		#	 256		4:58	4:55	1.0%
		#	 320		7:24	7:23	0.1%
			
		if self.source == "youtube":
			sec = self.length_seconds
		elif self.filesize and self.bitrate > 8000:
			sec = ((self.filesize-os.path.getsize(self.id3tags_file))/1024) / (self.bitrate/1024/8)
			
			if self.bitrate <= 48000:
				fix = 0.171
			elif self.bitrate <= 64000:
				fix = 0.115
			elif self.bitrate <= 96000:
				fix = 0.063
			elif self.bitrate <= 128000:
				fix = 0.042
			elif self.bitrate <= 160000:
				fix = 0.029
			elif self.bitrate <= 192000:
				fix = 0.020
			elif self.bitrate <= 256000:
				fix = 0.010
			elif self.bitrate <= 320000:
				fix = 0.000
			else:
				# more than 320kbps! the fuck?
				fix = 0
			
			sec *= 1-fix 
		else:
			sec = 0
		return sec
	
	def calcScore(self):
		"Calculates a score for the song. Score is a float number between 0 and 5."
		score = 0.0
		given_score_for_artist_match = False
		searchString_title, searchString_artist = core.parse_title_from_filename(self.searchString)
				
		log.debug("self.url: %s" % self.url)
		log.debug("self.searchString: %s" % self.searchString)
		log.debug("self.artist: %s" % self.artist)
		log.debug("self.title: %s" % self.title)
		
		# If it's a radio edit, +0.5
		good_words = ['radio edit']
		for word in good_words:
			if word in self.searchString:
				log.debug('a good word (%s) is in search string: +0.5' % word)
				score += 0.5
		
		# If we weren't searching for 'dj', 'mix', 'live' and the song do include these strings: -1.5
		forbidden_words_in_artist = ['dj', 'rmx', 'instrumental', 'piano', 'live', 'cover', 'karaoke', 'acapella', 'playback', 'parody', 'acoustic', u'קאבר', u'לייב', u'הופעה', u'רמיקס', u'קריוקי', u'פליבק', u'פלייבק', u'מעריצים', u'זאפה', u'מופע', u'פסנתר', u'פרודיה', u'פארודיה', u'אקוסטי']
		forbidden_words_in_title = ['mix', 'rmx', 'instrumental', 'piano', 'live', 'cover', 'karaoke', 'acapella', 'playback', 'parody', 'acoustic', u'קאבר', u'לייב', u'הופעה', u'רמיקס', u'קריוקי', u'פליבק', u'פלייבק', u'מעריצים', u'זאפה', u'מופע', u'פסנתר', u'פרודיה', u'פארודיה', u'אקוסטי']
				
		if self.artist:
			for word in forbidden_words_in_artist:
				if word in self.artist.lower() and not word in self.searchString:
					log.debug('%s is in artist, not in search string: -1' % word)
					score -= 1.5
					break		
		if self.title:
			for word in forbidden_words_in_title:
				if word in self.title.lower() and not word in self.searchString:
					log.debug('%s is in title, not in search string: -1' % word)
					score -= 1.5
					break
		
		# If the title OR the artist contains the whole search string: +1.5
		# Else, If the title's AND the artist's match ratio is over 80%: +1.0
		#		If it is over 95%: +1.5
		# If the title's length is over 60: -0.5
		# If it is over 100: -1.5
		if self.title:
			given_score_for_artist_match = True
			if self.searchString.count('-') > 0:
				x = self.searchString.split('-', 1)
				inverted_searchString = "%s - %s" % (x[1].strip(), x[0].strip())
			
			if (self.searchString in self.title.lower() or self.searchString in self.artist.lower()) or \
				(searchString_title.lower() in self.title.lower() and searchString_artist.lower() in self.artist.lower()):
				log.debug('the whole search string is in title or artist: +1.5')
				score += 1.5
			
			elif self.searchString.count('-') > 0 and (inverted_searchString in self.title.lower() or inverted_searchString in self.artist.lower()):
				log.debug('the whole inverted search string is in title or artist: +1.5')
				score += 1.5
				
			elif searchString_title.lower() in self.artist.lower() and searchString_artist.lower() in self.title.lower():
				log.debug('the whole inverted search string is in title or artist: +1.5')
				score += 1.5
			
			else:
				s1 = self.searchString.replace('-','').replace('  ',' ').lower()
				s2 = ("%s %s" % (self.title, self.artist)).lower()
				s3 = ("%s %s" % (self.artist, self.title)).lower()
				diff1 = SequenceMatcher(lambda x: x == " ", s1, s2).ratio()
				# print "difference between '%s' and '%s' is %f" % (s1, s2, diff1)
				diff2 = SequenceMatcher(lambda x: x == " ", s1, s3).ratio()
				# print "difference between '%s' and '%s' is %f" % (s1, s3, diff2)
			
				if max(diff1, diff2) >= 0.8:
					log.debug('match ratio of title+artist and search string (%d%%) is over 80%%: +1' % (int(max(diff1, diff2))*100))
					score += 1.0
				elif max(diff1, diff2) >= 0.95:
					log.debug('match ratio of title+artist and search string (%d%%) is over 95%%: +1.5' % (int(max(diff1, diff2))*100))
					score += 1.5
				else:
					log.debug('match ratio of title+artist and search string (%d%%) is below 80%%: +0' % (int(max(diff1, diff2))*100))
					given_score_for_artist_match = False
			
			## title's length ##
			if len(self.title) > 60:
				log.debug('title\'s length is over 60 chars: -0.5')
				score -= 0.5
			if len(self.title) > 100:
				log.debug('title\'s length is over 100 chars: -1.0')
				score -= 1.0
		
		# If it is youtube, and views are over 50,000: +0.5
		# Else, if the views counter are less then 2,500, but more than 1000: -0.5
		# Else, -1.0
		if self.source == "youtube":
			if self.youtube_views_count > 50000:
				log.debug('Views counter (%s) is over 50,000: +0.5' % "{:,}".format(self.youtube_views_count))
				score += 0.5
			elif 100 <= self.youtube_views_count < 2500:
				log.debug('Views counter (%s) is between 2,500 and 750: -0.5' % "{:,}".format(self.youtube_views_count))
				score -= 0.5
			elif self.youtube_views_count < 1000:
				log.debug('Views counter (%s) is below 1000: -1.0' % "{:,}".format(self.youtube_views_count))
				score -= 1.0
				
		if self.artist and not given_score_for_artist_match:
			artists1 = core.parse_artists_from_artist(searchString_artist.lower())
			artists2 = core.parse_artists_from_artist(self.artist.lower())
			artists3 = core.parse_artists_from_artist(searchString_title.lower())
			artists4 = core.parse_artists_from_artist(self.title.lower())
			if len(artists1+artists2+artists3+artists4) >= 6: # at least two are double
				s1 = " ".join(artists1)
				s2 = " ".join(artists2)
				s3 = " ".join(artists3)
				s4 = " ".join(artists4)
				diff1 = SequenceMatcher(lambda x: x == " ", s1, s2).ratio()
				diff2 = SequenceMatcher(lambda x: x == " ", s3, s4).ratio()
				max_diff = max(diff1, diff2)
				
				if max_diff >= 0.8:
					log.debug('match ratio of artists (parsed) (%d%%) is over 80%%: +1' % (int(max_diff)*100))
					score += 1.0
				# elif max_diff >= 0.95:
					# log.debug('match ratio of artists (parsed) (%d%%) is over 95%%: +1.5' % (int(max_diff)*100))
					# score += 1.5
				else:
					log.debug('match ratio of artists (parsed) (%d%%) is below 80%%: +0' % (int(max_diff)*100))
					
		# If the artist is unknown: -0.5
		if not self.artist:
			log.debug("the artist's unknown: -0.5")
			score -= 0.5
			
		# If the bitrate score calculation is as follows:
		# 64kbps or less --> -1.0
		# 96kbps --> +0.0
		# 128kbps --> +0.5
		# 192kbps --> +1.0
		# 256kbps --> +1.5
		if self.bitrate:
			if self.bitrate <= 64000:
				log.debug("bitrate is <= 64000: -1")
				score -= 1
			elif self.bitrate <= 96000:
				log.debug("bitrate is <= 96000: +0")
				pass
			elif self.bitrate <= 128000:
				log.debug("bitrate is <= 128000: +0.5")
				score += 0.5
			elif self.bitrate <= 192000:
				log.debug("bitrate is <= 192000: +1")
				score += 1
			elif self.bitrate <= 256000:
				log.debug("bitrate is <= 256000: +1.5")
				score += 1.5
			else:
				log.debug("bitrate is > 256000: +1.5")
				score += 1.5
		
		# if filesize is less than 2MB or more than 700MB: -2.0
		if self.filesize < 2*1024**2 or self.filesize > 700*1024**2:
			log.debug("filesize (%.2fMB) is not between 2 and 700: -2" % (self.filesize/1024.0**2))
			score -= 2
		
		# if server supports HTTPRange: +1.0
		if self.SupportsHTTPRange:
			log.debug("server supports HTTPRange: +1.0")
			score += 1.0
		else:
			log.debug("server does not support HTTPRange: +0")
		
		# If source is Youtube&SouncCloud, we should look if we're looking for an Hebrew song.
		# If True, +0.5, as Youtube&SouncCloud is the sole sources for Hebrew songs.
		# Else, because other sources are prefered over Youtube&SouncCloud:
		# 	Youtube: -1.0
		#	SouncCloud: -1.5
		if self.source in ["youtube", 'soundcloud']:
			# if search string is in hebrew
			if any(u"\u0590" <= c <= u"\u05EA" for c in self.searchString):
				log.debug("%s, and search string is in hebrew: +0.5" % self.source)
				score += 0.5
			elif self.source == 'soundcloud':
				log.debug("%s, but search string is not in hebrew: -1.5" % self.source)
				score -= 1.5
			else:
				log.debug("%s, but search string is not in hebrew: -1.0" % self.source)
				score -= 1.0
		
		# if media length is valid, but less than one minute, -1.5
		# if media length is over 20 mins, -0.5
		if 0 < self.mediaLength < 60:
			log.debug("media length (%ds) is between 0 and 60: -1.5" % self.mediaLength)
			score -= 1.5
		if self.mediaLength > 20*60:
			log.debug("media length (%ds) is longer than 20min: -0.5" % self.mediaLength)
			score -= 0.5
		
		# score has to be in range of 0.0 and 5.0
		log.debug('score is %.2f\n====================================================' % score)
		if score > 5:
			score = 5.0
		if score < 0:
			score = 0.0
			
		return float("%.2f" % score)