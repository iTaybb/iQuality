# Copyright (C) 2012-2013 Itay Brandes

'''Main Gui Threads'''

'''
Some notes:
1. the FINISHED signal is emitted even if the thread got terminated. There is no way
in Qt to get a FINISHED signal and know if it was launched by a terminating thread.
Therefore, all threads here have a _terminated value. At the FINISHED signal slot,
the _terminated attribute may be checked.
'''

import os
import time
import shutil
import urllib2
import datetime
import traceback
from urlparse import parse_qs, urlparse
import re

from PyQt4 import QtCore
from PyQt4 import QtGui
from threadpool import ThreadPool

import Main
import Config; config = Config.config
from logger import log
from CustomExceptions import NoResultsException, NotSupportedFiletypeException, YoutubeException
import utils
tr = utils.qt.tr

# import pdb; QtCore.pyqtRemoveInputHook(); pdb.set_trace()

class GenericThread(QtCore.QThread):
	output = QtCore.pyqtSignal(object)
	error = QtCore.pyqtSignal(str)
	
	def __init__(self, parent=None, log_succ=True):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		self.log_succ = log_succ
		
	def init(self, func, args=""):
		self._terminated = False
		
		self.func = func
		self.args = args
		self.start()
	
	def run(self): # Called by Qt once the thread environment has been set up.
		try:
			if not self.args:
				output = self.func()
			elif isinstance(self.args, basestring):
				output = self.func(self.args)
			else:
				output = self.func(*self.args)
			self.output.emit(output)
			if self.log_succ:
				log.debug("GenericThread has completed %s successfully." % self.func.func_name)
		except Exception, e:
			self.error.emit("Exception: %s" % str(e))
			log.debug("GenericThread has completed %s with errors (%s)." % (self.func.func_name, str(e)))

	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(GenericThread, self).terminate()

