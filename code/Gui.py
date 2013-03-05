# coding: utf-8
# Copyright (C) 2012-2013 Itay Brandes

'''
PyQt4 GUI for the iQuality program
'''

import os
import sys
import re
import operator
import shutil
import subprocess
import traceback
import time
import math
import copy
import random
import warnings
from socket import error as SocketError
from urllib2 import URLError

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QAxContainer
from PyQt4.phonon import Phonon

import Main
import Config; config = Config.config
import logger
from logger import log
from Gui_Threads import GenericThread, SearchThread, DownloadThread, ArtistSearchThread, ArtistLookupThread, LyricsFulltextSearchThread
from GuiSubWindows import ID3Window, PostDownloadWindow, TracksExplorerWindow, ChartsExplorerWindow, SettingsWindow, HelpSearchWindow, ComponentFetcherWindow
from CustomExceptions import NoSpaceWarning, NoResultsException, NewerVersionWarning, NoInternetConnectionException, NoDnsServerException, NotSupportedFiletypeException, FileInUseException, YoutubeException, ComponentsFaultyWarning
import Hints
import utils
tr = utils.qt.tr

__version__ = Config.__version__
__date__ = Config.__date__
__author__ = 'Itay Brandes (Brandes.Itay@gmail.com)'

# from PyQt4 import QtCore; import pdb; QtCore.pyqtRemoveInputHook(); pdb.set_trace()

