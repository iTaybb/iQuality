# Copyright (C) 2012-2014 Itay Brandes

'''Main Gui Threads

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

from PyQt4 import QtCore
from PyQt4 import QtGui
from threadpool import ThreadPool
from pySmartDL import SmartDL

import Main
import Config; config = Config.config
from logger import log
from CustomExceptions import NoResultsException, YoutubeException
import utils
import Wrappers
tr = utils.qt.tr

# import pdb; QtCore.pyqtRemoveInputHook(); pdb.set_trace()

class GenericThread(QtCore.QThread):
	output = QtCore.pyqtSignal(object)
	error = QtCore.pyqtSignal(object)
	
	def __init__(self, parent=None, log_succ=True, relaunch=0):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		self.log_succ = log_succ
		self.relaunch = relaunch
		
	def init(self, func, args=""):
		self._terminated = False
		
		self.func = func
		self.args = args
		self.start()
	
	def run(self):
		self._real_run()
		while self.relaunch:
			time.sleep(self.relaunch)
			self._real_run()
	
	def _real_run(self):
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
			self.error.emit("Exception: %s" % unicode(e))
			log.error("GenericThread has completed %s with errors (%s)." % (self.func.func_name, unicode(e)))

	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(GenericThread, self).terminate()
		
class SpellCheckThread(QtCore.QThread):
	output = QtCore.pyqtSignal(object, object, bool)
	error = QtCore.pyqtSignal(object)
	
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
	def init(self, s, luckyMode):
		self._terminated = False
		
		self.s = s
		self.luckyMode = luckyMode
		self.start()
	
	def run(self): # Called by Qt once the thread environment has been set up.
		try:
			ans = Main.WebParser.WebServices.spell_fix(self.s)
			if ans != self.s:
				self.output.emit(ans, self.s, self.luckyMode)
		except Exception, e:
			self.error.emit("Exception (SpellCheckThread): %s" % unicode(e))

	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(SpellCheckThread, self).terminate()

class SearchThread(QtCore.QThread):
	output = QtCore.pyqtSignal(utils.cls.Song)
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
		self.dont_emit_NoResultsException_error = False
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
			
			if (domainName.endswith('youtube.com') or domainName.endswith('youtu.be')) and not 'videoplayback' in self.url:
				queries = parse_qs(urlparse(self.url).query)
				if 'p' in queries or 'list' in queries:
					log.debug("Url is a direct url (Youtube playlist)")
					if 'p' in queries:
						playlist_id = queries['p'][0]
					elif 'list' in queries:
						playlist_id = queries['list'][0]
					videos_ids = Main.WebParser.LinksGrabber.parse_Youtube_playlist(playlist_id)					
					t_pool = ThreadPool(max_threads=config.buildSongObjs_processes, catch_returns=True, logger=log)
					for v_id in videos_ids:
						t_pool(Main.WebParser.LinksGrabber.get_youtube_dl_link)(v_id)
					links_gen = t_pool.iter()
					
				else:
					log.debug("Url is a direct url (Youtube)")
					if domainName.endswith('youtube.com'):
						video_id = queries['v'][0]
					else:
						video_id = urlparse(self.url).path.strip('/')
						
					try:
						metaUrlObj = Main.WebParser.LinksGrabber.get_youtube_dl_link(video_id)
						links_gen = (x for x in [metaUrlObj]) if metaUrlObj else (x for x in [])
					except YoutubeException, e:
						self.error.emit(e)
						self.dont_emit_NoResultsException_error = True
						links_gen = (x for x in [])
						
			# elif domainName.endswith('bandcamp.com'):
				# if '/album/' in self.url:
					# log.debug("Url is a direct url (bandcamp album)")
					# metaUrlObjs = Main.WebParser.LinksGrabber.get_bandcamp_album_dl_links(self.url)
					# links_gen = (x for x in metaUrlObjs)
				# elif '/track/' in self.url:
					# log.debug("Url is a direct url (bandcamp)")
					# metaUrlObj = Main.WebParser.LinksGrabber.get_bandcamp_dl_link(self.url)
					# links_gen = (x for x in [metaUrlObj]) if metaUrlObj else (x for x in [])
				# else:
					# links_gen = (x for x in [])
			# elif domainName.endswith('soundcloud.com'):
				# log.debug("Url is a direct url (Soundcloud)")
				# if self.url.startswith('https://'):
					# self.url = self.url.replace('https://', 'http://')
				# metaUrlObj = Main.WebParser.LinksGrabber.get_soundcloud_dl_link(self.url)	
				# links_gen = (x for x in [metaUrlObj]) if metaUrlObj else (x for x in [])
			else:
				metaUrlObjs = []
				ydlResult = Main.WebParser.LinksGrabber.get_ydl_extract_info(self.url)
				# from PyQt4 import QtCore; import pdb; QtCore.pyqtRemoveInputHook(); pdb.set_trace()
				
				if ydlResult:
					if ydlResult.has_key('entries'):
						sequence = ydlResult['entries']
					elif ydlResult.has_key('formats'):
						sequence = ydlResult['formats']
					elif ydlResult.has_key('url'):
						sequence = [ydlResult]
					else:
						sequence = [ydlResult]
						
					for entry in sequence:
						metaUrlObj = utils.cls.MetaUrl(	entry['url'],
														entry['extractor'],
														itag=utils.cls.ItagData(0, entry['ext'], entry.get('height', entry['format_id'])),
														title=entry.get('title'),
														videoid=entry.get('id'),
														webpage_url=entry.get('webpage_url'),
														view_count=entry.get('view_count', 0),
														description=entry.get('description', ''),
														thumbnail=entry.get('thumbnail')
														)
						metaUrlObjs.append(metaUrlObj)
														
					links_gen = (x for x in metaUrlObjs)
				else:
					log.debug("Url is a direct url (%s file)." % os.path.splitext(self.url.split('/')[-1])[1].strip('.'))
					
					metaUrlObj = utils.cls.MetaUrl(self.url, "Direct Link")
					links_gen = (x for x in [metaUrlObj])
		else:
			links_gen = Main.WebParser.LinksGrabber.search(self.song, self.numOfSongs, returnGen=True)
			
		i = 0
		for i, link in enumerate(links_gen):
			self.pool(self.create_and_emit_SongObj)(link)
			
		while not self.pool.isFinished():
			time.sleep(0.1)
		
		log.debug("Created %d song objects." % i)
		if not self.songObj_emitted:
			log.error("Got NoResultsException.")
			if not self.dont_emit_NoResultsException_error:
				self.error.emit(NoResultsException(self.isDirectLink))
		elif self.luckyDownload:
			self.finished_lucky.emit()
				
	def create_and_emit_SongObj(self, link):
		try:
			urlObj = Main.HTTPQuery.get_file_details(link)
			self.songObj = utils.cls.Song(*(urlObj+(self.song,)))
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
	status = QtCore.pyqtSignal(object)
	error = QtCore.pyqtSignal(Exception)
	startedTask = QtCore.pyqtSignal(int)
	finishedTask = QtCore.pyqtSignal(int, int, int)
	
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)
		self._terminated = False
		
		self.tasks = []
		
	def queue(self, songObj, dl_dir, taskId):
		self._terminated = False
		
		self.tasks.append([taskId, songObj, dl_dir])
		if not self.isRunning():
			self.start()
	
	@utils.decorators.log_exceptions(Exception, log)
	def run(self): # Called by Qt once the thread environment has been set up.
		while self.tasks:
			taskId, songObj, dl_dir = self.tasks.pop(0)
			self.startedTask.emit(taskId)
			
			isVideo = songObj.ext in ['mp4', 'avi', 'flv', 'webm', 'mkv']
			isAudio = songObj.ext in ['mp3', 'm4a', 'wav']
			isMultimediaFile = any([isVideo, isAudio])
			convertNeeded = isMultimediaFile and songObj.ext != 'mp3' and config.downloadAudio
			encode_time = 0
			url = songObj.url
			filesize = songObj.filesize
			
			audio_path = os.path.join(dl_dir, songObj.GetProperFilename('mp3')) # final path
			video_path = os.path.join(dl_dir, songObj.GetProperFilename()) # final path
			dest_audio_path = os.path.join(config.temp_dir, "%s.mp3" % utils.get_rand_string())
			
			if not isMultimediaFile:
				dest_path = os.path.join(config.temp_dir, utils.get_rand_string())
			elif songObj.ext == "mp3": # no convertion needed
				dest_path = dest_audio_path
			else:
				dest_path = os.path.join(config.temp_dir, "%s.%s" % (utils.get_rand_string(), songObj.ext))
			
			dl_obj = SmartDL(url, dest_path, logger=log, fix_urls=False)
			dl_obj.start(blocking=False)
			
			while not dl_obj.isFinished():
				if dl_obj.status == 'combining':
					self.status.emit(tr("Combining Parts..."))
					break
				
				self.downloadProgress.emit(int(dl_obj.get_progress()*100), dl_obj.get_speed(), dl_obj.get_eta(), dl_obj.get_dl_size(), filesize)
				time.sleep(0.1)
			while not dl_obj.isFinished():
				# if we were breaking the last loop, we are waiting for
				# parts to get combined. we shall wait.
				time.sleep(0.1)
			if not dl_obj.isSuccessful:
				log.error("Got DownloadFailedException() for %s" % url)
				self.error.emit(IOError())
				self.terminate()
				return
			self.downloadProgress.emit(100, dl_obj.get_speed(), dl_obj.get_eta(), filesize, filesize)
			
			if convertNeeded:
				t1 = time.time()
				log.debug("Encoding Audio...")
				self.status.emit(tr("Encoding Audio..."))
				est_final_filesize = songObj.final_filesize
				if est_final_filesize:
					print "Encoding: %s (%.2f MB) to %s" % (dest_audio_path, est_final_filesize / 1024.0 / 1024.0, dl_dir)
				else:
					print "Encoding: %s to %s" % (dest_audio_path, dl_dir)
				
				proc = Wrappers.FFMpeg(dest_path, dest_audio_path, config.itag_audio_bitrates[songObj.itag.quality])
				self.encProgress.emit(0)
				for fs_counter in proc:
					if not est_final_filesize:
						continue
					status = r"Encoding: %.2f MB / %.2f MB %s [%3.2f%%]" % (fs_counter / 1024.0, est_final_filesize / 1024.0**2, utils.progress_bar(1.0*fs_counter*1024/est_final_filesize) , fs_counter*1024 * 100.0 / est_final_filesize)
					status = status + chr(8)*(len(status)+1)
					print status,
					self.encProgress.emit(int(fs_counter*1024 * 100.0 / est_final_filesize))
				self.encProgress.emit(100)
				
				t2 = time.time()
				encode_time += t2-t1
				
				if not config.downloadVideo or not isVideo:
					log.debug("Removing %s..." % dest_path)
					os.unlink(dest_path)
			else:
				dest_audio_path = dest_path
					
			if config.downloadAudio and config.trimSilence:
				t1 = time.time()
				
				log.debug("Trimming Silence...")
				self.status.emit(tr("Trimming Silence from edges..."))
				
				temp_audio_trimmed_path = "%s.tmp.mp3" % dest_audio_path
				if os.path.exists(temp_audio_trimmed_path):
					os.unlink(temp_audio_trimmed_path)
				os.rename(dest_audio_path, temp_audio_trimmed_path)
				
				est_final_filesize = songObj.final_filesize
				print "Trimming Silence: %s (%.2f MB) to %s" % (dest_audio_path, est_final_filesize / 1024.0**2, dl_dir)
				self.encProgress.emit(0)
				
				proc = Wrappers.SoX(temp_audio_trimmed_path, dest_audio_path)
				for progress in proc:
					status = r"Trimming Silence: %s" % utils.progress_bar(progress/100.0)
					status = status + chr(8)*(len(status)+1)
					print status,
					self.encProgress.emit(progress)
				self.encProgress.emit(100)
				
				t2 = time.time()
				encode_time += t2-t1
				
				if not os.path.exists(dest_audio_path):
					log.error('SoX failed.')
				
			log.debug("Copying Files...")
			self.status.emit(tr("Copying Files..."))
			
			if isVideo:
				# IMPROVE: this crashes when a video is running in media player, os.unlink removes it, but it is still running in media player.
				if config.downloadAudio:
					log.debug("Moving %s to %s" % (dest_audio_path, audio_path))
					shutil.move(dest_audio_path, audio_path) 
				if config.downloadVideo:
					log.debug("Moving %s to %s" % (dest_path, video_path))
					shutil.move(dest_path, video_path)
			if isAudio:
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
			
			if encode_time:
				stats_str += tr('; Encoded: %ds') % encode_time
			self.status.emit(stats_str)
			self.finishedTask.emit(taskId, dl_time, encode_time)
		
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
	MainResult = QtCore.pyqtSignal(utils.cls.LyricsData)
	MinorResult = QtCore.pyqtSignal(utils.cls.LyricsData)
	eof = QtCore.pyqtSignal()
	error = QtCore.pyqtSignal(object)
	
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
	output = QtCore.pyqtSignal(object, object, object, object)
	error = QtCore.pyqtSignal(object)
	
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
	error = QtCore.pyqtSignal(object)
	
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
	error = QtCore.pyqtSignal(object, QtGui.QTreeWidgetItem)
	
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
	error = QtCore.pyqtSignal(object)
	
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
	error = QtCore.pyqtSignal(basestring, object)
	
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
			self.error.emit(tr("No data was found."), self.widgetItem)
			return
			
		self.output.emit(tracks, self.widgetItem)
	
	def terminate(self):
		"Setting _terminated to True"
		self._terminated = True
		super(ChartsLookupThread, self).terminate()
		
class LyricsFulltextSearchThread(QtCore.QThread):
	output = QtCore.pyqtSignal(object)
	
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
	t1 = time.time()
	
	def f(): print x
	
	t = SearchThread()
	t.output.connect(f)
	t.search('naruto', 15, False)
	
	while t.isRunning():
		time.sleep(0.1)
	
	t2 = time.time()
	print "took %ss" % (t2-t1)