class SearchThread(QtCore.QThread):
	output = QtCore.pyqtSignal(utils.classes.Song)
	finished_lucky = QtCore.pyqtSignal()
	error = QtCore.pyqtSignal(Exception)
	
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def search(self, song, numOfSongs, luckyDownload=False):
		self._terminated = False
		self.numOfSongs = numOfSongs
		self.luckyDownload = luckyDownload
		self.song = song
		self.isDirectLink = False
		self.songObj_emitted = False
		self.pool = ThreadPool(max_threads=config.buildSongObjs_processes, catch_returns=True, logger=log)
		
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once thethread environment has been set up.
		if urlparse(self.song).scheme in config.allowd_web_protocols:
			# if a url and not a search string
			self.isDirectLink = True
			self.url = self.song
			self.song = ""
			domainName = urlparse(self.url).netloc.lower()
			
			if domainName.endswith('youtube.com') or domainName.endswith('youtu.be'):
				queries = parse_qs(urlparse(self.url).query)
				if 'p' in queries or 'list' in queries:
					log.debug("Url is a direct url (Youtube playlist)")
					if 'p' in queries:
						playlist_id = queries['p'][0]
					elif 'list' in queries:
						playlist_id = queries['list'][0]
					videos_ids = Main.WebParser.LinksGrabber.parse_Youtube_playlist(playlist_id)	
					
					t_pool = ThreadPool(max_threads=config.buildSongObjs_processes, catch_returns=True, logger=log)
					for id in videos_ids:
						t_pool(Main.WebParser.LinksGrabber.get_youtube_dl_link)(id)
					links_gen = t_pool.iter()
					
				else:
					log.debug("Url is a direct url (Youtube)")
					if domainName.endswith('youtube.com'):
						video_id = queries['v'][0]
					else:
						video_id = urlparse(self.url).path.strip('/')
						
					try:
						metaUrlObj = Main.WebParser.LinksGrabber.get_youtube_dl_link(video_id)
					except YoutubeException, e:
						self.error.emit(e)
						
					links_gen = (x for x in [metaUrlObj])
			elif domainName.endswith('bandcamp.com'):
				if '/album/' in self.url:
					log.debug("Url is a direct url (bandcamp album)")
					metaUrlObjs = Main.WebParser.LinksGrabber.get_bandcamp_album_dl_links(self.url)
					links_gen = (x for x in metaUrlObjs)
				elif '/track/' in self.url:
					log.debug("Url is a direct url (bandcamp)")
					metaUrlObj = Main.WebParser.LinksGrabber.get_bandcamp_dl_link(self.url)
					links_gen = (x for x in [metaUrlObj])
				else:
					links_gen = (x for x in [])
			elif domainName.endswith('soundcloud.com'):
				log.debug("Url is a direct url (Soundcloud)")
				if self.url.startswith('https://'):
					self.url = self.url.replace('https://', 'http://')
				metaUrlObj = Main.WebParser.LinksGrabber.get_soundcloud_dl_link(self.url)	
				links_gen = (x for x in [metaUrlObj])
			else:
				ext = self.url.split('/')[-1].split('.')[-1]
				if re.match(r"^http://.*soundcloud\.com/.+/.+/download$", self.url):
					log.debug("Url is a direct url (Soundcloud).")
					metaUrlObj = utils.classes.MetaUrl(self.url, "Direct Link")
				elif ext in ['mp3', 'mp4', 'flv', 'webm']:
					log.debug("Url is a direct url (%s file)." % ext)
					metaUrlObj = utils.classes.MetaUrl(self.url, "Direct Link")
				elif ext:
					log.debug("Url is a direct url (%s - Non-multimedia file)." % ext)
					metaUrlObj = utils.classes.MetaUrl(self.url, "Direct Non-Multimedia Link")
				else:
					log.debug("Url is a direct url, no extention provided.")
					log.error("got NotSupportedFiletypeException() for the \"%s\" extention." % ext)
					self.error.emit(NotSupportedFiletypeException(ext))
					return
					
				links_gen = (x for x in [metaUrlObj])
		else:
			links_gen = Main.WebParser.LinksGrabber.search(self.song, self.numOfSongs, returnGen=True)
			
		for link in links_gen:
			self.pool(self.create_and_emit_SongObj)(link)
			
		while not self.pool.isFinished():
			time.sleep(0.1)
		
		if not self.songObj_emitted:
			log.error("Got NoResultsException.")
			self.error.emit(NoResultsException(self.isDirectLink))
		elif self.luckyDownload:
			self.finished_lucky.emit()
				
	def create_and_emit_SongObj(self, link):
		try:
			urlObj = Main.HTTPQuery.get_file_details(link)
			self.songObj = utils.classes.Song(*(urlObj+(self.song,)))
		except:
			log.exception(traceback.format_exc())
		if self.songObj.filesize == 0:
			log.error("self.songObj.bitrate is 0. skipping on %s..." % unicode(self.songObj))
		else:
			self.output.emit(self.songObj)
			
			if not self.songObj_emitted:
				self.songObj_emitted = True
		
	def terminate(self): # overload
		"Setting _terminated to True"
		self._terminated = True
		self.pool.terminate_nowait()
		super(SearchThread, self).terminate()