class MainWindow(QtGui.QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		
		self.resize(*config.mainWindow_resolution)
		self.setWindowTitle(config.windowTitle)
		self.setWindowIcon(QtGui.QIcon(r'pics\pokeball.png'))
		             
		self.artistsObjs = []
		self.songsObjs = []
			
		self.init_threads()
		self.init_menubar()
		self.init_widgets()
		
		_warnings = Main.sanity_check()
		for w in _warnings:
			if isinstance(w, NoSpaceWarning):
				QtGui.QMessageBox.warning(self, tr("Warning"), tr("There are less than 200MB available in drive %s (%.2fMB left). Application may not function properly.") % (w.drive, w.space/1024.0**2), QtGui.QMessageBox.Ok)
			if isinstance(w, NewerVersionWarning):
				QtGui.QMessageBox.information(self, tr("Information"), tr("A new version of iQuality is available (%s). Updates includes performance enhancements, bug fixes, new features and fixed parsers.<br />For the complete changes list, you can visit our <a href=\"%s\">facebook page</a>.<br /><br />You can grab it from the bottom box of the main window, or from the <a href=\"%s\">iQuality website</a>.") % (w.newest, config.facebook_page, config.website), QtGui.QMessageBox.Ok)
			if isinstance(w, ComponentsFaultyWarning):
				win = ComponentFetcherWindow.MainWin(w.components)
				win.exec_()
		
		### Caching
		if config.prefetch_charts:
			self.thread1.init(Main.WebParser.WebServices.parse_billboard)
			self.thread2.init(Main.WebParser.WebServices.parse_glgltz)
			self.thread4.init(Main.WebParser.WebServices.parse_chartscoil)
		
		if len(sys.argv) > 1 and sys.argv[1]:
			if sys.argv[1] in ['-c', '--config', '/config']:
				self.settingsWindow_slot()
				sys.exit()
			elif sys.argv[1] in ['/test']: #TEMP
				# progress = QtGui.QProgressDialog("Copying files...", "Abort Copy", 0, 8)
				# progress.setWindowModality(QtCore.Qt.WindowModal)
				
				# for i in range(0,8):
					# progress.setValue(i)
					# QtGui.QApplication.processEvents()
					# time.sleep(1)
			
			
			
				w = ComponentFetcherWindow.MainWin()
				w.exec_()
				# sys.exit()
			else:
				self.search_lineEdit.setText(unicode(sys.argv[1], sys.getfilesystemencoding()))
				if len(sys.argv) > 2 and sys.argv[2] and sys.argv[2] in ['-l', '--lucky', '/lucky', '-d', '--download', '/dl' , '/download']:
					log.debug("Setting luckyMode to True")
					self.search_slot(luckyMode=True)
				else:
					self.search_slot()
		elif config.parse_links_from_clipboard_at_startup:
			clipboard = QtGui.QApplication.clipboard()
			x = unicode(clipboard.text())

			if 'youtube.com' in x.lower() or 'youtu.be' in x.lower() or 'soundcloud.com' in x.lower():
				self.search_lineEdit.setText(x)
				self.search_slot()
	
	def reload_thread(self, thread, do_log=True):
		'''
		Terminates and then creating a new thread on the same object name.
		paramter "thread" must be a string.
		'''
		if do_log:
			log.debug("Terminating and restarting thread \"%s\"..." % thread)
		eval("self." + thread).terminate()
		self.init_threads([thread])
	
	def init_threads(self, threads=None):
		"initialize application threads"
		if not threads:
			threads = ['thread1', 'thread2', 'thread3', 'thread4', 'search_thread', 'dl_thread',
						'artist_search_thread', 'artist_album_thread', 'lyrics_fulltext_thread',
						'autocomplete_thread']
		
		if 'thread1' in threads:
			self.thread1 = GenericThread()
			
		if 'thread2' in threads:
			self.thread2 = GenericThread()
			
		if 'thread3' in threads:
			self.thread3 = GenericThread()
			self.thread3.error.connect(self.error_slot)
			self.thread3.finished.connect(self.disableStatusGif)
			
		if 'thread4' in threads:
			self.thread4 = GenericThread()
			
		if 'autocomplete_thread' in threads:
			self.autocomplete_thread = GenericThread(log_succ=False)
			self.autocomplete_thread.output.connect(self.slot_autocomplete_done)
			
		if 'search_thread' in threads:
			self.search_thread = SearchThread()
			self.search_thread.output.connect(self.update_search_results)
			self.search_thread.error.connect(self.error_slot)
			self.search_thread.finished_lucky.connect(self.search_thread_finished_lucky)
			self.search_thread.finished.connect(self.search_thread_finished)
			
		if 'dl_thread' in threads:
			self.dl_thread = DownloadThread()
			self.dl_thread.downloadProgress.connect(self.update_dl_progress_bar)
			self.dl_thread.encProgress.connect(self.update_enc_progress_bar)
			self.dl_thread.status.connect(self.updateStatusBar)
			self.dl_thread.error.connect(self.error_slot)
			self.dl_thread.finished.connect(self.dl_thread_and_id3_window_finished)
			
		if 'artist_search_thread' in threads:
			self.artist_search_thread = ArtistSearchThread()
			self.artist_search_thread.output.connect(self.fetch_tracks_init_data)
			
		if 'artist_album_thread' in threads:
			self.artist_album_thread = ArtistLookupThread()
			self.artist_album_thread.output.connect(self.launch_tracks_explorer)
			
		if 'lyrics_fulltext_thread' in threads:
			self.lyrics_fulltext_thread = LyricsFulltextSearchThread()
			self.lyrics_fulltext_thread.output.connect(self.slot_lyrics_fulltext)
	
	def init_menubar(self):
		"initialize application menubar"
		# File Menu
		fileMenu = self.menuBar().addMenu(tr('File'))
		id3Action = QtGui.QAction(QtGui.QIcon(r'pics\id3edit.png'), tr('ID3 Editor'), self)        
		id3Action.setStatusTip(tr('Edit ID3'))
		id3Action.triggered.connect(self.id3Window_slot)
		exitAction = QtGui.QAction(QtGui.QIcon(r'pics\cancel.png'), tr('Exit'), self)
		exitAction.setStatusTip(tr('Exit application'))
		exitAction.triggered.connect(QtGui.qApp.quit)
		fileMenu.addAction(id3Action)
		fileMenu.addSeparator()
		fileMenu.addAction(exitAction)
		
		# Tools Menu
		toolsMenu = self.menuBar().addMenu(tr('Tools'))
		rand_act = QtGui.QAction(QtGui.QIcon(r'pics\dice.png'), tr('Pick up a random song'), self)
		rand_act.triggered.connect(self.randomSong_slot)
		chart_act = QtGui.QAction(QtGui.QIcon(r'pics\charts.png'), tr('Choose songs from top charts'), self)
		chart_act.triggered.connect(self.chartsFetch_slot)
		opendir_act = QtGui.QAction(QtGui.QIcon(r'pics\folder.png'), tr('Open downloaded files folder'), self)
		opendir_act.triggered.connect(self.slot_opendir)
		
		toolsMenu.addAction(rand_act)
		toolsMenu.addAction(chart_act)
		toolsMenu.addAction(opendir_act)
		
		# Settings Menu
		settingsMenu = self.menuBar().addMenu(tr('Settings'))
		act = QtGui.QAction(QtGui.QIcon(r'pics\settings.png'), tr('Preferences'), self)
		act.setStatusTip(tr("Configure iQuality's behavior"))
		act.triggered.connect(self.settingsWindow_slot)
		settingsMenu.addAction(act)
		
		# Languages Menu
		langMenu = self.menuBar().addMenu(tr('Languages'))
		# langMenu = settingsMenu.addMenu(tr('Languages'))
		actus = QtGui.QAction(QtGui.QIcon(r'pics\flag-us.png'), tr('English'), self)
		actus.setStatusTip(tr("English"))
		actus.triggered.connect(self.lang_en_slot)
		actil = QtGui.QAction(QtGui.QIcon(r'pics\flag-il.png'), tr('Hebrew'), self)
		actil.setStatusTip(tr("Hebrew"))
		actil.triggered.connect(self.lang_he_slot)
		langMenu.addAction(actus)
		langMenu.addAction(actil)
		
		# Help Menu
		helpMenu = self.menuBar().addMenu(tr('Help'))
		act_help = QtGui.QAction(QtGui.QIcon(r'pics\support.png'), tr('Search Field Help'), self)
		act_help.setStatusTip(tr('Search Field Help'))
		act_help.triggered.connect(self.helpSearch_slot)
		act_logfile = QtGui.QAction(QtGui.QIcon(r'pics\file_broken.png'), tr('Open Log File'), self)
		act_logfile.setStatusTip(tr('Open Log File'))
		act_logfile.triggered.connect(self.logfile_slot)
		act_credits = QtGui.QAction(QtGui.QIcon(r'pics\pokeball.png'), tr('About'), self)
		act_credits.setStatusTip(tr('Show Credits'))
		act_credits.triggered.connect(self.creditsWindow_slot)
		act_website = QtGui.QAction(QtGui.QIcon(r'pics\world.png'), tr('Visit our website'), self)
		act_website.setStatusTip(tr('Visit our website'))
		act_website.triggered.connect(self.visitWebsite_slot)
		act_facebook = QtGui.QAction(QtGui.QIcon(r'pics\facebook.png'), tr('Visit our facebook page'), self)
		act_facebook.setStatusTip(tr('Visit our facebook page'))
		act_facebook.triggered.connect(self.visit_facebook_slot)
		
		helpMenu.addAction(act_help)
		helpMenu.addAction(act_logfile)
		helpMenu.addSeparator()
		helpMenu.addAction(act_credits)
		helpMenu.addAction(act_website)
		helpMenu.addAction(act_facebook)
		
		# Image Push Buttons
		helpSearch_button = QtGui.QPushButton(QtGui.QIcon(r'pics\support.png'), "")
		helpSearch_button.clicked.connect(self.helpSearch_slot)
		helpSearch_button.setFlat(True)
		helpSearch_button.setToolTip(tr('Search Field Help'))
		charts_button = QtGui.QPushButton(QtGui.QIcon(r'pics\charts.png'), "")
		charts_button.clicked.connect(self.chartsFetch_slot)
		charts_button.setFlat(True)
		charts_button.setToolTip(tr('Choose songs from top charts'))
		opendir_button = QtGui.QPushButton(QtGui.QIcon(r'pics\folder.png'), "")
		opendir_button.clicked.connect(self.slot_opendir)
		opendir_button.setFlat(True)
		opendir_button.setToolTip(tr('Open downloaded files folder'))
		rand_button = QtGui.QPushButton(QtGui.QIcon(r'pics\dice.png'), "")
		rand_button.clicked.connect(self.randomSong_slot)
		rand_button.setFlat(True)
		rand_button.setToolTip(tr('Pick up a random song'))
		facebook_button = QtGui.QPushButton(QtGui.QIcon(r'pics\facebook.png'), "")
		facebook_button.clicked.connect(self.visit_facebook_slot)
		facebook_button.setFlat(True)
		facebook_button.setToolTip(tr('Visit our facebook page'))
		
		# Environment Setup
		menuPushButtonsWidget = QtGui.QWidget()
		menuPushButtonsWidget.setLayoutDirection(QtGui.QApplication.layoutDirection() ^ 1) # doing xor on Qt.LayoutDirection
		buttonsLayout = QtGui.QHBoxLayout(menuPushButtonsWidget)
		buttonsLayout.setContentsMargins(0, 0, 0, 0)
		buttonsLayout.setSpacing(0)
		
		buttonsLayout.addSpacerItem(QtGui.QSpacerItem(10, 1))
		buttonsLayout.addWidget(helpSearch_button)
		buttonsLayout.addSpacerItem(QtGui.QSpacerItem(15, 1))
		buttonsLayout.addWidget(rand_button)
		buttonsLayout.addWidget(charts_button)
		buttonsLayout.addWidget(opendir_button)
		buttonsLayout.addSpacerItem(QtGui.QSpacerItem(15, 1))
		buttonsLayout.addWidget(facebook_button)
		
		self.menuBar().setCornerWidget(menuPushButtonsWidget)
		
	def id3Window_slot(self):
		dialog = QtGui.QFileDialog()
		dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
		f = unicode(dialog.getOpenFileName(caption=tr('Choose the mp3 file'), filter="MP3 file (*.mp3)"))
		if f:
			log.debug('Changing ID3 data for %s' % f)
			w = ID3Window.MainWin(f, 'ask_albumart')
			if w.isValid:
				w.exec_()
				if hasattr(w, 'ID3TagsToEdit'):
					utils.setID3Tags(w.ID3TagsToEdit, f)
					self.updateStatusBar(tr('ID3 Data has been saved successfully.'))
	
	def settingsWindow_slot(self):
		w = SettingsWindow.MainWin()
		w.exec_()
		
		self.downloadAudio_checkbox.setCheckState(config.downloadAudio)
		self.downloadAudio_checkbox.setTristate(False)
		self.downloadVideo_checkbox.setCheckState(config.downloadVideo)
		self.downloadVideo_checkbox.setTristate(False)
		
	def lang_en_slot(self):
		self.lang_slot('en_US')
		
	def lang_he_slot(self):
		self.lang_slot('he_IL')
		
	def lang_slot(self, lang):
		if not lang in config.lang_rtl.keys():
			log.error('lang_slot: no such lang "%s".' % lang)
			return
		if config.lang == lang:
			log.debug('lang_slot: config.lang is already "%s".' % lang)
			QtGui.QMessageBox.information(self, tr("Language Package Setting"), tr("The selected language is already installed."), QtGui.QMessageBox.Ok)
			return

		log.debug('Setting language as %s' % lang)
		config.lang = lang
		log.debug('Restarting application...')
		self.closeEvent()
		QtCore.QCoreApplication.exit(1000) # 1000 is the RESTART code
		
	def creditsWindow_slot(self):
		QtGui.QMessageBox.information(self, tr("About"), config.credits_text, QtGui.QMessageBox.Ok)
	
	def visitWebsite_slot(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(config.website))
		
	def visit_facebook_slot(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(config.facebook_page))
		
	def logfile_slot(self):
		os.startfile(config.logfile_path)
		
	def init_widgets(self):
		"initialize application widgets"
		mainLayout = QtGui.QGridLayout()
		
		self.label1 = QtGui.QLabel(tr("Song name or url:"))
		self.search_lineEdit = QtGui.QLineEdit()
		self.search_lineEdit.setPlaceholderText(tr("Type a song name or url."))
		self.search_lineEdit.returnPressed.connect(self.search_slot)
		self.search_lineEdit.textEdited.connect(self.slot_autocomplete)
		self.search_button = QtGui.QPushButton(tr("Search"))
		self.search_button.clicked.connect(self.search_slot)
		self.search_cancel_button = QtGui.QPushButton(QtGui.QIcon(r'pics\cancel.png'), "")
		self.search_cancel_button.clicked.connect(self.cancel_search_slot)
		self.search_cancel_button.setEnabled(False)
		self.search_cancel_button.setFlat(True)
		self.search_cancel_button.setToolTip(tr('Stop search process'))
		
		self.table = QtGui.QTableView()
		self.table.setShowGrid(False)
		self.table.setFont(QtGui.QFont(*config.table_font))
		self.table.setSelectionBehavior(QtGui.QTableView.SelectRows)
		self.table.setSelectionMode(QtGui.QTableView.SingleSelection)
		self.table.setSortingEnabled(True)
		self.table.horizontalHeader().setStretchLastSection(True)
		self.table.verticalHeader().setVisible(False)
		self.table.verticalHeader().setDefaultSectionSize(config.table_DefaultSectionSize)
		self.table.resizeColumnsToContents()
		self.table.setStyleSheet(config.table_styleSheet)
		self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.table.customContextMenuRequested.connect(self.table_rightclick_popup)
		self.table.doubleClicked.connect(self.table_doubleClicked_slot)
		
		header = [tr('Title'), tr('Artist'), tr('Bitrate'), tr('Video Size (MB)'), 
					tr('Audio Size (MB)'), tr('Length'), tr('Relevance'), tr('Source'),
					tr('URL')]
					
		self.tableModel = MyTableModel([], header, self)
		self.table.setModel(self.tableModel)
		
		self.table.setColumnWidth(0, 200) # title
		self.table.setColumnWidth(1, 95) # artist
		self.table.setColumnWidth(2, 58) # bitrate
		self.table.setColumnWidth(5, 47) # length
		self.table.setColumnWidth(7, 75) # source
	
		self.listen_button = QtGui.QCommandLinkButton(tr("Listen"))
		self.listen_button.clicked.connect(self.listen_slot)
		self.listen_pause_button = QtGui.QPushButton(QtGui.QIcon(r'pics\pause.png'), "")
		self.listen_pause_button.clicked.connect(self.playpause_slot)
		self.listen_pause_button.setEnabled(False)
		self.listen_pause_button.setFlat(True)
		self.listen_pause_button.setToolTip(tr('Pause/Continue media player'))
		self.mediaSlider = Phonon.SeekSlider()
		self.mediaVolumeSlider = Phonon.VolumeSlider()
		self.mediaVolumeSlider.setMaximumSize(90, 40)
		self.mediaTimer = QtGui.QLabel()
		self.mediaTimer.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
		
		self.dl_button = QtGui.QCommandLinkButton(tr("Download"))
		# self.dl_button.setMaximumSize(100, 40)
		self.dl_button.clicked.connect(self.download_slot)
		self.dl_cancel_button = QtGui.QPushButton(QtGui.QIcon(r'pics\cancel.png'), "")
		self.dl_cancel_button.clicked.connect(self.cancel_download_slot)
		self.dl_cancel_button.setEnabled(False)
		self.dl_cancel_button.setFlat(True)
		self.dl_cancel_button.setToolTip(tr('Stop the download process'))
		self.prg_bar = QtGui.QProgressBar()
		
		self.downloadAudio_checkbox = QtGui.QCheckBox(tr("Audio"))
		self.downloadAudio_checkbox.setCheckState(config.downloadAudio)
		self.downloadAudio_checkbox.setTristate(False)
		self.downloadAudio_checkbox.stateChanged.connect(self.slot_downloadAudio_changed_checkbox)
		self.downloadVideo_checkbox = QtGui.QCheckBox(tr("Video (If exists)"))
		self.downloadVideo_checkbox.setCheckState(config.downloadVideo)
		self.downloadVideo_checkbox.setTristate(False)
		self.downloadVideo_checkbox.stateChanged.connect(self.slot_downloadVideo_changed_checkbox)
		
		self.status_txt = QtGui.QLabel(Hints.get_hints())
		self.status_txt.setFont(QtGui.QFont(*config.status_txt_font))
		self.status_gif = QtGui.QLabel()
		self.movie = QtGui.QMovie(r"pics\loading.gif")
		self.status_gif.setMovie(self.movie)
		self.movie.start()
		self.status_gif.setVisible(False)
		
		if config.show_ads:
			url = config.browser_website.format(config.lang[:2])
			self.browser = QAxContainer.QAxWidget()
			self.browser.setControl("{8856F961-340A-11D0-A96B-00C04FD705A2}")
			self.browser.dynamicCall('Navigate(const QString&)', url)
			self.browser.setFixedHeight(config.browser_height)
		
		try:
			users_online_count = Main.WebParser.WebServices.get_currentusers()
		except (SocketError, URLError):
			log.error("Failed to get current users number (WebParser.WebServices.get_currentusers)")
			users_online_count = 0
		if users_online_count:
			self.label5 = QtGui.QLabel(tr(u"iQuality© v%s beta by Itay Brandes (%s). The software has been launched %s times, and downloaded %s songs. %s user(s) are currently using the software.") % (__version__, __date__, format(config.count_application_runs, ',d'), format(config.count_download, ',d'), format(users_online_count, ',d')))
		else:
			self.label5 = QtGui.QLabel(tr(u"iQuality© v%s beta by Itay Brandes (%s). The software has been launched %s times, and downloaded %s songs.") % (__version__, __date__, format(config.count_application_runs, ',d'), format(config.count_download, ',d')))
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		row1_Layout = QtGui.QHBoxLayout()
		row1_Layout.addWidget(self.label1)
		row1_Layout.addWidget(self.search_lineEdit)
		row1_Layout.addWidget(self.search_button)
		row1_Layout.addWidget(self.search_cancel_button)
		# row1_Layout.addWidget(self.helpSearch_button)
		# row1_Layout.addWidget(self.charts_button)
		
		mainLayout.addLayout(row1_Layout, 1, 0, 1, 3)
		mainLayout.addWidget(self.table, 2, 0, 1, 0)
		
		videoaudio_checkboxs_Layout = QtGui.QVBoxLayout()
		videoaudio_checkboxs_Layout.addWidget(self.downloadAudio_checkbox)
		videoaudio_checkboxs_Layout.addWidget(self.downloadVideo_checkbox)
		
		row_5_6_Layout = QtGui.QGridLayout()
		# row_5_6_Layout.addWidget(self.listen_button, 0, 0, 1, 2)
		row_5_6_Layout.addWidget(self.listen_button, 0, 0)
		row_5_6_Layout.addWidget(self.mediaVolumeSlider, 0, 1)
		row_5_6_Layout.addWidget(self.listen_pause_button, 0, 2)
		row_5_6_Layout.addWidget(self.mediaSlider, 0, 3)
		row_5_6_Layout.addWidget(self.mediaTimer, 0, 4)
		row_5_6_Layout.addWidget(self.dl_button, 1, 0)
		row_5_6_Layout.addLayout(videoaudio_checkboxs_Layout, 1, 1)
		row_5_6_Layout.addWidget(self.dl_cancel_button, 1, 2)
		row_5_6_Layout.addWidget(self.prg_bar, 1, 3, 1, 2)

		row7_Layout = QtGui.QHBoxLayout()
		row7_Layout.addWidget(self.status_txt)
		row7_Layout.addWidget(self.status_gif)
		
		mainLayout.addLayout(row_5_6_Layout, 5, 1, 2, 1)
		mainLayout.addLayout(row7_Layout, 7, 0, 1, 5, QtCore.Qt.AlignCenter)
		if config.show_ads:
			mainLayout.addWidget(self.browser, 8, 0, 1, 5)
		mainLayout.addWidget(self.label5, 9, 0, 1, 0)
		central_widget = QtGui.QWidget()
		central_widget.setLayout(mainLayout)
		self.setCentralWidget(central_widget)
		
	### SLOTS ###
	def slot_autocomplete(self, s):
		if config.search_autocomplete and s:
			self.autocomplete_thread.init(Main.WebParser.WebServices.google_autocomplete, unicode(s))
		
	def slot_autocomplete_done(self, words):
		completer = QtGui.QCompleter(words, self)
		completer.setCompletionMode(QtGui.QCompleter.InlineCompletion)
		self.search_lineEdit.setCompleter(completer)
		
	def slot_opendir(self):
		log.debug('Running explorer "%s"...' % config.dl_dir)
		os.startfile(config.dl_dir)
		
	def chartsFetch_slot(self):
		w = ChartsExplorerWindow.MainWin()
		w.exec_()
		
		if hasattr(w, 'output'):
			self.search_lineEdit.setText(w.output)
			self.search_slot(spellCheck=False, ArtistLookup=False)
		
	def randomSong_slot(self, luckyMode=False):
		if self.search_thread.isRunning(): # if another search task already runs, just terminate it
			self.reload_thread('search_thread')
			
		if (config.lang == 'he_IL' and random.randint(0, 1)) or config.lang != 'he_IL':
			try:
				hot_100_chart = Main.WebParser.WebServices.parse_billboard()[:50]
				song = hot_100_chart[random.randint(0, len(hot_100_chart)-1)]
			except Exception, e:
				log.error("error in parse_billboard: %s" % unicode(e))
				
		else:
			try:
				hot_heb_24 = Main.WebParser.WebServices.parse_glgltz()[:20]
				song = hot_heb_24[random.randint(0, len(hot_heb_24)-1)]
			except Exception, e:
				log.error("error in parse_glgltz: %s" % unicode(e))
				try:
					hot_heb_20 = Main.WebParser.WebServices.parse_chartscoil()[:20]
					song = hot_heb_20[random.randint(0, len(hot_heb_20)-1)]
				except Exception, e:
					log.error("error in parse_chartscoil: %s" % unicode(e))
					try:
						hot_100_chart = Main.WebParser.WebServices.parse_billboard()[:50]
						song = hot_100_chart[random.randint(0, len(hot_100_chart)-1)]
					except Exception, e:
						log.error("error in parse_billboard: %s" % unicode(e))
			
		self.search_lineEdit.setText(song)
		self.search_slot(spellCheck=False, luckyMode=luckyMode)
		
	def helpSearch_slot(self):
		w = HelpSearchWindow.MainWin()
		w.exec_()
		
	def search_slot(self, spellCheck=None, luckyMode=False, ArtistLookup=None):
		self.search_starttime = time.time()
		
		if spellCheck is None:
			spellCheck = config.enableSpellCheck
		if ArtistLookup is None:
			ArtistLookup = config.artist_lookup
		isUrl = False
		song = unicode(self.search_lineEdit.displayText().toUtf8(), "utf-8").strip()
			
		modifiers = QtGui.QApplication.keyboardModifiers()
		if modifiers == QtCore.Qt.ShiftModifier: # if user pressed shift
			log.debug("User pressed shift. setting luckymode to True")
			luckyMode = True
		
		if not song:
			log.debug("User inserted blank field. running randomSong_slot()")
			self.randomSong_slot(luckyMode)
			return

		if self.search_thread.isRunning():
			self.reload_thread('search_thread')
		if self.artist_search_thread.isRunning():
			self.reload_thread('artist_search_thread')
		if self.lyrics_fulltext_thread.isRunning():
			self.reload_thread('lyrics_fulltext_thread')
		
		while "  " in song:
			song = song.replace('  ', ' ')
			self.search_lineEdit.setText(song)
		
		if song.startswith('http://') or song.startswith('https://') or song.startswith('ftp://'):
			log.debug("search string is a url")
			isUrl = True
		
		elif spellCheck:
			self.search_suggestion = Main.WebParser.WebServices.spell_fix(song)
			if self.search_suggestion.lower() != song.lower():
				if luckyMode:
					song = self.search_suggestion
					self.search_lineEdit.setText(song)
				else:
					ans = QtGui.QMessageBox.question(self, tr("Spelling Suggestion"), tr('Did you mean %s?') % utils.append_bold_changes(song, self.search_suggestion), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
					if ans == QtGui.QMessageBox.Yes:
						song = self.search_suggestion
						self.search_lineEdit.setText(song)
		
		if luckyMode:
			self.updateStatusBar(tr("Searching for %s in LuckyMode...") % song)
		else:
			self.updateStatusBar(tr("Searching for %s...") % song)
		self.status_gif.setVisible(True)
				
		if not luckyMode and not isUrl:
			self.searchString = song
			if config.lyrics_lookup and len(song) >= 22 and '-' not in song: # already contains ArtistLookup in it
				self.lyrics_fulltext_thread.search(self.searchString)
			elif ArtistLookup:
				self.artist_search_thread.search(self.searchString)
		
		self.tableModel.clearTable()
		self.songsObjs = []
		self.search_cancel_button.setEnabled(True)
		self.search_thread.search(song, config.songs_count_spinBox, luckyMode)
			
	def cancel_search_slot(self):
		self.reload_thread('search_thread')
		log.debug("Search task was canceled.")
		self.status_txt.setText(tr("Task was canceled."))
		self.enableSearchUi()
	
	def cancel_download_slot(self):
		self.reload_thread('dl_thread')
		log.debug("Download task was canceled.")
		self.status_txt.setText(tr("Task was canceled."))
		self.finished_signals_count = 0
		self.enableDownloadUi()
		
	def listen_slot(self, QModelIndex=None):
		if config.warn_listen_slot:
			QtGui.QMessageBox.warning(self, tr("Warning"), tr("The listening feature is experimental and may not work properly."), QtGui.QMessageBox.Ok)
			config.warn_listen_slot = False
		
		if self.table.selectedIndexes():
			index = self.table.selectedIndexes()[0]
		else:
			QtGui.QMessageBox.critical(self, tr("Error"), tr("Please choose a song."), QtGui.QMessageBox.Ok)
			return
		
		url = str(index.data(QtCore.Qt.UserRole).toString())
		songObj = [x for x in self.songsObjs if x.url == url][0]
		
		if hasattr(self, 'player'):
			log.debug("Stopping audio player...")
			self.player.clear()
			try:
				self.player.tick.disconnect()
			except TypeError:
				pass
			
		if songObj.source == "youtube":
			ans = Main.WebParser.LinksGrabber.get_youtube_dl_link(songObj.youtube_videoid,
													config.youtube_listen_quality_priority,
													config.youtube_listen_formats_priority)
			if not ans:
				QtGui.QMessageBox.critical(self, tr("Error"), tr('Sorry, a preview is not available for this video. You can watch it on <a href="%s">youtube</a>.') % songObj.youtube_watchurl, QtGui.QMessageBox.Ok)
				return
				
			url = ans.url

		log.debug("Starting audio player (%s)..." % url)
		
		mediaSource = Phonon.MediaSource(url) # creates a media source
		mediaSource.setAutoDelete(True)
		audioOutput = Phonon.AudioOutput(Phonon.MusicCategory) # create an audio output device
		audioOutput.setVolume(config.listen_volumeSlider_volume)
		audioOutput.volumeChanged.connect(self.volumeChanged_slot)
		
		self.player = Phonon.MediaObject() # creates the audio handler
		self.player.setCurrentSource(mediaSource) # loads the media source in the audio handler
		
		Phonon.createPath(self.player, audioOutput) # links the audio handler and the audio output device
		
		self.player.setTickInterval(100)
		self.player.tick.connect(self.updatePlayerLength)
		self.mediaSlider.setMediaObject(self.player)
		self.mediaVolumeSlider.setAudioOutput(audioOutput)
		
		self.player.play()
		
		self.listen_pause_button.setIcon(QtGui.QIcon(r'pics\pause.png'))
		self.listen_pause_button.setEnabled(True)
	
	def volumeChanged_slot(self, val):
		if val > 0.3:
			config.listen_volumeSlider_volume = val
		
	def playpause_slot(self):
		if self.player.state() == Phonon.PlayingState:
			self.player.pause()
			self.listen_pause_button.setIcon(QtGui.QIcon(r'pics\play.png'))
		else:
			self.player.play()
			self.listen_pause_button.setIcon(QtGui.QIcon(r'pics\pause.png'))
	
	def download_slot(self, QModelSearch=None, songObj=None, luckyMode=False):
		if not config.downloadAudio and not config.downloadVideo:
			QtGui.QMessageBox.critical(self, tr("Error"), tr("You've configured the application to download neither audio nor video files. You must choose at least one of them."), QtGui.QMessageBox.Ok)
			return
		
		if not songObj:
		# Check if user has choosen a song
			if self.table.selectedIndexes():
				index = self.table.selectedIndexes()[0]
			else:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Please choose a song."), QtGui.QMessageBox.Ok)
				return
			
			# retriving url and deep-copying songobj
			url = str(index.data(QtCore.Qt.UserRole).toString())
			self.songObj = [x for x in self.songsObjs if x.url == url][0]
			self.songObj = copy.deepcopy(self.songObj)
		else:
			self.songObj = copy.deepcopy(songObj)
		
		# if downloading audio but not video from youtube, we should always prefer the 720p version, as the audio stream bitrates are equal between 720p and 1080p.
		if self.songObj.source == "youtube" and config.downloadAudio and not config.downloadVideo:
			priority = config.youtube_quality_priority[:]
			if self.songObj.video_itag.quality == 'hd1080' and 'hd1080' in priority and 'hd720' in priority:
				priority.remove('hd1080')
				metaUrl = Main.WebParser.LinksGrabber.get_youtube_dl_link(self.songObj.youtube_videoid, priority)
				self.songObj.url = metaUrl.url
				self.songObj.itag = metaUrl.itag
				old_filesize = self.songObj.filesize
				self.songObj.filesize = Main.HTTPQuery.get_filesize(self.songObj.url)
				
				log.debug("User downloads audio only from youtube. downloads 720p instead of 1080p (%.2f MB instead of %.2f MB)" % (self.songObj.filesize/1024.0**2, old_filesize/1024.0**2))
		
		# Deleting id3 data, if exists from last songs. IMPROVE: make sure this gets deleted on the end of each download.
		if hasattr(self, 'ID3TagsToEdit'):
			del self.ID3TagsToEdit
		isMultimediaFile = False if "non-multimedia" in self.songObj.source.lower() else True
		
		# validating dl_dir
		if not re.search(r'^([a-zA-Z]:)?(\\[^<>:"/\\|?*]+)+\\?$', config.dl_dir): # valid path regex
				QtGui.QMessageBox.critical(self, tr("Error"), tr("The filename, directory name, or volume label syntax is incorrect. Please specify a valid download directory."), QtGui.QMessageBox.Ok)
				return
				
		elif not os.path.exists(config.dl_dir):
			ans = QtGui.QMessageBox.question(self, tr("Information"), tr('Download directory "%s" does not exist. Create it?') % config.dl_dir, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
			if ans == QtGui.QMessageBox.No:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Please specify a valid directory."), QtGui.QMessageBox.Ok)
				return
			else:
				try:
					os.makedirs(config.dl_dir)
				except WindowsError, e:
					QtGui.QMessageBox.critical(self, tr("Error"), tr("Error %d: %s.") % (int(e[0]), e[1]), QtGui.QMessageBox.Ok)
					return

		config.count_download += 1
		
		# making dest_paths
		dest_paths = []
		if not isMultimediaFile:
			dest_paths.append(r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename()))
		if config.downloadAudio:
			dest_paths.append(r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename('mp3')))
		if config.downloadVideo and self.songObj.source == "youtube":
			dest_paths.append(r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename()))
		if not dest_paths:
			log.error("Error: I got nothing to download!")
			if not self.songObj.source == "youtube" and not config.downloadAudio and config.downloadVideo:
				# if url is not youtube, however user seeks only video
				QtGui.QMessageBox.critical(self, tr("Error"), tr("This song has no video available. Please check the audio checkbox, or choose a different song."))
			else:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("I got nothing to download! The link doesn't have the mediatype that the application is set for (downloadVideo: %s, downloadAudio: %s). This can be changed in the settings window.") % (config.downloadVideo, config.downloadAudio), QtGui.QMessageBox.Ok)
			return
		
		# validating overwrites, validate only if we are not in a lucky mode
		if not luckyMode:
			for path in dest_paths:
				if os.path.exists(path): # If final file already exists
					ans = QtGui.QMessageBox.question(self, tr("Information"), tr('File "%s" already exists. Overwrite it?') % path, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
					if ans == QtGui.QMessageBox.No:
						dialog = QtGui.QFileDialog()
						dialog.setDirectory(config.dl_dir)
						ans = unicode(dialog.getSaveFileName(caption=tr("Choose a new filename for %s") % path).replace('/','\\'))
						if not ans:
							break
						config.dl_dir, dl_filename = os.path.split(ans)
						
						log.debug('dl_dir is now %s' % config.dl_dir)
						self.songObj.constantFileName = dl_filename
						break
					
		
		self.updateStatusBar(tr("Starting Download..."))

		# Disable Ui
		self.downloadAudio_checkbox.setEnabled(False)
		self.downloadVideo_checkbox.setEnabled(False)
		self.dl_button.setEnabled(False)
		self.dl_cancel_button.setEnabled(True)
		self.status_gif.setVisible(True)
		
		# Reset finished_signals_count. dl_thread and SetID3Window will both report
		# when they are finished by increasing this var. when this var reaches two, the
		# ID3 tags will be appended to the .mp3 file, and it will be run.
		self.finished_signals_count = 0
	
		# Run download thread
		self.dl_thread.download(self.songObj, config.dl_dir)
		
		# Run ID3 Tags Window
		if isMultimediaFile and config.downloadAudio and config.editID3:
			if luckyMode:
				w = ID3Window.MainWin(self.songObj.id3tags_file, 'noask')
			else:
				w = ID3Window.MainWin(self.songObj.id3tags_file)
				
			if w.isValid:
				w.exec_()
				self.ID3TagsToEdit = w.ID3TagsToEdit if hasattr(w, 'ID3TagsToEdit') else ""
				
			# run the dl_thread finished slot so the data will be appended and the file will be run.
			self.dl_thread_and_id3_window_finished() # mimics a FINISHED signal emit.
			
	def table_doubleClicked_slot(self, index):
		if config.table_doubleClick_action == 'listen':
			self.listen_slot(index)
		if config.table_doubleClick_action == 'download':
			self.download_slot(index)
		
	def error_slot(self, e):
		"Error slot for the error signal"
		if isinstance(e, NotSupportedFiletypeException):
			QtGui.QMessageBox.critical(self, tr("Error"), tr('The application does not support the %s filetype.') % e.ext, QtGui.QMessageBox.Ok)
			
		elif isinstance(e, NoResultsException):
			if e.isDirectLink:
				QtGui.QMessageBox.critical(self, tr("Error"), tr('There is a network problem: The address may be incorrect, or your internet connection got terminated. Please try again later.'), QtGui.QMessageBox.Ok)
			elif not all(config.search_sources.values()):
				disabled_search_sources = [k for k, v in config.search_sources.items() if not v]
				log.debug('some media sources are disabled (%s). asking user if he wants to enable them...' % ", ".join(disabled_search_sources))
				ans = QtGui.QMessageBox.critical(self, tr("Error"), tr('No songs were found. Also, some media sources are disabled (%s). Enable them and search again?') % ", ".join(disabled_search_sources), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
				if ans == QtGui.QMessageBox.Yes:
					log.debug("Enabling all media sources...")
					for k in config.search_sources.keys():
						config.search_sources[k] = True
					self.search_slot()
					return
			else:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("No songs were found."), QtGui.QMessageBox.Ok)
			self.status_txt.setText(tr("No songs were found."))
		
		elif isinstance(e, FileInUseException):
			QtGui.QMessageBox.critical(self, tr("Error"), tr("The process cannot access the file %s because it is being used by another process.") % e.f, QtGui.QMessageBox.Ok)
			
		elif isinstance(e, YoutubeException):
			QtGui.QMessageBox.critical(self, tr("Error"), tr("The application was unable to fetch the Youtube video. (Error %d: %s)") % (e.errorcode, e.reason), QtGui.QMessageBox.Ok)
			
		# elif isinstance(e, Exception):
			# pass
			
		else:
			s = "Unhandled exception: %s" % unicode(e)
			log.error(s)
			QtGui.QMessageBox.critical(self, tr("Error"), s, QtGui.QMessageBox.Ok)
		
		self.enableSearchUi()
		self.enableDownloadUi()
		
	def slot_downloadAudio_changed_checkbox(self, state):
		# IMPROVE: These two can be combined
		if state == 0:
			config.downloadAudio = False
		if state == 2:
			config.downloadAudio = True
			
	def slot_downloadVideo_changed_checkbox(self, state):
		# IMPROVE: These two can be combined
		if state == 0:
			config.downloadVideo = False
		if state == 2:
			config.downloadVideo = True
		
	### THREAD FINISHED FUNCTIONS ###
	
	def search_thread_finished(self):
		"Will run when search_thread will return a FINISHED signal."
		if self.search_thread._terminated:
			return
			
		log.debug("The search task is done within %.2f seconds." % (time.time()-self.search_starttime))
		self.status_txt.setText(tr("The search task is done."))
		self.enableSearchUi()
	
	def search_thread_finished_lucky(self):
		log.debug("Lucky Mode!")
		l = sorted(self.songsObjs, key=lambda x: x.score, reverse=True)
		l = [x for x in l if x.score == l[0].score]
		best = sorted(l, key=lambda x: x.filesize)[0]
		self.table.selectRow(self.songsObjs.index(best))
		self.download_slot(songObj=best, luckyMode=True)
	
	def dl_thread_and_id3_window_finished(self):
		"Will run when dl_thread and id3_window both return a FINISHED signal."
		if self.dl_thread._terminated:
			return
			
		isMultimediaFile = False if "non-multimedia" in self.songObj.source.lower() else True
			
		if isMultimediaFile and config.downloadAudio and config.editID3:
			self.finished_signals_count += 1
			if self.finished_signals_count == 2:
				log.debug('finished_signals_count is 2.')
				try:
					self.setID3Tags()
				except:
					log.warning("got self.setID3Tags() error, skipping...")
					log.error(traceback.format_exc())
				self.renameFilesByID3()
			else:
				log.debug('finished_signals_count is 1. dl_thread OR id3_window are done. Waiting for the other to continue...')
				return
				
		self.enableDownloadUi()
		self.runPostDownloadTasks()
		
	def slot_lyrics_fulltext(self, track):
		if not track:
			self.artist_search_thread.search(self.searchString)
			return
			
		ans = QtGui.QMessageBox.question(self, tr("Song Suggestion"), tr("You've searched a partial lyrics of the following song:<br /><b>%s</b>.<br /><br />Do you want to search for it instead?") % track, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
		if ans == QtGui.QMessageBox.Yes:
			self.search_lineEdit.setText(track)
			self.search_slot(spellCheck=False)
		
	def fetch_tracks_init_data(self, artists):
		self.artistsObjs = artists
		self.artist_album_thread.search(artists[0])
		
	def launch_tracks_explorer(self, vars):
		if self.artistsObjs:
			w = TracksExplorerWindow.MainWin(self.artistsObjs)
			w.exec_()
			
			if hasattr(w, 'output'):
				self.search_lineEdit.setText(w.output)
				self.search_slot(spellCheck=False, ArtistLookup=False)
		else:
			log.error("reached to launch_tracks_explorer, but self.artistsObjs is blank.")
		
	### CUSTOM SIGNALS PROCESSING ###
	
	def updateStatusBar(self, s, append=False):
		"update slot for the updateStatusBar(PyQt_PyObject) signal"
		if append:
			s = unicode(self.status_txt.text()) + unicode(s)
		self.status_txt.setText(s)

	def update_search_results(self, songObj):
		if songObj and songObj.score >= config.relevance_minimum and not songObj.url in [x.url for x in self.songsObjs] and songObj.filesize:
			self.songsObjs.append(songObj)
			log.debug("New SongObj created: %s" % repr(songObj))
			
			# If the filesize and final_filesize are equal, there is no video and
			# no conversation. Therefore, "Video Filesize" needs to be set to None.
			if songObj.filesize == songObj.final_filesize:
				rowData = [songObj.title, songObj.artist, songObj.bitrate/1000, 0,
							float("%.2f" % (songObj.filesize/1024.0**2)),
							songObj.mediaLength, songObj.score, songObj.source, songObj.url]
			else:
				rowData = [songObj.title, songObj.artist, songObj.bitrate/1000,
							float("%.2f" % (songObj.filesize/1024.0**2)),
							float("%.2f" % (songObj.final_filesize/1024.0**2)),
							songObj.mediaLength, songObj.score, songObj.source, songObj.url]
			self.tableModel.addRow(rowData)
		elif songObj and not songObj.filesize and songObj.source == 'youtube':
			log.error("Youtube wasn't parsed correctly (filesize=0). search string: %s, videoid: %s" % (songObj.searchString, songObj.youtube_videoid))

	def update_dl_progress_bar(self, i, dlRate, eta, currentBytes, filesize):
		"updates download progress bar"
		
		eta_s = eta%60
		eta_m = eta/60
		
		self.prg_bar.setValue(i)
		if dlRate/1024**2 > 1: # If dlRate is in MBs
			if eta:
				if eta_m:
					self.status_txt.setText(tr("Downloading @ %.2f MB/s, %dm%ds left... [%.2f/%.2f MB]") % (dlRate/1024**2, eta_m, eta_s, currentBytes/1024.0**2, filesize/1024.0**2))
				else:
					self.status_txt.setText(tr("Downloading @ %.2f MB/s, %ds left... [%.2f/%.2f MB]") % (dlRate/1024**2, eta, currentBytes/1024.0**2, filesize/1024.0**2))
			else:
				self.status_txt.setText(tr("Downloading @ %.2f MB/s... [%.2f/%.2f MB]") % (dlRate/1024**2, currentBytes/1024.0**2, filesize/1024.0**2))
		else: # If dlRate is in KBs
			if eta:
				if eta_m:
					self.status_txt.setText(tr("Downloading @ %.2f KB/s, %dm%ds left... [%.2f/%.2f MB]") % (dlRate/1024, eta_m, eta_s, currentBytes/1024.0**2, filesize/1024.0**2))
				else:
					self.status_txt.setText(tr("Downloading @ %.2f KB/s, %ds left... [%.2f/%.2f MB]") % (dlRate/1024, eta, currentBytes/1024.0**2, filesize/1024.0**2))
			else:
				self.status_txt.setText(tr("Downloading @ %.2f KB/s... [%.2f/%.2f MB]") % (dlRate/1024, currentBytes/1024.0**2, filesize/1024.0**2))
		
	def update_enc_progress_bar(self, i, currentBytes, filesize):
		"updates download progress bar"
		self.prg_bar.setValue(i)
		# self.status_txt.setText(tr("Encoding... [%.2f MB / %.2f MB]") % (currentBytes/1024.0**2, filesize/1024.0**2))
		
	### OTHER FUNCTIONS ###
	def enableSearchUi(self):
		"Make search button clickable again"
		self.search_cancel_button.setEnabled(False)
		
		if not self.search_thread.isRunning() and not self.thread3.isRunning():
			self.status_gif.setVisible(False)
		
	def enableDownloadUi(self):
		"Make download button clickable again"
		self.downloadAudio_checkbox.setEnabled(True)
		self.downloadVideo_checkbox.setEnabled(True)
		self.dl_button.setEnabled(True)
		self.dl_cancel_button.setEnabled(False)
		
		if not self.search_thread.isRunning() and not self.thread3.isRunning():
			self.status_gif.setVisible(False)
			
	def enableStatusGif(self):
		self.status_gif.setVisible(True)
	
	def disableStatusGif(self):
		if not self.search_thread.isRunning() and not self.thread3.isRunning():
			self.status_gif.setVisible(False)
		
	def setID3Tags(self):
		"Function sets ID3 Tags"
		if self.ID3TagsToEdit:
			log.debug("Saving ID3 data to file...")
			audio_path = r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename('mp3'))
			if not os.path.exists(audio_path):
				log.error('audio_path does not exist: %s' % audio_path)
				QtGui.QMessageBox.critical(self, tr("Error"), tr("We couldn't save the ID3 data. We advise you to get in contact with the developer of this software and send him the debug data."), QtGui.QMessageBox.Ok)
			utils.setID3Tags(self.ID3TagsToEdit, audio_path)
	
	def renameFilesByID3(self):
		"Renames files by ID3 data"
		d = self.ID3TagsToEdit
		if d:
			old_audio_path = r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename('mp3'))
			old_video_path = r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename())
				
			if 'TPE1' in d.keys() and d['TPE1'].text[0]:
				self.songObj.artist = self.ID3TagsToEdit['TPE1'].text[0]
			if 'TIT2' in d.keys() and d['TIT2'].text[0]:
				self.songObj.title = self.ID3TagsToEdit['TIT2'].text[0]
				
			new_audio_path = r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename('mp3'))
			new_video_path = r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename())
			
			log.debug('renameFilesByID3 (audio old-->new): %s --> %s' % (old_audio_path, new_audio_path))
			log.debug('renameFilesByID3 (video old-->new): %s --> %s' % (old_video_path, new_video_path))
			
			if config.downloadAudio and old_audio_path.lower() != new_audio_path.lower():
				log.debug("Renaming %s to %s..." % (old_audio_path, new_audio_path))
				if os.path.exists(new_audio_path):
					os.unlink(new_audio_path)
				try:
					shutil.move(old_audio_path, new_audio_path)
				except shutil.Error:
					log.error(traceback.format_exc())
					log.warning("Got shutil.Error, Not Changing filenames...")
				
			elif config.downloadVideo and old_video_path.lower() != new_video_path.lower() and self.songObj.source == 'youtube':
				if os.path.exists(new_video_path):
					os.unlink(new_video_path)
				try:
					shutil.move(old_video_path, new_video_path)
				except shutil.Error, e:
					log.error(traceback.format_exc())
					log.debug("Got shutil.Error, Not Changing filenames...")
				log.debug("Renaming %s to %s..." % (old_video_path, new_video_path))
				
			else:
				log.debug("Names remained the same. Not Changing filenames...")
	
	def runPostDownloadTasks(self):
		"Function runs the post-download tasks"
		# could be runMultimedia, openDir, addItunes, addPlaylist, ask
		act = config.post_download_action
		log.debug("post-download action is %s." % act)
		video_path = r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename())
		audio_path = r"%s\%s" % (config.dl_dir, self.songObj.GetProperFilename('mp3'))
		isMultimediaFile = False if "non-multimedia" in self.songObj.source.lower() else True
		
		try:
			assert (config.downloadAudio and os.path.exists(audio_path)) or (config.downloadVideo and os.path.exists(video_path) or (not isMultimediaFile and os.path.exists(video_path)))
			if act == 'ask':
				w = PostDownloadWindow.MainWin(self.songObj)
				w.exec_()
				# Window may want to append data to the status bar
				if hasattr(w, 'statusBar_append'):
					self.updateStatusBar(w.statusBar_append, append=True)
					
			elif act == 'runMultimedia':
				if os.path.exists(audio_path):
					log.debug("Running %s..." % audio_path)
					os.startfile(audio_path)
				else:
					log.debug("Running %s..." % video_path)
					os.startfile(video_path)
			elif act == 'openDir':
				if config.downloadAudio and os.path.exists(audio_path):
					log.debug("Running explorer with %s selected..." % audio_path)
					utils.launch_file_explorer(audio_path)
				elif video_path != audio_path and config.downloadVideo and os.path.exists(video_path):
					log.debug("Running explorer with %s selected..." % video_path)
					utils.launch_file_explorer(video_path)
				else: # doesnt suppose to happen
					log.debug('Running explorer "%s"...' % config.dl_dir)
					os.startfile(config.dl_dir)
			elif act == 'addItunes':
				log.debug("Adding %s to the iTunes library..." % audio_path)
				utils.add_item_to_itunes_playlist(audio_path)
				self.updateStatusBar(tr("; Saved to iTunes"), append=True)
			elif act == 'addPlaylist':
				log.debug("Adding %s to the %s playlist..." % (audio_path, config.post_download_playlist_path))
				utils.add_item_to_playlist(config.post_download_playlist_path, audio_path)
				self.updateStatusBar(tr("; Saved to playlist"), append=True)
			elif act == 'customLaunch':
				audio_path_mbcs = audio_path.encode('mbcs')
				if not config.downloadAudio or not os.path.exists(audio_path):
					raise RuntimeError(tr('customLaunch is not currently supported with videos'))
				elif not os.path.exists(audio_path_mbcs):
					raise RuntimeError(tr('customLaunch is not currently supported with unicode names'))
				else:
					cmd = config.post_download_custom_cmd.encode('mbcs')
					for x in ['%Audio%', '%audio%', '%AUDIO%']:
						cmd = cmd.replace(x, audio_path_mbcs)
					
					log.debug("Running as a post-download action the command: \"%s\"..." % cmd)
					if config.post_download_custom_wait_checkbox:
						log.debug("post_download_custom_wait_checkbox is True, waiting for termination...")
						func = lambda x: subprocess.Popen(x).wait()
					else:
						func = subprocess.Popen
					self.thread3.init(func, cmd)
					self.enableStatusGif()
					
					exe_name = (cmd.split('"')[1] if cmd[0] == '"' else cmd.split()[0]).split('\\')[-1]
					self.updateStatusBar(tr("; Launched %s") % exe_name, append=True)
			elif act == 'nothing':
				pass
			else:
				raise RuntimeError('act is invalid (%s)' % act)
		except Exception, e:
			log.error(unicode(e))
			QtGui.QMessageBox.critical(self, tr("Error"), tr("An error occured: %s. Running default post-download window.") % unicode(e), QtGui.QMessageBox.Ok)
			w = PostDownloadWindow.MainWin(self.songObj)
			w.exec_()

	def updatePlayerLength(self, t):
		t = t/1000
		m = t/60
		s = t-m*60
		self.mediaTimer.setText('%02d:%02d' % (m, s))
		
	def table_rightclick_popup(self, pos):
		if self.table.selectedIndexes():
			index = self.table.selectedIndexes()[0]
		else:
			return
		url = str(index.data(QtCore.Qt.UserRole).toString())
		songObj = [x for x in self.songsObjs if x.url == url][0]
		
		menu = QtGui.QMenu()
		act_listen = menu.addAction(tr("Listen"))
		act_dl = menu.addAction(tr("Download"))
		act_copyurl = menu.addAction(tr("Copy Url"))
		act_copyname = menu.addAction(tr("Copy Song Name"))
		if songObj.source == "youtube":
			act_copywatchurl = menu.addAction(tr("Copy WatchUrl"))
		act_copyall = menu.addAction(tr("Copy All Data"))
		
		clipboard = QtGui.QApplication.clipboard()
		action = menu.exec_(self.table.mapToGlobal(pos))
		if action == act_listen:
			self.listen_slot()
		if action == act_dl:
			self.download_slot()
		if action == act_copyurl:
			clipboard.setText(songObj.url)
		if action == act_copyname:
			if songObj.artist and songObj.title:
				clipboard.setText("%s - %s" % (songObj.artist, songObj.title))
			elif songObj.title:
				clipboard.setText(songObj.title)
		if action == act_copyall:
			s = ""
			s += "Title: %s\n" % songObj.title
			s += "Artist: %s\n" % songObj.artist
			s += "Bitrate: %s\n" % songObj.bitrate
			if not songObj.source == "youtube":
				s += "Filename: %s\n" % songObj.filename
			s += "Source: %s\n" % songObj.source
			s += "Length (seconds): %s\n" % songObj.mediaLength
			s += "Score: %s\n" % songObj.score
			s += "Url: %s\n" % songObj.url
			s += "Search String: %s" % songObj.searchString
			if songObj.source == "youtube":
				s += "\nYotube WatchUrl: %s" % songObj.youtube_watchurl
			clipboard.setText(s)
		if songObj.source == "youtube" and action == act_copywatchurl:
			clipboard.setText(songObj.youtube_watchurl)
	
	def closeEvent(self, event=None):
		"Runs when the widget is closed"
		if hasattr(self, 'search_thread') and self.search_thread.isRunning():
			self.search_thread.terminate()
		if hasattr(self, 'dl_thread') and self.dl_thread.isRunning():
			self.dl_thread.terminate()
		if hasattr(self, 'player'):
			self.player.clear()

