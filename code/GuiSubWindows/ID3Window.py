# Copyright (C) 2012-2013 Itay Brandes

''' ID3 Window '''

import os.path

from PyQt4 import QtCore
from PyQt4 import QtGui
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, COMM, APIC, USLT, error, ID3NoHeaderError
from mutagen.easyid3 import EasyID3

import Config; config = Config.config
from logger import log
from Gui_Threads import GoogleImagesGrabberThread, LyricsGrabberThread, MusicBrainzFetchThread
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, songPath, id3_action="", parent=None):
		super(MainWin, self).__init__(parent)
		self.isValid = True
		
		self.path = songPath
		self.id3_action = id3_action if id3_action else config.id3_action
		self.changed_AlbumArt = False
		self.pix_path = ""
		self.albumArt_task = "nothing"
		
		'''
		albumArt_task may be 'nothing', 'add' and 'delete':
		'nothing': Do not touch the APIC tag.
		'add': creates an APIC tag with self.pix_path.
		'delete': deletes an APIC tag, if exists.
		'''
		self.lyricsList = [] # The lyrics list
		self.lyricsListIndex = -1
		
		# Will be enabled when the last value of lyricsList will be fetched
		# and the servers will return EOF.
		# Until then, the lyrics groupbox will look like:
		# Lyrics (4/7+) (showing lyrics num. 4 out of seven, and more are available but not fetched yet)
		# When that switch will be enabled, the plus sign will get disappeared.
		self.lyricsList_EOF = False
		
		# If value is 0, notfound errors won't be suppressed. Any other value will suppress all errors.
		self.suppress_notfound_errors = 0
		
		self.setWindowTitle(tr("ID3 Editor"))
		self.resize(650, 430)
		self.setWindowIcon(QtGui.QIcon(r'pics\id3edit.png'))
		self.empty_cdbox_path = r"pics\empty_cdbox_%s.png" % config.lang if os.path.exists("pics\empty_cdbox_%s.png" % config.lang) else r"pics\empty_cdbox.png"
		
		log.debug("Initializing SetID3Window Widgets...")
		self.init_threads()
		self.init_id3data()
		if not self.isValid:
			return
		self.init_widgets()
		
		if self.id3_action == 'ask_albumart':
			self.fetch_all(autochoose_albumart=False)
		if self.id3_action == 'ask':
			self.fetch_all(autochoose_albumart=True)
		if self.id3_action == 'noask':
			self.close_with_timeout()
			self.fetch_all(autochoose_albumart=True)
		
	def init_threads(self):
		self.thread = LyricsGrabberThread()
		self.thread.MainResult.connect(self.slot_lyrics_main)
		self.thread.MinorResult.connect(self.slot_lyrics_minor)
		self.thread.eof.connect(self.slot_lyrics_eof)
		self.thread.error.connect(self.slot_error)
		
		self.id3fetch_thread = MusicBrainzFetchThread()
		self.id3fetch_thread.output.connect(self.slot_setFreeDBData)
		self.id3fetch_thread.error.connect(self.slot_error)
		
		self.googleImages_thread = GoogleImagesGrabberThread()
		self.googleImages_thread.output.connect(self.slot_googleImagesResult)
		
	def init_id3data(self):
		try: # Add ID3 Tags if does not exist
			mp3Obj = MP3(self.path, ID3=ID3)
			mp3Obj.add_tags()
			mp3Obj.save()
		except error:
			pass
		except HeaderNotFoundError:
			log.warning("This MP3 files seems to be faulty. Cannot edit it's ID3 data.")
			QtGui.QMessageBox.critical(self, tr("Error"), tr("This MP3 files seems to be faulty. Cannot edit it's ID3 data."), QtGui.QMessageBox.Ok)
			self.isValid = False
			return
		try:
			self.easyID3Obj = EasyID3(self.path)
			self.ID3Obj = ID3(self.path)
		except ID3NoHeaderError:
			log.warning("This MP3 files seems to be faulty. Cannot edit it's ID3 data.")
			QtGui.QMessageBox.critical(self, tr("Error"), tr("This MP3 files seems to be faulty. Cannot edit it's ID3 data."), QtGui.QMessageBox.Ok)
			self.isValid = False
			return
		
		USLT_Tag = [x for x in self.ID3Obj.keys() if x.startswith('USLT')]
		
		if USLT_Tag:
			self.originalLyrics = self.ID3Obj[USLT_Tag[0]].text
		else:
			self.originalLyrics = ""
		
		APIC_Tag = [x for x in self.ID3Obj.keys() if x.startswith('APIC')]
		if APIC_Tag:
			APIC_Tag = APIC_Tag[0]
			
			mime = self.ID3Obj[APIC_Tag].mime
			if mime == u'image/jpeg':
				self.pix_path = r"%s\album_art.jpg" % (config.temp_dir)
			elif mime == u'image/png':
				self.pix_path = r"%s\album_art.png" % (config.temp_dir)
			else:
				self.pix_path = r"%s\album_art.pic" % (config.temp_dir)
			
			with open(self.pix_path, 'wb') as f:
				f.write(self.ID3Obj[APIC_Tag].data)
		
	def init_widgets(self):
		self.title = QtGui.QLineEdit(utils.fix_faulty_unicode(self.easyID3Obj['title'][0])) if 'title' in self.easyID3Obj.keys() else QtGui.QLineEdit("")
		self.artist = QtGui.QLineEdit(utils.fix_faulty_unicode(self.easyID3Obj['artist'][0])) if 'artist' in self.easyID3Obj.keys() else QtGui.QLineEdit("")
		self.album = QtGui.QLineEdit(utils.fix_faulty_unicode(self.easyID3Obj['album'][0])) if 'album' in self.easyID3Obj.keys() else QtGui.QLineEdit("")
		self.date = QtGui.QLineEdit(self.easyID3Obj['date'][0]) if 'date' in self.easyID3Obj.keys() else QtGui.QLineEdit("")
		
		self.original_title = unicode(self.title.displayText())
		self.original_artist = unicode(self.artist.displayText())
		self.original_album = unicode(self.album.displayText())
		self.original_date = unicode(self.date.displayText())
		
		pixmap = QtGui.QPixmap(self.pix_path) if self.pix_path else QtGui.QPixmap(self.empty_cdbox_path)
		if max(pixmap.width(), pixmap.height()) > 200:
			pixmap = pixmap.scaled(200, 200, aspectRatioMode=QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
			
		self.albumArt = QtGui.QLabel()
		self.albumArt.setPixmap(pixmap)
		self.albumArt.setStyleSheet("border-style:solid; border-color:#999792; border-width:1px;")
		
		self.remove_albumart_button = QtGui.QPushButton(QtGui.QIcon(r'pics\cancel.png'), "")
		self.remove_albumart_button.clicked.connect(self.remove_albumart_slot)
		self.remove_albumart_button.setFlat(True)
		if not self.pix_path:
			self.remove_albumart_button.setEnabled(False)

		# Row Layouts
		buttonLayout = QtGui.QHBoxLayout()
		applyButton = QtGui.QPushButton(tr("Apply"))
		applyButton.clicked.connect(self.slot_apply)
		closeButton = QtGui.QPushButton(tr("Dismiss"))
		closeButton.clicked.connect(self.close)
		buttonLayout.addWidget(applyButton)
		buttonLayout.addWidget(closeButton)
		
		self.changeImageButton = QtGui.QPushButton(tr("Fetch From The Web"))
		self.changeImageButton.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
		self.changeImageButton.clicked.connect(self.slot_changeImage)
		self.loadLocalImageButton = QtGui.QPushButton(tr("Choose Image Locally"))
		self.loadLocalImageButton.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
		self.loadLocalImageButton.clicked.connect(self.slot_loadLocalImage)
		self.loadFreeDBButton = QtGui.QPushButton(tr("Load From MusicBrainz"))
		self.loadFreeDBButton.clicked.connect(self.slot_loadFreeDBButton)
		self.restoreOriginalButton = QtGui.QPushButton(tr("Restore Original"))
		self.restoreOriginalButton.clicked.connect(self.slot_restoreOriginal)

		# Layouts
		mainLayout = QtGui.QVBoxLayout()
		formLayout = QtGui.QHBoxLayout()
		
		### RIGHT ###
		rightLayout = QtGui.QVBoxLayout()
		
		basicTagsGroup = QtGui.QGroupBox(tr("ID3 Tags"))
		layout = QtGui.QFormLayout()
		layout.addRow(tr("Title:"), self.title)
		layout.addRow(tr("Artist:"), self.artist)
		layout.addRow(tr("Album:"), self.album)
		layout.addRow(tr("Date:"), self.date)
		buttons = QtGui.QHBoxLayout()
		buttons.addWidget(self.loadFreeDBButton)
		buttons.addWidget(self.restoreOriginalButton)
		layout.addRow(buttons)
		basicTagsGroup.setLayout(layout)
		
		albumArtGroup = QtGui.QGroupBox(tr("Album Art"))
		layout = QtGui.QGridLayout()
		layout.addWidget(self.albumArt, 0, 0, 1, 3, QtCore.Qt.AlignCenter)
		layout.addWidget(self.changeImageButton, 1, 0)
		layout.addWidget(self.loadLocalImageButton, 1, 1)
		layout.addWidget(self.remove_albumart_button, 1, 2)
		albumArtGroup.setLayout(layout)
		
		rightLayout.addWidget(basicTagsGroup)
		rightLayout.addWidget(albumArtGroup)
		
		### LEFT ###
		self.changeLyricsButton = QtGui.QPushButton(tr("Load Lyrics From The Web"))
		self.changeLyricsButton.clicked.connect(self.slot_changeLyrics)
		self.changeLyricsButton.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
		self.deleteLyricsButton = QtGui.QPushButton(QtGui.QIcon(r'pics\cancel.png'), "")
		self.deleteLyricsButton.setFlat(True)
		self.deleteLyricsButton.clicked.connect(self.slot_deleteLyrics)
		
		self.lyrics_left_button = QtGui.QPushButton("<<")
		self.lyrics_left_button.setEnabled(False)
		self.lyrics_left_button.clicked.connect(self.slot_lyrics_left_button)
		self.lyrics_right_button = QtGui.QPushButton(">>")
		self.lyrics_right_button.setEnabled(False)
		self.lyrics_right_button.clicked.connect(self.slot_lyrics_right_button)
		self.changeLyricsLabel = QtGui.QLabel(tr("* Loaded from file's tags *")) if self.originalLyrics else QtGui.QLabel("")
		self.changeLyricsLabel.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
		self.changeLyricsLabel.setWordWrap(True)
		
		self.lyrics = QtGui.QPlainTextEdit(self.originalLyrics)
		leftLayout = QtGui.QGroupBox(tr("Lyrics"))
		self.lyricsGroupBox = leftLayout # For manipulating the title name
		layout = QtGui.QVBoxLayout()
		layout.addWidget(self.lyrics)
		inner_layout = QtGui.QHBoxLayout()
		inner_layout.addWidget(self.lyrics_left_button)
		inner_layout.addWidget(self.changeLyricsLabel)
		inner_layout.addWidget(self.lyrics_right_button)
		layout.addLayout(inner_layout)
		inner_layout = QtGui.QHBoxLayout()
		inner_layout.addWidget(self.changeLyricsButton)
		inner_layout.addWidget(self.deleteLyricsButton, alignment=QtCore.Qt.AlignRight)
		layout.addLayout(inner_layout)
		leftLayout.setLayout(layout)
		
		### Exit Counter Layout ###
		exitCounterLayout = QtGui.QHBoxLayout()
		self.exitCounterLabel = QtGui.QLabel(tr("<h1>Closing window in %d seconds...</h1>") % (config.id3_noask_wait_interval+1))
		self.exitCounterButton = QtGui.QPushButton(tr("Don't close"))
		self.exitCounterButton.clicked.connect(self.slot_close_cancel)
		exitCounterLayout.addWidget(self.exitCounterLabel)
		exitCounterLayout.addWidget(self.exitCounterButton)
		
		### OTHERS ###
		formLayout.addLayout(rightLayout)
		formLayout.addWidget(leftLayout)
		mainLayout.addLayout(formLayout)
		if self.id3_action == 'noask':
			mainLayout.addLayout(exitCounterLayout)
		mainLayout.addLayout(buttonLayout)
		self.setLayout(mainLayout)
	
	def fetch_all(self, autochoose_albumart):
		title = unicode(self.title.displayText())
		artist = unicode(self.artist.displayText())
		
		if title or artist:
			self.suppress_notfound_errors = 3
			self.slot_changeImage(autochoose_albumart)
			self.slot_changeLyrics()
			self.slot_loadFreeDBButton()
	
	def close_with_timeout(self):
		"Function shows a message to the user for 5 seconds, then closes window."
		self.close_waitthreads_calls = 0
		self.close_timer = QtCore.QTimer()
		self.close_timer.timeout.connect(self.close_waitthreads)
		self.close_timer.start(1000)

	def close_waitthreads(self):
		sec_to_wait = config.id3_noask_wait_interval
		
		if sec_to_wait-self.close_waitthreads_calls > 0:
			self.exitCounterLabel.setText(tr("<h1>Closing window in %d seconds...</h1>") % (sec_to_wait-self.close_waitthreads_calls))
		else:
			self.exitCounterLabel.setText(tr("<h1>Closing Window...</h1>"))
			if not any([self.thread.isRunning(), self.id3fetch_thread.isRunning(), self.googleImages_thread.isRunning()]):
				self.close_timer.stop()
				self.slot_apply()
		
		self.close_waitthreads_calls += 1
	
	def slot_close_cancel(self):
		if hasattr(self, 'close_timer'):
			self.close_timer.stop()
			self.exitCounterLabel.setText(tr("<h1>Automatic Closing Canceled.</h1>"))
			self.exitCounterButton.setEnabled(False)
		
	def slot_error(self, s):
		if hasattr(self, 'splash') and self.suppress_notfound_errors <= 1:
			self.splash.finish(self)
		if self.suppress_notfound_errors == 0:
			QtGui.QMessageBox.warning(self, tr("Error"), "<h2>%s</h2>" % s, QtGui.QMessageBox.Ok)
		else:
			self.suppress_notfound_errors -= 1
			
		self.changeLyricsButton.setEnabled(True)
		self.changeImageButton.setEnabled(True)
		self.loadFreeDBButton.setEnabled(True)
		self.restoreOriginalButton.setEnabled(True)
	
	def slot_apply(self):
		self.ID3TagsToEdit = {}
		log.debug("Saving ID3 Data in cache...")

		self.ID3TagsToEdit['TIT2'] = TIT2(encoding=3, text=unicode(self.title.displayText()))
		self.ID3TagsToEdit['TPE1'] = TPE1(encoding=3, text=unicode(self.artist.displayText()))
		self.ID3TagsToEdit['TALB'] = TALB(encoding=3, text=unicode(self.album.displayText()))
		self.ID3TagsToEdit['TDRC'] = TDRC(encoding=3, text=unicode(self.date.displayText()))
		self.ID3TagsToEdit['COMM'] = COMM(encoding=3, text=unicode(config.id3tags_whitemark), desc='')
		lyrics = unicode(self.lyrics.toPlainText()).replace('\r\n','\n').replace('\n','\r\n')

		if lyrics:
			if utils.isHebrew(lyrics):
				self.ID3TagsToEdit['USLT'] = USLT(encoding=3, lang=u'heb', desc=u'', text=lyrics)
			else:
				self.ID3TagsToEdit['USLT'] = USLT(encoding=3, lang=u'eng', desc=u'', text=lyrics)
		else:
			self.ID3TagsToEdit['USLT'] = ''

		if self.albumArt_task == 'add' and self.pix_path:
			with open(self.pix_path, 'rb') as f:
				data = f.read()
			self.ID3TagsToEdit['APIC'] = APIC(encoding=0, mime=utils.guess_image_mime_type(self.pix_path),
												type=0, desc="", data=data)
		elif self.albumArt_task == 'delete':
			self.ID3TagsToEdit['APIC'] = '' # empty value doesn't add a new APIC tag. All other APIC tags are removed piror to insertion.
		self.close()

	def slot_changeImage(self, autochoose=False):
		title = unicode(self.title.displayText())
		artist = unicode(self.artist.displayText())
		if title and artist:
			s = "%s - %s" % (artist, title)
		elif title:
			s = title
		elif artist:
			s = artist
		else:
			self.slot_error(tr("No title or artist values were given."))
			return
		self.last_search_string = s
			
		splash_movie = QtGui.QMovie(r'pics\loading_row.gif')
		self.splash = utils.qt.MovieSplashScreen(splash_movie, QtCore.Qt.WindowStaysOnTopHint)
		self.splash.show()
		
		self.changeImageButton.setEnabled(False)
		
		if autochoose:
			self.googleImages_thread.search(s, 1)
		else:
			self.googleImages_thread.search(s, 3)
			
	def slot_loadLocalImage(self):
		dialog = QtGui.QFileDialog()
		dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
		f = unicode(dialog.getOpenFileName(caption=tr('Choose the artwork'), filter=tr("Images (*.png *.jpg)")))
		if f:
			self.pix_path = f
			pixmap = QtGui.QPixmap(self.pix_path)
			if max(pixmap.width(), pixmap.height()) > 200:
				pixmap = pixmap.scaled(200, 200, aspectRatioMode=QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
			self.albumArt.setPixmap(pixmap)
			self.albumArt_task = 'add'
			self.remove_albumart_button.setEnabled(True)
	
	def slot_googleImagesResult(self, fn_list):
		self.changeImageButton.setEnabled(True)
		
		if self.suppress_notfound_errors <= 1:
			self.splash.finish(self)
		
		if not fn_list and self.suppress_notfound_errors == 0:
			QtGui.QMessageBox.warning(self, "Error", tr("<h2>No photos were found.</h2>"), QtGui.QMessageBox.Ok)
			return
			
		if self.suppress_notfound_errors > 0:
			self.suppress_notfound_errors -= 1
			
		if len(fn_list) == 1:
			self.pix_path = fn_list[0]
		else:
			w = AlbumArtWin(fn_list, self.last_search_string)
			w.exec_()
			if hasattr(w, 'pix'):
				self.pix_path = w.pix
			if hasattr(w, 'search_string'):
				splash_movie = QtGui.QMovie(r'pics\loading_row.gif')
				self.splash = utils.qt.MovieSplashScreen(splash_movie, QtCore.Qt.WindowStaysOnTopHint)
				self.splash.show()
				
				self.last_search_string = w.search_string
				self.googleImages_thread.search(w.search_string, 3)
				return

		if self.pix_path:
			pixmap = QtGui.QPixmap(self.pix_path)
			if max(pixmap.width(), pixmap.height()) > 200:
				pixmap = pixmap.scaled(200, 200, aspectRatioMode=QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
			self.albumArt.setPixmap(pixmap)
			self.albumArt_task = 'add'
			self.remove_albumart_button.setEnabled(True)
	
	def slot_changeLyrics(self):
		title = unicode(self.title.displayText())
		artist = unicode(self.artist.displayText())
		
		if not title and not artist:
			self.slot_error(tr("No title or artist values were given."))
			return
		
		self.lyricsList = []
		self.lyricsListIndex = -1
		
		splash_movie = QtGui.QMovie(r'pics\loading_row.gif')
		self.splash = utils.qt.MovieSplashScreen(splash_movie, QtCore.Qt.WindowStaysOnTopHint)
		self.splash.show()
		
		self.changeLyricsButton.setEnabled(False)
		
		self.thread.search(title, artist)
		
	def slot_deleteLyrics(self):
		self.changeLyricsLabel.setText("")
		self.lyrics.setPlainText("")
	
	def remove_albumart_slot(self):
		self.albumArt_task = 'delete'
		self.pix_path = ""
		self.albumArt.setPixmap(QtGui.QPixmap(self.empty_cdbox_path))
		self.remove_albumart_button.setEnabled(False)
		log.debug('AlbumArt is marked for deletion.')
	
	def slot_lyrics_main(self, lyrics):
		self.changeLyricsButton.setEnabled(True)
		
		if self.suppress_notfound_errors <= 1:
			self.splash.finish(self)
		
		if self.suppress_notfound_errors > 0:
			self.suppress_notfound_errors -= 1
		
		self.lyricsList.append(lyrics)
		self.lyricsListIndex = len(self.lyricsList)-1
		if self.lyricsListIndex > 0:
			self.lyrics_left_button.setEnabled(True)
		
		# We're dealing with LyricsData object here
		self.lyrics.setPlainText(lyrics.lyrics)
		self.changeLyricsLabel.setText("%s - %s" % (lyrics.artist, lyrics.title))
		if self.lyricsList_EOF:
			self.lyricsGroupBox.setTitle(tr("Lyrics (%d/%d)") % (self.lyricsListIndex+1, len(self.lyricsList)))
		else:
			self.lyricsGroupBox.setTitle(tr("Lyrics (%d/%d+)") % (self.lyricsListIndex+1, len(self.lyricsList)))
		
	def slot_lyrics_minor(self, lyrics):
		self.changeLyricsButton.setEnabled(True)
		
		if self.suppress_notfound_errors <= 1:
			self.splash.finish(self)
			
		self.lyricsList.append(lyrics)
		self.lyrics_right_button.setEnabled(True)
		self.lyricsGroupBox.setTitle(tr("Lyrics (%d/%d+)") % (self.lyricsListIndex+1, len(self.lyricsList)))
	
	def slot_lyrics_eof(self):
		self.changeLyricsButton.setEnabled(True)
		
		if self.suppress_notfound_errors <= 1:
			self.splash.finish(self)
			
		self.lyricsList_EOF = True
		self.lyricsGroupBox.setTitle(tr("Lyrics") + " (%d/%d)" % (self.lyricsListIndex+1, len(self.lyricsList)))
		self.lyrics_right_button.setEnabled(False)
			
	def slot_lyrics_left_button(self):
		self.lyricsListIndex -= 1
		lyrics = self.lyricsList[self.lyricsListIndex]
		
		# We're dealing with LyricsData object here
		self.lyrics.setPlainText(lyrics.lyrics)
		self.changeLyricsLabel.setText("%s - %s" % (lyrics.artist, lyrics.title))
		if self.lyricsList_EOF:
			self.lyricsGroupBox.setTitle(tr("Lyrics") + " (%d/%d)" % (self.lyricsListIndex+1, len(self.lyricsList)))
		else:
			self.lyricsGroupBox.setTitle(tr("Lyrics") + " (%d/%d+)" % (self.lyricsListIndex+1, len(self.lyricsList)))
		
		self.lyrics_right_button.setEnabled(True)
		if self.lyricsListIndex == 0:
			self.lyrics_left_button.setEnabled(False)
	
	def slot_lyrics_right_button(self):
		self.lyricsListIndex += 1
		lyrics = self.lyricsList[self.lyricsListIndex]
		
		# We're dealing with LyricsData object here
		self.lyrics.setPlainText(lyrics.lyrics)
		self.changeLyricsLabel.setText("%s - %s" % (lyrics.artist, lyrics.title))
		if self.lyricsList_EOF:
			self.lyricsGroupBox.setTitle(tr("Lyrics") + " (%d/%d)" % (self.lyricsListIndex+1, len(self.lyricsList)))
		else:
			self.lyricsGroupBox.setTitle(tr("Lyrics") + " (%d/%d+)" % (self.lyricsListIndex+1, len(self.lyricsList)))
		
		self.lyrics_left_button.setEnabled(True)
		if self.lyricsListIndex == len(self.lyricsList)-1:
			self.thread.nextLyrics()
			self.lyrics_right_button.setEnabled(False)
		
	def slot_restoreOriginal(self):
		self.title.setText(self.original_title)
		self.artist.setText(self.original_artist)
		self.album.setText(self.original_album)
		self.date.setText(self.original_date)
	
	def slot_loadFreeDBButton(self):
		title = unicode(self.title.displayText())
		artist = unicode(self.artist.displayText())
		
		if not title and not artist:
			self.slot_error(tr("No title or artist values were given."))
			return
		
		splash_movie = QtGui.QMovie(r'pics\loading_row.gif')
		self.splash = utils.qt.MovieSplashScreen(splash_movie, QtCore.Qt.WindowStaysOnTopHint)
		self.splash.show()
		
		self.loadFreeDBButton.setEnabled(False)
		self.restoreOriginalButton.setEnabled(False)
		
		self.id3fetch_thread.fetch(title, artist)
		
	def slot_setFreeDBData(self, album, date, tag, artist):
		self.loadFreeDBButton.setEnabled(True)
		self.restoreOriginalButton.setEnabled(True)
		
		if self.suppress_notfound_errors <= 1:
			self.splash.finish(self)
		
		if self.suppress_notfound_errors > 0:
			self.suppress_notfound_errors -= 1
		
		if album:
			self.album.setText(album)
		if date:
			self.date.setText(date)
		if artist:
			self.artist.setText(artist)
			
class AlbumArtWin(QtGui.QDialog):
	def __init__(self, fn_list, last_search_string, parent=None):
		super(AlbumArtWin, self).__init__(parent)
		
		self.fn_list = fn_list
		self.last_search_string = last_search_string
		
		self.setWindowTitle(tr("Set Album Art"))
		self.resize(20, 10)
		self.setWindowIcon(QtGui.QIcon(r'pics\id3edit.png'))
		
		log.debug("Initializing SetAlbumArtWindow Widgets...")
		self.init_widgets()
		
	def init_widgets(self):
		self.albumArts = []
		for pix_path in self.fn_list:
			pixmap = QtGui.QPixmap(pix_path)
			
			if max(pixmap.width(), pixmap.height()) > 200:
				pixmap = pixmap.scaled(200, 200, aspectRatioMode=QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
			
			button = QtGui.QPushButton(QtGui.QIcon(pixmap), '')
			button.setIconSize(pixmap.size())
			button.clicked.connect(self.slot_select)
			button.pix_path = pix_path
			self.albumArts.append(button)
			
		self.saveSelection_CheckBox = QtGui.QCheckBox(tr("Choose album art automatically next time"))
		self.saveSelection_CheckBox.setTristate(False)
		if config.id3_action == 'ask':
			self.saveSelection_CheckBox.setCheckState(True)
			self.saveSelection_CheckBox.setEnabled(False)
		elif config.id3_action == 'ask_albumart':
			self.saveSelection_CheckBox.setCheckState(False)

		# Layouts
		mainLayout = QtGui.QVBoxLayout()
		closeButton = QtGui.QPushButton(tr("Cancel"))
		closeButton.clicked.connect(self.close)

		pixLayout = QtGui.QHBoxLayout()
		for art in self.albumArts:
			pixLayout.addWidget(art)
		
		searchLabel = QtGui.QLabel(tr("Look for:"))
		self.search_lineEdit = QtGui.QLineEdit(self.last_search_string)
		self.search_lineEdit.returnPressed.connect(self.slot_search)
		search_button = QtGui.QPushButton(tr("Search"))
		search_button.clicked.connect(self.slot_search)
		
		textboxLayout = QtGui.QHBoxLayout()
		textboxLayout.addWidget(searchLabel)
		textboxLayout.addWidget(self.search_lineEdit)
		textboxLayout.addWidget(search_button)
		
		mainLayout.addWidget(QtGui.QLabel(tr("<h2>Choose a new album art:</h2>")), alignment = QtCore.Qt.AlignCenter)
		mainLayout.addLayout(pixLayout)
		mainLayout.addWidget(QtGui.QLabel(tr("<h2>Or search for other images:</h2>")), alignment = QtCore.Qt.AlignCenter)
		mainLayout.addLayout(textboxLayout)
		
		if config.id3_action != 'noask':
			mainLayout.addWidget(self.saveSelection_CheckBox)
		mainLayout.addWidget(closeButton)

		self.setLayout(mainLayout)
	
	def slot_select(self):
		pix = self.sender().pix_path
		log.debug("Choosing Album Art '%s'..." % pix)
		self.pix = pix
		
		if self.saveSelection_CheckBox.isChecked():
			config.id3_action = 'ask'
			
		self.close()
		
	def slot_search(self):
		self.search_string = unicode(self.search_lineEdit.displayText()).strip()
		self.close()