class DownloadThread(QtCore.QThread):
	downloadProgress = QtCore.pyqtSignal(int, float, int, int, int)
	encProgress = QtCore.pyqtSignal(int)
	status = QtCore.pyqtSignal(str)
	error = QtCore.pyqtSignal(Exception)
	
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def download(self, songObj, dl_dir):
		self._terminated = False
		self.songObj = songObj
		self.dl_dir = dl_dir
		self.isMultimediaFile = not "non-multimedia" in songObj.source.lower()
		self.isVideo = self.isMultimediaFile and self.songObj.ext != "mp3"
		self.isAudio = self.isMultimediaFile and self.songObj.ext == "mp3"
		self.encode_time = 0
		self.start()
		
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		url = self.songObj.url
		filesize = self.songObj.filesize
		
		audio_path = r"%s\%s" % (self.dl_dir, self.songObj.GetProperFilename('mp3'))
		video_path = r"%s\%s" % (self.dl_dir, self.songObj.GetProperFilename())
		dest_audio_path = r"%s\%s" % (config.temp_dir, "%s.mp3" % utils.get_rand_string())
		
		if not self.isMultimediaFile:
			dest_path = r"%s\%s" % (config.temp_dir, utils.get_rand_string())
		elif self.songObj.ext == "mp3":
			dest_path = dest_audio_path
		else: # video
			dest_path = r"%s\%s" % (config.temp_dir, "%s.vid" % utils.get_rand_string())
		
		dl_obj = Main.SmartDL(url, dest_path, logger=log)
		dl_obj.start()
		self.dl_obj = dl_obj
		
		while not dl_obj.isFinished():
			if dl_obj.status == 'combining':
				self.status.emit(tr("Combining Parts..."))
				break
				
			self.downloadProgress.emit(int(dl_obj.get_progress()*100), dl_obj.get_speed(), dl_obj.get_eta(), dl_obj.get_downloaded_size(), filesize)
			time.sleep(0.1)
		while not dl_obj.isFinished():
			# if we were breaking the last loop, we are waiting for
			# parts to get combined. we shall wait.
			time.sleep(0.1)
		if dl_obj._failed:
			log.error("Got DownloadFailedException() for %s" % url)
			self.error.emit(Main.SmartDL.DownloadFailedException())
			self.terminate()
			return
		self.downloadProgress.emit(100, dl_obj.get_speed(), dl_obj.get_eta(), filesize, filesize)
			
		if self.isVideo:
			dest_video_path = dest_path
			
			t1 = time.time()
			if config.downloadAudio: # if we want an audio file
				log.debug("Encoding Audio...")
				self.status.emit(tr("Encoding Audio..."))
				
				cmd = r'bin\ffmpeg -y -i "%s" -vn -ac 2 -b:a %d -f mp3 "%s"' % (dest_video_path,
						config.youtube_audio_bitrates[self.songObj.video_itag.quality], dest_audio_path)
				log.debug("Running '%s'" % cmd)
				est_final_filesize = self.songObj.final_filesize
				
				print "Encoding: %s (%.2f MB) to %s" % (dest_audio_path, est_final_filesize / 1024.0 / 1024.0, self.dl_dir)
				self.encProgress.emit(0)
				proc = utils.launch_without_console(cmd)
				
				old_encoded_fs_counter = 0
				while True:
					out = proc.stderr.read(54)
					if not out:
						break
					# size=    2930kB time=00:03:07.49 bitrate= 128.0kbits/s
					if 'size=' in out and 'time=' in out:
						encoded_fs_counter = out.split('size=')[1].split('kB')[0].strip()
						if encoded_fs_counter.isdigit():
							encoded_fs_counter = int(encoded_fs_counter)
							if encoded_fs_counter > old_encoded_fs_counter:
								status = r"Encoding: %.2f MB / %.2f MB %s [%3.2f%%]" % (encoded_fs_counter / 1024.0, est_final_filesize / 1024.0**2, utils.progress_bar(1.0*encoded_fs_counter*1024/est_final_filesize) , encoded_fs_counter*1024 * 100.0 / est_final_filesize)
								status = status + chr(8)*(len(status)+1)
								print status,
								self.encProgress.emit(int(encoded_fs_counter*1024 * 100.0 / est_final_filesize))
								old_encoded_fs_counter = encoded_fs_counter
					time.sleep(0.1)
				self.encProgress.emit(100)
				proc.wait()
				
				t2 = time.time()
				self.encode_time += t2-t1
				
				if not config.downloadVideo:
					log.debug("Removing %s..." % dest_path)
					os.unlink(dest_path)
				
		if config.downloadAudio and config.trimSilence:
			t1 = time.time()
			
			log.debug("Trimming Silence...")
			self.status.emit(tr("Trimming Silence from edges..."))
			
			temp_audio_trimmed_path = "%s.tmp.mp3" % dest_audio_path
			if os.path.exists(temp_audio_trimmed_path):
				os.unlink(temp_audio_trimmed_path)
			os.rename(dest_audio_path, temp_audio_trimmed_path)
			
			cmd = r'bin\sox -S "%s" "%s" silence 1 0.1 1%% reverse silence 1 0.1 1%% reverse' % (temp_audio_trimmed_path, dest_audio_path)
			log.debug("Running '%s'" % cmd)
			est_final_filesize = self.songObj.final_filesize
			
			print "Trimming Silence: %s (%.2f MB) to %s" % (dest_audio_path, est_final_filesize / 1024.0**2, self.dl_dir)
			self.encProgress.emit(0)
			proc = utils.launch_without_console(cmd)
			
			samples = 1
			in_value = 0
			out_value = 0
			while True:
				# print out
				out = proc.stderr.read(70)
				if not out:
					break
				
				# Duration       : 00:04:24.06 = 11644870 samples = 19804.2 CDDA sectors
				if 'samples =' in out:
					samples = out.split('samples')[0].split('=')[-1].strip()
					if samples.isdigit():
						samples = int(samples)
				
				# In:100%  00:04:23.96 [00:00:00.09] Out:11.6M [      |      ] Hd:0.0 Clip:400
				if 'In:' in out:
					t = out.split('In:')[1].split('.')[0].strip()
					if t.isdigit() and int(t) > in_value:
						in_value = int(t)
				
				# In:100%  00:04:23.96 [00:00:00.09] Out:11.6M [      |      ] Hd:0.0 Clip:400	
				if 'Out:' in out:
					t = out.split('Out:')[1].split(' ')[0].strip()
					try:
						if 'k' in t:
							out_value = t.split('k')[0]
							out_value = float(out_value)*1000
						elif 'M' in t:
							out_value = t.split('M')[0]
							out_value = float(out_value)*1000000
					except:
						pass
				
				progress = in_value*0.3+(out_value/samples*100)*0.7+1
				status = r"Trimming Silence: %s" % utils.progress_bar(progress/100.0)
				status = status + chr(8)*(len(status)+1)
				print status,
				self.encProgress.emit(progress)
				
				time.sleep(0.1)
				
			self.encProgress.emit(100)
			proc.wait()
			
			t2 = time.time()
			self.encode_time += t2-t1
			
			if not os.path.exists(dest_audio_path):
				log.error('SoX failed: %s' % out)
			
		log.debug("Copying Files...")
		self.status.emit(tr("Copying Files..."))
		
		if self.isVideo:
			# IMPROVE: this crashes when a video is running in media player, os.unlink removes it, but it is still running in media player.
			if config.downloadAudio:
				log.debug("Moving %s to %s" % (dest_audio_path, audio_path))
				shutil.move(dest_audio_path, audio_path) 
			if config.downloadVideo:
				log.debug("Moving %s to %s" % (dest_video_path, video_path))
				shutil.move(dest_video_path, video_path)
		if self.isAudio:
			log.debug("Moving %s to %s" % (dest_path, audio_path))
			shutil.move(dest_path, audio_path) 
		
		dl_time = dl_obj.get_dl_time()
		dl_time_s = int(dl_time)%60
		dl_time_m = int(dl_time)/60
		if filesize/dl_time/1024**2 > 1: # If dlRate is in MBs
			if dl_time_m:
				stats_str = tr('Download: %d:%.2d (%.2f MB/s)') % (dl_time_m, dl_time_s, filesize/dl_time/1024**2)
			else:
				stats_str = tr('Download: %ds (%.2f MB/s)') % (dl_time, filesize/dl_time/1024**2)
		else:
			if dl_time_m:
				stats_str = tr('Download: %d:%.2d (%.2f KB/s)') % (dl_time_m, dl_time_s, filesize/dl_time/1024)
			else:
				stats_str = tr('Download: %ds (%.2f KB/s)') % (dl_time, filesize/dl_time/1024)
		
		if self.encode_time:
			stats_str += tr('; Encoded: %ds') % self.encode_time
		self.status.emit(stats_str)
		
	def isRunning(self):
		if self._terminated:
			return False
		return super(DownloadThread, self).isRunning()
	
	def terminate(self):
		self._terminated = True
		try:
			self.dl_obj.stop()
		except:
			pass
		super(DownloadThread, self).terminate()
		