class MyTableModel(QtCore.QAbstractTableModel): 
	def __init__(self, datain, headerdata, parent=None, *args): 
		QtCore.QAbstractTableModel.__init__(self, parent, *args) 
		self.arraydata = datain
		self.headerdata = headerdata

	def rowCount(self, parent=None):
		return len(self.arraydata)

	def columnCount(self, parent=None):
		return len(self.headerdata)

	def data(self, index, role): 
		if not index.isValid():
			return QtCore.QVariant()
			
		value = self.arraydata[index.row()][index.column()]

		if role == QtCore.Qt.UserRole:
			return self.arraydata[index.row()][-1] # url
		
		if role == QtCore.Qt.BackgroundRole:
			if index.row() % 2:
				return QtCore.QVariant(QtGui.QBrush(QtGui.QColor(*config.table_odd_color)))
			else:
				return QtCore.QVariant(QtGui.QBrush(QtGui.QColor(*config.table_even_color)))
		
		if role == QtCore.Qt.ForegroundRole:
			return QtCore.QVariant(QtGui.QBrush(QtGui.QColor(*config.table_foreground_color)))
			
		if index.column() == 6: # If score column
			if role == QtCore.Qt.DecorationRole:
				value = math.ceil(value*2)/2
				pix_list = []
				
				for i in range(int(value)):
					pix_list.append(QtGui.QPixmap('pics/fullstar.png'))
				if not value.is_integer():
					pix_list.append(QtGui.QPixmap('pics/halfstar.png'))
				for i in range(5-int(math.ceil(value))):
					pix_list.append(QtGui.QPixmap('pics/emptystar.png'))
				
				pix = utils.qt.combine_pixmaps(pix_list)
				if app.isRightToLeft(): # If the app is in RTL mode, we need to reverse the pixmap
					pix = pix.transformed(QtGui.QTransform().scale(-1, 1))
				return pix
			else:
				return QtCore.QVariant()
				
		if role != QtCore.Qt.DisplayRole:
			return QtCore.QVariant()
			
		if index.column() == 5 and value: # if source length
			value = "%.1d:%.2d" % (value/60, value%60)
		if index.column() == 7: # if source column
			value = value.capitalize()
			
		if value == 0:
			value = '-----'
			
		return QtCore.QVariant(value)

	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return QtCore.QVariant(self.headerdata[col])
		return QtCore.QVariant()
		
	def sort(self, Ncol, order):
		self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
		self.arraydata = sorted(self.arraydata, key=operator.itemgetter(Ncol))
		if order == QtCore.Qt.DescendingOrder:
			self.arraydata.reverse()
		self.emit(QtCore.SIGNAL("layoutChanged()"))
	
	def addRow(self, row_data, parent=QtCore.QModelIndex()):
		if parent.isValid():
			return QtCore.QVariant()
		self.beginInsertRows(parent, self.rowCount(), self.rowCount())
		self.arraydata.append(row_data)
		self.endInsertRows()
	
	def clearTable(self, parent=QtCore.QModelIndex()):
		if parent.isValid():
			return QtCore.QVariant()
		self.beginRemoveRows(parent, 0, self.rowCount()-1)
		self.arraydata = []
		self.endRemoveRows()

if __name__ == '__main__':
	# Setup Environment
	if '__file__' in vars():
		os.chdir(utils.module_path(__file__))
	else:
		os.chdir(utils.module_path())
		log.debug(utils.module_path())
	sys.excepthook = Main.my_excepthook
	warnings.simplefilter('ignore')
	logger.start(config)
	
	# QApp Launch, wrapped in a while loop to allow restarting of the QApp.
	# The config and logger does NOT restart or reloaded.
	app = QtGui.QApplication(sys.argv)
	app.setStyle(config.appStyle)
	while True:
		if not config.lang:
			trans = QtCore.QTranslator()
			qt_trans = QtCore.QTranslator()
			log.debug('Prefered language is not set. Asking user... (Locale is %s)' % QtCore.QLocale.system().name())
			
			if QtCore.QLocale.system().name() == 'en_US':
				log.debug('Setting language as en_US')
				config.lang = 'en_US'
				
			# if the user's locale language is supported
			elif QtCore.QLocale.system().name() in config.lang_rtl.keys():
				# init translator
				qm_path = r'ts\%s.qm' % QtCore.QLocale.system().name()
				if not os.path.exists(qm_path):
					log.error('QM file was not found: %s' % qm_path)
					
				trans.load(qm_path)
				qt_trans.load(r"ts\qt_" + QtCore.QLocale.system().name()[:2])
				
				app.installTranslator(trans)
				app.installTranslator(qt_trans)
				
				if config.lang_rtl[str(QtCore.QLocale.system().name())]:
					app.setLayoutDirection(QtCore.Qt.RightToLeft)
				
				# ask for suggestion
				ans = QtGui.QMessageBox.question(None, tr("Language Suggestion"), tr('The application is available in %s. Do you want to use the language pack?\n\nClick yes for %s.\nClick no for English.') % (QtCore.QLocale.system().nativeLanguageName(), QtCore.QLocale.system().nativeLanguageName()), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
				if ans == QtGui.QMessageBox.Yes:
					log.debug('Setting language as %s' % QtCore.QLocale.system().name())
					config.lang = QtCore.QLocale.system().name()
				else:
					log.debug('Setting language as en_US')
					config.lang = 'en_US'
					app.removeTranslator(trans)
					app.setLayoutDirection(QtCore.Qt.LeftToRight)
					
		elif config.lang == 'en_US':
			app.setLayoutDirection(QtCore.Qt.LeftToRight)
			
			# Remove translators, if exist
			try:
				app.removeTranslator(trans)
			except Exception:
				pass
			try:
				app.removeTranslator(qt_trans)
			except Exception:
				pass

		elif config.lang != 'en_US':
			trans = QtCore.QTranslator()
			qt_trans = QtCore.QTranslator()
			
			qm_path = r'ts\%s.qm' % config.lang
			if not os.path.exists(qm_path):
				log.error('QM file was not found: %s' % qm_path)
				
			trans.load(qm_path)
			qt_trans.load(r"ts\qt_" + config.lang[:2])
			
			app.installTranslator(trans)
			app.installTranslator(qt_trans)
			if config.lang_rtl[config.lang]:
				app.setLayoutDirection(QtCore.Qt.RightToLeft)
				
		try:
			Main.init()
		except NoInternetConnectionException:
			QtGui.QMessageBox.warning(None, tr("Error"), tr("The Internet connection seems to be faulty. Please make sure you have access to the web and try again."), QtGui.QMessageBox.Ok)
			sys.exit()
		except NoDnsServerException:
			QtGui.QMessageBox.warning(None, tr("Error"), tr("The Internet connection seems to be faulty. Your DNS server couldn't be reached. Please make sure you have access to the web and try again."), QtGui.QMessageBox.Ok)
			sys.exit()
		
		main_win = MainWindow()
		main_win.show()
		
		exitcode = app.exec_()
		if exitcode != 1000: # 1000 is the RESTART code.
			log.debug("Stopped logging.")
			logger.stop()
			if os.path.exists(config.temp_dir):
				p = utils.launch_without_console(r'cmd /c rd /S /Q %s' % config.temp_dir)
				p.wait()
			sys.exit(exitcode)