class GoogleImagesGrabberThread(QtCore.QThread):
	output = QtCore.pyqtSignal(list)
	
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def search(self, song, numOfPhotos):
		self._terminated = False

		self.song = song
		self.numOfPhotos = numOfPhotos
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		google_ans = Main.WebParser.WebServices.googleImageSearch(self.song)[:]
		pool = ThreadPool(max_threads=config.GoogleImagesGrabber_processes, catch_returns=True, logger=log)
		
		fn_list = []
		while len(fn_list) < self.numOfPhotos and google_ans:
			urls = []
			for i in range(self.numOfPhotos-len(fn_list)):
				if google_ans:
					urls.append(google_ans.pop(0))

			for url in urls:
				pool(self.fetchPhoto)(url)
				
			for photo in pool.iter():
				try:
					if photo:
						fn_list.append(photo)
				except Exception, e:
					log.warning("Exception %s ignored in GoogleImagesGrabberThread." % str(e))
		
		self.output.emit(fn_list)
	
	def fetchPhoto(self, url):
		req = urllib2.Request(url, headers=config.generic_http_headers)
		try:
			urlObj = urllib2.urlopen(req, timeout=config.GoogleImagesGrabber_timeout)
			meta = urlObj.info()
			filesize = int(meta.getheaders("Content-Length")[0])
			if filesize > config.GoogleImagesGrabber_maxsize:
				return ""
		except urllib2.URLError, IndexError:
			return ""
		with open(utils.get_rand_filename(config.temp_dir), 'wb') as f:
			f.write(urlObj.read())
			x = f.name
		urlObj.close()
		return x

	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(GoogleImagesGrabberThread, self).terminate()

class LyricsGrabberThread(QtCore.QThread):
	MainResult = QtCore.pyqtSignal(utils.classes.LyricsData)
	MinorResult = QtCore.pyqtSignal(utils.classes.LyricsData)
	eof = QtCore.pyqtSignal()
	error = QtCore.pyqtSignal(str)
	
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def search(self, title, artist):
		self._terminated = False
		self.IsNextLyrics = False
		self.title = title
		self.artist = artist
		
		if hasattr(self, "gen"):
			del self.gen
		
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		if not hasattr(self, "gen"):
			self.gen = Main.WebParser.LyricsGrabber.parse(self.title, self.artist)
		
		# We'll be doing two passes: We'll fetch the current lyrics, and the next lyrics in line.
		# The first will be called "main" and the second "minor".
		# 'main' will be shown on the screen.
		# 'minor' will be loaded and be accessed by the ">>" button.
		if not self.IsNextLyrics:
			self._nextLyrics(minor=False)
		self._nextLyrics(minor=True)
	
	def nextLyrics(self):
		self.IsNextLyrics = True
		self.start()
	
	def _nextLyrics(self, minor=False):
		"Returns the next lyrics"
		if not self.isRunning:
			return
		try:
			lyrics = self.gen.next()
		except StopIteration:
			lyrics = None
		if minor:
			if lyrics:
				self.MinorResult.emit(lyrics)
			else:
				self.eof.emit()
		else:
			if lyrics:
				self.MainResult.emit(lyrics)
			else:
				self.error.emit(tr("No lyrics were found."))
				
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(LyricsGrabberThread, self).terminate()

class MusicBrainzFetchThread(QtCore.QThread):
	output = QtCore.pyqtSignal(str, str, str, str)
	error = QtCore.pyqtSignal(str)
	
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def fetch(self, title, artist):
		self._terminated = False

		self.title = title
		self.artist = artist
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		d = Main.WebParser.MetadataGrabber.parse_musicBrainz(self.title, self.artist)
		if not d:
			self.error.emit(tr("No tags were found."))
			return
			
		title_list = [d[x]['title'] for x in d.keys()]
		title_list = [x for x in title_list if x]
		if title_list:
			album = sorted(title_list, key=title_list.count, reverse=True)[0]
		else:
			album = ""
		
		date_list = [d[x]['date'] for x in d.keys()]
		date_list = [x for x in date_list if x]
		date_list = list(set(date_list))
		if date_list:
			dateDict = {}
			for dateStr in date_list:
				args = map(int, dateStr.split('-'))
				if len(args) < 3:
					for i in range(3-len(args)):
						args.append(1)
				obj = datetime.date(*args)
				dateDict[dateStr] = obj
				
			date = [x for x in dateDict.keys() if dateDict[x] == sorted(dateDict.values())[0]][0]
			# date = date.split('-', 1)[0]
		else:
			date = ""
		
		tag = d[d.keys()[0]]['tag'] if 'tag' in d[d.keys()[0]].keys() else ""
		artist = d[d.keys()[0]]['artist'] if 'artist' in d[d.keys()[0]].keys() else ""
		
		self.output.emit(album, date, tag, artist)
		
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(MusicBrainzFetchThread, self).terminate()
		
class ArtistSearchThread(QtCore.QThread):
	output = QtCore.pyqtSignal(list)
	error = QtCore.pyqtSignal(str)
	
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def search(self, artist):
		self._terminated = False

		self.artist = artist
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		if utils.isHebrew(self.artist):
			f = Main.WebParser.MetadataGrabber.shironet_artist_search
		else:
			f = Main.WebParser.MetadataGrabber.musicbrainz_artist_search
			
		artists = f(self.artist)

		if not artists:
			self.error.emit(tr("No data was found."))
			return
			
		self.output.emit(artists)
	
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(ArtistSearchThread, self).terminate()
		
class ArtistLookupThread(QtCore.QThread):
	output = QtCore.pyqtSignal(list, list, list, QtGui.QTreeWidgetItem)
	error = QtCore.pyqtSignal(str, QtGui.QTreeWidgetItem)
	
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def search(self, artistObj, widgetItem=None):
		self._terminated = False
		
		self.artistObj = artistObj
		self.widgetItem = widgetItem if widgetItem else QtGui.QTreeWidgetItem()
		self.arid = artistObj.id
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		if self.artistObj.source == 'shironet':
			if self.artistObj.has_albums:
				albums = Main.WebParser.MetadataGrabber.shironet_artist_albums(self.arid)
				singles = []
				others = []
			else:
				albums = []
				singles = Main.WebParser.MetadataGrabber.shironet_artist_songs(self.arid)
				others = []
		else:
			albums, singles, others = Main.WebParser.MetadataGrabber.musicbrainz_release_search(self.arid)
			
		if not any([albums, singles, others]):
			self.error.emit(tr("No data was found."), self.widgetItem)
			return
			
		self.output.emit(albums, singles, others, self.widgetItem)
	
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(ArtistLookupThread, self).terminate()
		
class AlbumLookupThread(QtCore.QThread):
	output = QtCore.pyqtSignal(list, QtGui.QTreeWidgetItem)
	error = QtCore.pyqtSignal(str)
	
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def search(self, releaseObj, widgetItem):
		self._terminated = False
		
		self.reid = releaseObj.id
		self.arid = releaseObj.arid # may not be implemented by musicbrainz
		self.source = releaseObj.source
		self.widgetItem = widgetItem
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		if self.source == 'shironet':
			tracks = Main.WebParser.MetadataGrabber.shironet_album_songs(self.arid, self.reid)
		else:
			tracks = Main.WebParser.MetadataGrabber.musicbrainz_recording_search(self.reid)
			
		if not tracks:
			self.error.emit(tr("No data was found."))
			return
			
		self.output.emit(tracks, self.widgetItem)
	
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(AlbumLookupThread, self).terminate()
		
class ChartsLookupThread(QtCore.QThread):
	output = QtCore.pyqtSignal(list, QtGui.QTreeWidgetItem)
	error = QtCore.pyqtSignal(str)
	
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def lookup(self, func, widgetItem):
		self._terminated = False
		
		self.f = func
		self.widgetItem = widgetItem
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		tracks = self.f()
			
		if not tracks:
			self.error.emit(tr("No data was found."))
			return
			
		self.output.emit(tracks, self.widgetItem)
	
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(ChartsLookupThread, self).terminate()
		
class LyricsFulltextSearchThread(QtCore.QThread):
	output = QtCore.pyqtSignal(basestring)
	
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def search(self, lyric):
		self._terminated = False
		
		self.lyric = lyric
		self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		if utils.isHebrew(self.lyric):
			track = Main.WebParser.MetadataGrabber.parse_shironet_songs_by_lyrics(self.lyric)
		else:
			track = Main.WebParser.MetadataGrabber.parse_songlyrics_songs_by_lyrics(self.lyric)
			if not track:
				track = Main.WebParser.MetadataGrabber.parse_animelyrics_songs_by_lyrics(self.lyric)
			
		self.output.emit(track)
	
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(LyricsFulltextSearchThread, self).terminate()
		
if __name__ == '__main__':
	import time
	t1 = time.time()
	
	def f(): print x
	
	t = SearchThread()
	t.output.connect(f)
	t.search('naruto', 15, False)
	
	while t.isRunning():
		time.sleep(0.1)
	
	t2 = time.time()
	print "took %ss" % (t2-t1)