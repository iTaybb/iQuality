# coding: utf-8
# Copyright (C) 2012-2015 Itay Brandes

'''
PyQt4 GUI for the iQuality application
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
import pprint
import copy
import random
import webbrowser
import urllib
from urlparse import parse_qs, urlparse, urlunparse
import warnings

import sip; sip.setapi('QString', 2)
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QAxContainer
from PyQt4.phonon import Phonon
import pySmartDL

import Main
import Config; config = Config.config
import logger
from logger import log
from GuiThreads import GenericThread, SearchThread, DownloadThread, ArtistSearchThread, ArtistLookupThread, LyricsFulltextSearchThread, SpellCheckThread
from GuiSubWindows import ID3Window, PostDownloadWindow, TracksExplorerWindow, ChartsExplorerWindow, SettingsWindow, HelpSearchWindow, UpdaterWindow, SupportArtistsWindow
from CustomExceptions import NoSpaceWarning, NoResultsException, NewerVersionWarning, NoInternetConnectionException, NoDnsServerException, NotSupportedFiletypeException, FileInUseException, YoutubeException, ComponentsFaultyWarning
import Hints
import utils
tr = utils.qt.tr

__version__ = Config.__version__
__date__ = Config.__date__
__author__ = 'Itay Brandes (Brandes.Itay@gmail.com)'

# from PyQt4 import QtCore; import pdb; QtCore.pyqtRemoveInputHook(); pdb.set_trace()

class MainWindow(QtGui.QMainWindow):
	"Main Gui Window"
	
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		
		self.resize(*config.mainWindow_resolution)
		self.setStyleSheet(config.mainWindow_styleSheet)
		self.setWindowTitle(config.windowTitle)
		self.setWindowIcon(QtGui.QIcon(os.path.join('pics', 'pokeball.png')))
		self.setAcceptDrops(True)
		             
		self.artistsObjs = []
		self.songsObjs = []
		self.downloadQueue = []
		self._threads = []
			
		self.init_threads()
		self.init_systemTray()
		self.init_menubar()
		self.init_widgets()
		
		if len(sys.argv) > 1 and (sys.argv[1] == '/stage' or sys.argv[1] == '/stagelocal'):
			log.debug('Working in stage mode')
			if sys.argv[1] == '/stagelocal':
				config.esky_zipfiles_download_page = config.esky_zipfiles_stagelocal_download_page
				config.newest_version_API_webpage = config.newest_version_stagelocal_API_webpage
				config.components_json_url = config.components_json_stagelocal_url
				config.packages_json_url = config.packages_json_stagelocal_url
			else:
				config.esky_zipfiles_download_page = config.esky_zipfiles_stage_download_page
				config.newest_version_API_webpage = config.newest_version_stage_API_webpage
				config.components_json_url = config.components_json_stage_url
				config.packages_json_url = config.packages_json_stage_url
			config.last_sanity_check_timestamp = 0 # trigger online sanity check everytime
			
			log.debug('Esky ZipFiles: %s' % config.esky_zipfiles_download_page)
			log.debug('Newest Version API: %s' % config.newest_version_API_webpage)
			log.debug('Components Json: %s' % config.components_json_url)
			log.debug('Packages Json: %s' % config.packages_json_url)
			log.debug('Newest Version API: %s' % config.newest_version_API_webpage)
			
			del sys.argv[1]
		
		_warnings = Main.sanity_check()
		for w in _warnings:
			if isinstance(w, NoSpaceWarning):
				QtGui.QMessageBox.warning(self, tr("Warning"), tr("There are less than 200MB available in drive %s (%.2fMB left). Application may not function properly.") % (w.drive, w.space/1024.0**2), QtGui.QMessageBox.Ok)
			if isinstance(w, NewerVersionWarning):
				if w.esky:
					if config.auto_update:
						win = UpdaterWindow.MainWin('update_app', w.esky, w.newest)
						win.exec_()
					else:
						ans = QtGui.QMessageBox.question(self, tr("Update Available"), tr("A new version of iQuality is available (%s). Updates includes performance enhancements, bug fixes, new features and fixed parsers.<br /><br />For the complete changes list, you can visit our <a href=\"%s\">facebook page</a>.<br /><br />Do you want to install the update?") % (w.newest, config.facebook_page), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
						if ans == QtGui.QMessageBox.Yes:
							win = UpdaterWindow.MainWin('update_app', w.esky, w.newest)
							win.exec_()
				else:
					QtGui.QMessageBox.information(self, tr("Information"), tr("A new version of iQuality is available (%s). Updates includes performance enhancements, bug fixes, new features and fixed parsers.<br /><br />The application is not guaranteed to work if it's not updated, and will probably fail.<br />For the complete changes list, you can visit our <a href=\"%s\">facebook page</a>.<br /><br />You can grab it from the bottom box of the main window, or from the <a href=\"%s\">iQuality website</a>.") % (w.newest, config.facebook_page, config.website), QtGui.QMessageBox.Ok)
			if isinstance(w, ComponentsFaultyWarning):
				win = UpdaterWindow.MainWin('update_component', w.components)
				win.exec_()
		
		### Caching
		if config.prefetch_charts:
			self.run_in_new_thread(Main.WebParser.WebServices.parse_billboard)
			self.run_in_new_thread(Main.WebParser.WebServices.parse_uktop40)
			self.run_in_new_thread(Main.WebParser.WebServices.parse_glgltz)
			self.run_in_new_thread(Main.WebParser.WebServices.parse_chartscoil)
		
		if len(sys.argv) > 1 and sys.argv[1]:
			if sys.argv[1] in ['-c', '--conf', '--config', '/conf', '/config']:
				self.settingsWindow_slot()
				sys.exit()
			elif sys.argv[1] in ['-i', '--id3', '/id3']:
				if len(sys.argv) > 2:
					self.id3Window_slot(unicode(sys.argv[2], sys.getfilesystemencoding()))
				else:
					while True:
						self.id3Window_slot()
						
						ans = QtGui.QMessageBox.question(self, tr("ID3 Editor"), tr("Do you want to edit another song's tags?"), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
						if ans != QtGui.QMessageBox.Yes:
							break
				
				sys.exit()
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
			
			if urlparse(x.lower()).scheme in config.allowd_web_protocols \
				and ('.' in urlparse(x.lower()).path.split('/')[-1] or urlparse(x.lower()).query or 'soundcloud.com' in x.lower()):
				self.search_lineEdit.setText(x)
				self.search_slot()
				
		if config.isDownloadInProgress:
			ans = QtGui.QMessageBox.question(self, tr("Download Interrupted"), tr('A previous download has been interrupted. Do you want to do resume it?<br /><br />(url: <i>%s</i>)') % config.last_url_download, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
			if ans == QtGui.QMessageBox.Yes:
				self.search_lineEdit.setText(config.last_url_download)
				self.search_slot(luckyMode=True)
						
			config.isDownloadInProgress = False
				
	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls:
			event.accept()
		else:
			event.ignore()
			
	def dragMoveEvent(self, event):
		if event.mimeData().hasUrls:
			event.setDropAction(QtCore.Qt.CopyAction)
			event.accept()
		else:
			event.ignore()
			
	def dropEvent(self, event):
		if event.mimeData().hasUrls:
			event.setDropAction(QtCore.Qt.CopyAction)
			event.accept()
			path = unicode(event.mimeData().urls()[0].toLocalFile())
			self.id3Window_slot(path)
		else:
			event.ignore()
	
	def reload_thread(self, thread, do_log=True):
		'''
		Terminates and then creating a new thread on the same object name.
		paramter "thread" must be a string.
		'''
		if do_log:
			log.debug('Terminating and restarting thread "%s"...' % thread)
		eval("self." + thread).terminate()
		self.init_threads([thread])
		
	def run_in_new_thread(self, func, args=""):
		t = GenericThread()
		t.init(func, args)
		
		'''
		if no reference exists in the object itself, GC will collect and delete the thread even if it's still running.
		Fixes error: QThread: Destroyed while thread is still running
		'''
		self._threads.append(t)
		
		return t
	
	def init_threads(self, threads=None):
		"initialize application threads"
		if not threads:
			threads = ['thread3', 'search_thread', 'dl_thread', 'artist_search_thread', 'artist_album_thread', 
						'lyrics_fulltext_thread', 'autocomplete_thread', 'spellcheck_thread', 'usersonline_thread']
			
		if 'thread3' in threads:
			self.thread3 = GenericThread()
			self.thread3.error.connect(self.error_slot)
			self.thread3.finished.connect(self.disableStatusGif)
			
		if 'autocomplete_thread' in threads:
			self.autocomplete_thread = GenericThread(log_succ=False)
			self.autocomplete_thread.output.connect(self.slot_autocomplete_done)
			
		if 'spellcheck_thread' in threads:
			self.spellcheck_thread = SpellCheckThread()
			self.spellcheck_thread.output.connect(self.slot_spellcheck_done)
			
		if 'usersonline_thread' in threads:
			self.usersonline_thread = GenericThread(relaunch=config.online_users_check_interval)
			self.usersonline_thread.output.connect(self.slot_usersonline_done)
			
		if 'search_thread' in threads:
			self.search_thread = SearchThread()
			self.search_thread.output.connect(self.update_search_table)
			self.search_thread.error.connect(self.error_slot)
			self.search_thread.finished_lucky.connect(self.search_thread_finished_lucky)
			self.search_thread.finished.connect(self.search_thread_finished)
			
		if 'dl_thread' in threads:
			self.dl_thread = DownloadThread()
			self.dl_thread.downloadProgress.connect(self.update_dl_progress_bar)
			self.dl_thread.encProgress.connect(self.update_enc_progress_bar)
			self.dl_thread.status.connect(self.updateStatusBar)
			self.dl_thread.error.connect(self.error_slot)
			self.dl_thread.startedTask.connect(self.dl_thread_startedTask)
			self.dl_thread.finishedTask.connect(self.dl_thread_finishedTask)
			# self.dl_thread.finished.connect(self.dl_thread_finished_all)
			
		if 'artist_search_thread' in threads:
			self.artist_search_thread = ArtistSearchThread()
			self.artist_search_thread.output.connect(self.fetch_tracks_init_data)
			
		if 'artist_album_thread' in threads:
			self.artist_album_thread = ArtistLookupThread()
			self.artist_album_thread.output.connect(self.launch_tracks_explorer)
			
		if 'lyrics_fulltext_thread' in threads:
			self.lyrics_fulltext_thread = LyricsFulltextSearchThread()
			self.lyrics_fulltext_thread.output.connect(self.slot_lyrics_fulltext)
	
	def init_systemTray(self):
		self.systemTray = QtGui.QSystemTrayIcon(QtGui.QIcon(os.path.join('pics', 'iQUACK.png')), self)
		menu = QtGui.QMenu(self)
		exitAction = menu.addAction(tr("Exit"))
		exitAction.triggered.connect(QtGui.qApp.quit)
		self.systemTray.setContextMenu(menu)
		self.systemTray.show()
	
	def init_menubar(self):
		"initialize application menubar"
		# File Menu
		fileMenu = self.menuBar().addMenu(tr('File'))
		id3Action = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'id3edit.png')), tr('ID3 Editor'), self)        
		id3Action.setStatusTip(tr('Edit ID3'))
		id3Action.triggered.connect(self.id3Window_slot)
		exitAction = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'cancel.png')), tr('Exit'), self)
		exitAction.setStatusTip(tr('Exit application'))
		exitAction.triggered.connect(QtGui.qApp.quit)
		fileMenu.addAction(id3Action)
		fileMenu.addSeparator()
		fileMenu.addAction(exitAction)
		
		# Tools Menu
		toolsMenu = self.menuBar().addMenu(tr('Tools'))
		rand_act = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'dice.png')), tr('Pick up a random song'), self)
		rand_act.triggered.connect(self.randomSong_slot)
		chart_act = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'charts.png')), tr('Choose songs from top charts'), self)
		chart_act.triggered.connect(self.chartsFetch_slot)
		opendir_act = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'folder.png')), tr('Open downloaded files folder'), self)
		opendir_act.triggered.connect(self.slot_opendir)
		
		toolsMenu.addAction(rand_act)
		toolsMenu.addAction(chart_act)
		toolsMenu.addAction(opendir_act)
		
		# Settings Menu
		settingsMenu = self.menuBar().addMenu(tr('Settings'))
		act = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'settings.png')), tr('Preferences'), self)
		act.setStatusTip(tr("Configure iQuality's behavior"))
		act.triggered.connect(self.settingsWindow_slot)
		settingsMenu.addAction(act)
		
		# Languages Menu
		langMenu = self.menuBar().addMenu(tr('Languages'))
		# langMenu = settingsMenu.addMenu(tr('Languages'))
		actus = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'flag-us.png')), tr('English'), self)
		actus.setStatusTip(tr("English"))
		actus.triggered.connect(self.lang_en_slot)
		actil = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'flag-il.png')), tr('Hebrew'), self)
		actil.setStatusTip(tr("Hebrew"))
		actil.triggered.connect(self.lang_he_slot)
		langMenu.addAction(actus)
		langMenu.addAction(actil)
		
		# Help Menu
		helpMenu = self.menuBar().addMenu(tr('Help'))
		act_help = QtGui.QAction(QtGui.QIcon(os.path.join('pics', 'support.png')), tr('Search Field Help'), self)
		act_help.setStatusTip(tr('Search Field Help'))
		act_help.triggered.connect(self.helpSearch_slot)
		act_logfile = QtGui.QAction(QtGui.QIcon(os.path.join('pics' ,'file_broken.png')), tr('Open Log File'), self)
		act_logfile.setStatusTip(tr('Open Log File'))
		act_logfile.triggered.connect(self.logfile_slot)
		act_credits = QtGui.QAction(QtGui.QIcon(os.path.join('pics' ,'pokeball.png')), tr('About'), self)
		act_credits.setStatusTip(tr('Show Credits'))
		act_credits.triggered.connect(self.creditsWindow_slot)
		act_website = QtGui.QAction(QtGui.QIcon(os.path.join('pics' ,'world.png')), tr('Visit our website'), self)
		act_website.setStatusTip(tr('Visit our website'))
		act_website.triggered.connect(self.visitWebsite_slot)
		act_facebook = QtGui.QAction(QtGui.QIcon(os.path.join('pics' ,'facebook.png')), tr('Visit our facebook page'), self)
		act_facebook.setStatusTip(tr('Visit our facebook page'))
		act_facebook.triggered.connect(self.visit_facebook_slot)
		
		helpMenu.addAction(act_help)
		helpMenu.addAction(act_logfile)
		helpMenu.addSeparator()
		helpMenu.addAction(act_credits)
		helpMenu.addAction(act_website)
		helpMenu.addAction(act_facebook)
		
		# Image Push Buttons
		helpSearch_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics' ,'support.png')), "")
		helpSearch_button.clicked.connect(self.helpSearch_slot)
		helpSearch_button.setFlat(True)
		helpSearch_button.setToolTip(tr('Search Field Help'))
		charts_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics' ,'charts.png')), "")
		charts_button.clicked.connect(self.chartsFetch_slot)
		charts_button.setFlat(True)
		charts_button.setToolTip(tr('Choose songs from top charts'))
		opendir_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics' ,'folder.png')), "")
		opendir_button.clicked.connect(self.slot_opendir)
		opendir_button.setFlat(True)
		opendir_button.setToolTip(tr('Open downloaded files folder'))
		rand_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics' ,'dice.png')), "")
		rand_button.clicked.connect(self.randomSong_slot)
		rand_button.setFlat(True)
		rand_button.setToolTip(tr('Pick up a random song'))
		facebook_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics' ,'facebook.png')), "")
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
		
	def id3Window_slot(self, f = None):
		"Runs the ID3 Editor"
		if not f:
			dialog = QtGui.QFileDialog()
			dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
			f = unicode(dialog.getOpenFileName(caption=tr('Choose the mp3 file'), filter="MP3 file (*.mp3)"))
		if f:
			if not os.path.exists(f):
				log.debug('File "%s" does not exists. Trying to fix unicode problems...' % f)
				fixed_path = utils.attemp_to_fix_unicode_problems(f)

				if fixed_path:
					log.debug('Fix succeeded: %s --> %s' % (f, fixed_path))
					f = fixed_path
				if not fixed_path:
					log.debug('Fix didn\'t succeed. File "%s" does not exist.' % f)
					QtGui.QMessageBox.critical(self, tr("Error"), tr('File "%s" does not exist.') % f, QtGui.QMessageBox.Ok)
					return
			
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
		QtGui.QMessageBox.about(self, tr("About"), config.credits_text)
	
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
		self.search_cancel_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics', 'cancel.png')), "")
		self.search_cancel_button.clicked.connect(self.cancel_search_slot)
		self.search_cancel_button.setEnabled(False)
		self.search_cancel_button.setFlat(True)
		self.search_cancel_button.setToolTip(tr('Stop search process'))
		
		self.searchTable = QtGui.QTableView()
		self.searchTable.setShowGrid(False)
		self.searchTable.setFont(QtGui.QFont(*config.table_font))
		self.searchTable.setSelectionBehavior(QtGui.QTableView.SelectRows)
		# self.searchTable.setSelectionMode(QtGui.QTableView.SingleSelection)
		self.searchTable.setSortingEnabled(True)
		self.searchTable.horizontalHeader().setStretchLastSection(True)
		self.searchTable.verticalHeader().setVisible(False)
		self.searchTable.verticalHeader().setDefaultSectionSize(config.table_DefaultSectionSize)
		self.searchTable.resizeColumnsToContents()
		self.searchTable.setStyleSheet(config.table_styleSheet_rtl if config.lang_rtl[config.lang] else config.table_styleSheet_ltr)
		self.searchTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.searchTable.customContextMenuRequested.connect(self.searchTable_rightclick_popup)
		self.searchTable.doubleClicked.connect(self.searchTable_doubleClicked_slot)
		
		if config.hide_url_column:
			header = [tr('Title'), tr('Artist'), tr('Bitrate'), tr('Video Size (MB)'), 
						tr('Audio Size (MB)'), tr('Length'), tr('Relevance'), tr('Source')]
		else:
			header = [tr('Title'), tr('Artist'), tr('Bitrate'), tr('Video Size (MB)'), 
						tr('Audio Size (MB)'), tr('Length'), tr('Relevance'), tr('Source'),
						tr('URL')]
		
		self.searchTableModel = SearchTableModel([], header, self)
		self.searchTable.setModel(self.searchTableModel)
		
		if config.hide_url_column:
			self.searchTable.setColumnWidth(0, 300) # title
			self.searchTable.setColumnWidth(1, 170) # artist
		else:
			self.searchTable.setColumnWidth(0, 200) # title
			self.searchTable.setColumnWidth(1, 95) # artist
		self.searchTable.setColumnWidth(2, 58) # bitrate
		self.searchTable.setColumnWidth(5, 47) # length
		self.searchTable.setColumnWidth(7, 75) # source
		
		self.downloadTable = QtGui.QTableView()
		self.downloadTable.setShowGrid(False)
		self.downloadTable.setFont(QtGui.QFont(*config.table_font))
		self.downloadTable.setSelectionBehavior(QtGui.QTableView.SelectRows)
		self.downloadTable.setSelectionMode(QtGui.QTableView.SingleSelection)
		self.downloadTable.setSortingEnabled(True)
		self.downloadTable.horizontalHeader().setStretchLastSection(True)
		self.downloadTable.verticalHeader().setVisible(False)
		self.downloadTable.verticalHeader().setDefaultSectionSize(config.table_DefaultSectionSize)
		self.downloadTable.resizeColumnsToContents()
		self.downloadTable.setStyleSheet(config.table_styleSheet_rtl if config.lang_rtl[config.lang] else config.table_styleSheet_ltr)
		self.downloadTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		
		header = [	tr('Index'), tr('Title'), tr('Artist'), tr('Filename'), tr('Filesize (MB)'), 
					tr('Downloaded (MB)'), tr('Progress'), tr('Speed'), tr('ETA')]
		
		self.downloadTableModel = DownloadTableModel([], header, self)
		self.downloadTable.setModel(self.downloadTableModel)
	
		self.listen_button = QtGui.QCommandLinkButton(tr("Listen"))
		self.listen_button.clicked.connect(self.listen_slot)
		self.listen_pause_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics', 'pause.png')), "")
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
		self.dl_button.clicked.connect(self.download_slot)
		self.dl_cancel_button = QtGui.QPushButton(QtGui.QIcon(os.path.join('pics', 'cancel.png')), "")
		self.dl_cancel_button.clicked.connect(self.cancel_download_slot)
		self.dl_cancel_button.setEnabled(False)
		self.dl_cancel_button.setFlat(True)
		self.dl_cancel_button.setToolTip(tr('Stop the download process'))
		
		self.buy_button = QtGui.QCommandLinkButton(tr("Support the artists"))
		self.buy_button.clicked.connect(self.slot_buy)
		
		self.prg_bar = QtGui.QProgressBar()
		self.prg_txt = QtGui.QLabel()
		
		self.downloadAudio_checkbox = QtGui.QCheckBox(tr("Audio"))
		self.downloadAudio_checkbox.setCheckState(config.downloadAudio)
		self.downloadAudio_checkbox.setTristate(False)
		self.downloadAudio_checkbox.stateChanged.connect(self.slot_downloadAudio_changed_checkbox)
		self.downloadVideo_checkbox = QtGui.QCheckBox(tr("Video (If exists)"))
		self.downloadVideo_checkbox.setCheckState(config.downloadVideo)
		self.downloadVideo_checkbox.setTristate(False)
		self.downloadVideo_checkbox.stateChanged.connect(self.slot_downloadVideo_changed_checkbox)
		self.trimSilence_checkbox = QtGui.QCheckBox(tr("Trim Silence"))
		self.trimSilence_checkbox.setCheckState(config.trimSilence)
		self.trimSilence_checkbox.setTristate(False)
		self.trimSilence_checkbox.stateChanged.connect(self.slot_trimSilence_changed_checkbox)
		if not config.downloadAudio:
			self.trimSilence_checkbox.setEnabled(False)
		
		self.status_txt = QtGui.QLabel(Hints.get_hint())
		self.status_txt.setFont(QtGui.QFont(*config.status_txt_font))
		self.status_gif = QtGui.QLabel()
		self.movie = QtGui.QMovie(os.path.join("pics", "loading.gif"))
		self.status_gif.setMovie(self.movie)
		self.movie.start()
		self.status_gif.setVisible(False)
		
		if config.show_ads:
			url = config.browser_website.format(config.lang[:2])
			self.browser = QAxContainer.QAxWidget()
			self.browser.setControl("{8856F961-340A-11D0-A96B-00C04FD705A2}")
			self.browser.dynamicCall('Navigate(QString&)', QtCore.QVariant(url))
			self.browser.setFixedHeight(config.browser_height)
		
		self.label5_orig_text = tr(u"iQuality v%s beta by Itay Brandes (%s). The software has been launched %s times, and downloaded %s songs.") % (__version__, __date__, format(config.count_application_runs, ',d'), format(config.count_download, ',d'))
		self.label5 = QtGui.QLabel(self.label5_orig_text)
		self.usersonline_thread.init(Main.WebParser.WebServices.get_currentusers)
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		row1_Layout = QtGui.QHBoxLayout()
		row1_Layout.addWidget(self.label1)
		row1_Layout.addWidget(self.search_lineEdit)
		row1_Layout.addWidget(self.search_button)
		row1_Layout.addWidget(self.search_cancel_button)
		row1_Layout.setContentsMargins(0, 0, 0, 0)
		
		mainLayout.addLayout(row1_Layout, 1, 0, 1, 3)
		
		self.tables = QtGui.QTabWidget()
		# self.tables.addTab(self.searchTable, tr("Searchs"))
		# self.tables.addTab(self.downloadTable, tr("Downloads"))
		
		# mainLayout.addWidget(self.tables, 2, 0, 1, 0)
		mainLayout.addWidget(self.searchTable, 2, 0, 1, 0)
		
		videoaudio_checkboxs_Layout = QtGui.QVBoxLayout()
		videoaudio_checkboxs_Layout.addWidget(self.downloadAudio_checkbox)
		videoaudio_checkboxs_Layout.addWidget(self.downloadVideo_checkbox)
		videoaudio_checkboxs_Layout.addWidget(self.trimSilence_checkbox)
		videoaudio_checkboxs_Layout.addStretch(5)
		
		prg_bar_Layout = QtGui.QVBoxLayout()
		prg_bar_Layout.addStretch(1)
		prg_bar_Layout.addWidget(self.prg_bar)
		prg_bar_Layout.addWidget(self.prg_txt)
		prg_bar_Layout.addStretch(1)
		
		row_5_6_Layout = QtGui.QGridLayout()
		row_5_6_Layout.addWidget(self.listen_button, 0, 0)
		row_5_6_Layout.addWidget(self.mediaVolumeSlider, 0, 1)
		row_5_6_Layout.addWidget(self.listen_pause_button, 0, 2)
		row_5_6_Layout.addWidget(self.mediaSlider, 0, 3)
		row_5_6_Layout.addWidget(self.mediaTimer, 0, 4)
		row_5_6_Layout.addWidget(self.dl_button, 1, 0)
		row_5_6_Layout.addWidget(self.buy_button, 2, 0)
		row_5_6_Layout.addLayout(videoaudio_checkboxs_Layout, 1, 1, 2, 1)
		row_5_6_Layout.addWidget(self.dl_cancel_button, 1, 2, 2, 1)
		row_5_6_Layout.addLayout(prg_bar_Layout, 1, 3, 2, 2)

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
		
	def slot_spellcheck_done(self, fixed_s, old_s, luckyMode):
		if luckyMode:
			self.search_lineEdit.setText(fixed_s)
			self.search_slot(spellCheck=False, luckyMode=luckyMode)
		else:
			ans = QtGui.QMessageBox.question(self, tr("Spelling Suggestion"), tr('Did you mean %s?') % utils.append_bold_changes(old_s, fixed_s), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
			if ans == QtGui.QMessageBox.Yes:
				self.search_lineEdit.setText(fixed_s)
				self.search_slot(spellCheck=False, luckyMode=luckyMode)
				
	def slot_usersonline_done(self, users_online_count):
		if users_online_count:
			self.label5.setText(self.label5_orig_text + tr(" %s user(s) are currently using the software.") % format(users_online_count, ',d'))
		
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
		song = self.search_lineEdit.displayText().strip()
			
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
			
			# Check if url is youtube with both playlist and specific video part
			urlObj = urlparse(song)
			domainName = urlObj.netloc.lower()
			if (domainName.endswith('youtube.com') or domainName.endswith('youtu.be')) and not 'videoplayback' in song:
				queries = parse_qs(urlObj.query)
				if ('p' in queries or 'list' in queries) and 'v' in queries:
					log.debug('Url is youtube with playlist part and video part. Asking user what does he want...')
					if luckyMode:
						del queries['v']
					else:
						ans = QtGui.QMessageBox.question(self, tr("Video or playlist?"), tr("You're trying to download a link that contains both a playlist and a specific video. Which do you want to download?"), tr("Playlist"), tr("Specific Video"), tr("Nothing"))
						if ans == 0:
							log.debug('user chosen to search for the playlist')
							# del queries['v']
						if ans == 1:
							log.debug('user chosen to search for the specific video')
							if 'p' in queries:
								del queries['p']
							if 'list' in queries:
								del queries['list']
						if ans == 2:
							log.debug('user chosen to cancel search')
							return
					
					qs_string = urllib.urlencode(queries, True)
					song = urlunparse((urlObj.scheme, urlObj.netloc, urlObj.path, urlObj.params, qs_string , urlObj.fragment))
					self.search_lineEdit.setText(song)
					log.debug('New url is %s' % song)
		
		elif spellCheck:
			self.spellcheck_thread.init(song, luckyMode)
		
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
		
		self.searchTableModel.clearTable()
		self.songsObjs = []
		self.search_cancel_button.setEnabled(True)
		self.tables.setCurrentIndex(0)
		self.search_thread.search(song, config.songs_count_spinBox, luckyMode)
			
	def cancel_search_slot(self):
		self.reload_thread('search_thread')
		self.reload_thread('spellcheck_thread')
		log.debug("Search task was canceled.")
		self.status_txt.setText(tr("Task was canceled."))
		self.enableSearchUi()
	
	def cancel_download_slot(self):
		self.reload_thread('dl_thread')
		# log.debug("Download task was canceled.")
		self.status_txt.setText(tr("Task was canceled."))
		self.enableDownloadUi()
		
	def listen_slot(self, QModelIndex=None):
		if not Phonon.BackendCapabilities.isMimeTypeAvailable('video/x-flv'):
			ans = QtGui.QMessageBox.question(self, tr("Missing component"), tr('Your system does not support audio streaming. Installing a codec pack is required in order to listen to songs.<br /><br /><b><a href="http://www.cccp-project.net">The Combined Community Codec Pack</a></b> is a simple playback pack for Windows that allows you to play songs and movies. <br /><br />Do you want iQuality to install the "<b>Combined Community Codec Pack</b>" for you?'), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
			if ans == QtGui.QMessageBox.No:
				return
			if ans == QtGui.QMessageBox.Yes:
				win = UpdaterWindow.MainWin('install_package', ['Combined Community Codec Pack'])
				win.exec_()
				
				if Phonon.BackendCapabilities.isMimeTypeAvailable('video/x-flv'):
					QtGui.QMessageBox.information(self, tr("Successful Installation"), tr("Installation completed successfully."), QtGui.QMessageBox.Ok)
				else:
					QtGui.QMessageBox.critical(self, tr("Error"), tr("The installation failed. Please download and install the package manually from <b><a href=\"http://www.cccp-project.net\">http://www.cccp-project.net</a></b>."), QtGui.QMessageBox.Ok)
					return
			
		if self.searchTable.selectedIndexes():
			selectedRows = utils.qt.selectedRowsIndexes(self.searchTable.selectedIndexes())
			if len(selectedRows) > 1:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Please choose one song."), QtGui.QMessageBox.Ok)
				return
			index = self.searchTable.selectedIndexes()[0]
			url = str(index.data(QtCore.Qt.UserRole).toString())
		elif len(self.songsObjs) == 1:
			url = self.songsObjs[0].url
		else:
			QtGui.QMessageBox.critical(self, tr("Error"), tr("Please choose a song."), QtGui.QMessageBox.Ok)
			return
		
		songObj = [x for x in self.songsObjs if x.url == url][0]
		
		if hasattr(self, 'player'):
			log.debug("Stopping audio player...")
			self.player.clear()
			try:
				self.player.tick.disconnect()
			except TypeError:
				pass
			
		if songObj.source == "youtube":
			ans = Main.WebParser.LinksGrabber.get_youtube_dl_link(songObj.videoid,
													config.youtube_listen_quality_priority,
													config.youtube_listen_formats_priority)
			if not ans:
				QtGui.QMessageBox.critical(self, tr("Error"), tr('Sorry, a preview is not available for this video. You can watch it on <a href="%s">youtube</a>.') % songObj.webpage_url, QtGui.QMessageBox.Ok)
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
		
		self.listen_pause_button.setIcon(QtGui.QIcon(os.path.join('pics', 'pause.png')))
		self.listen_pause_button.setEnabled(True)
	
	def volumeChanged_slot(self, val):
		if val > 0.3:
			config.listen_volumeSlider_volume = val
		
	def playpause_slot(self):
		if self.player.state() == Phonon.PlayingState:
			self.player.pause()
			self.listen_pause_button.setIcon(QtGui.QIcon(os.path.join('pics', 'play.png')))
		else:
			self.player.play()
			self.listen_pause_button.setIcon(QtGui.QIcon(os.path.join('pics', 'pause.png')))
	
	def download_slot(self, QModelSearch=None, songObj=None, luckyMode=False):
		if not config.downloadAudio and not config.downloadVideo:
			QtGui.QMessageBox.critical(self, tr("Error"), tr("You've configured the application to download neither audio nor video files. You must choose at least one of them."), QtGui.QMessageBox.Ok)
			return
			
		songObjs = []
			
		if songObj and isinstance(songObj, list): # may be a song object, or a list of songs objects
			songObjs.extend(songObj)
		elif songObj:
			songObjs.append(songObj)
		else:
			selectedRows = utils.qt.selectedRowsIndexes(self.searchTable.selectedIndexes())
			if selectedRows: # If we have selections
				
				# if user's trying to download too many files - we should ask him if that's what he meant
				if not luckyMode and len(selectedRows) > config.files_dl_quantity_threshold:
					ans = QtGui.QMessageBox.question(self, tr("Information"), tr("You're trying to download %d files. Are you sure?") % len(selectedRows), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
					if ans == QtGui.QMessageBox.No:
						return
				
				urls = [str(index.data(QtCore.Qt.UserRole).toString()) for index in selectedRows]
				for url in urls:
					songObjs.append([x for x in self.songsObjs if x.url == url][0])
			elif len(self.songsObjs) == 1: # we don't have selections, but only 1 song is available, so we'll download it
				url = self.songsObjs[0].url
				songObj = [x for x in self.songsObjs if x.url == url][0]
				songObjs.append(songObj)
			else: # no songs available!
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Please choose a song."), QtGui.QMessageBox.Ok)
				return
				
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
		
		'''
		First loop creates the tasks. Second loop queues them.
		We need two loops because we want to create all tasks (takes milliseconds)
		before queuing (may take seconds per each, due to user interaction required with ID3 tagging).
		'''
		tasks = []
		for obj in songObjs:
			obj_copy = copy.deepcopy(obj)
			downloadTask = utils.cls.DownloadTask(len(self.downloadQueue), obj_copy)
			tasks.append(downloadTask)
			self.downloadQueue.append(downloadTask)
			
		for task in tasks:
			self.queue_new_download(task, luckyMode)
			
	def queue_new_download(self, downloadTask, luckyMode):
		songObj = downloadTask.songObj
		
		# download improvments
		if songObj.source == "youtube" and config.downloadAudio and not config.downloadVideo:
			# if downloading audio only from youtube, we should always prefer the audio version 
			metaUrl = Main.WebParser.LinksGrabber.get_youtube_dl_link(songObj.videoid, config.youtube_audioStream_quality_priority, config.youtube_audioStream_formats_priority)
			if metaUrl:
				songObj.url = metaUrl.url
				songObj.itag = metaUrl.itag
				old_filesize = songObj.filesize
				songObj.filesize = Main.HTTPQuery.get_filesize(songObj.url)
				
				log.debug("User downloads audio only from youtube. downloads audio-only stream (%.2f MB instead of %.2f MB)" % (songObj.filesize/1024.0**2, old_filesize/1024.0**2))
				
			else:
				# if downloading audio but not video from youtube, we should always prefer the 720p version, as the audio stream bitrates are equal between 720p and 1080p.
				priority = config.youtube_quality_priority[:]
				if songObj.itag.quality == 'hd1080' and 'hd1080' in priority and 'hd720' in priority:
					priority.remove('hd1080')
					metaUrl = Main.WebParser.LinksGrabber.get_youtube_dl_link(songObj.videoid, priority)
					songObj.url = metaUrl.url
					songObj.itag = metaUrl.itag
					old_filesize = songObj.filesize
					songObj.filesize = Main.HTTPQuery.get_filesize(songObj.url)
					
					log.debug("User downloads audio only from youtube. downloads 720p instead of 1080p (%.2f MB instead of %.2f MB)" % (songObj.filesize/1024.0**2, old_filesize/1024.0**2))
		
		isMultimediaFile = False if "non-multimedia" in songObj.source.lower() else True
		config.count_download += 1
		
		# making dest_paths
		dest_paths = []
		if not isMultimediaFile:
			dest_paths.append(os.path.join(config.dl_dir, songObj.GetProperFilename()))
		if config.downloadAudio:
			dest_paths.append(os.path.join(config.dl_dir, songObj.GetProperFilename('mp3')))
		if config.downloadVideo and songObj.itag:
			dest_paths.append(os.path.join(config.dl_dir, songObj.GetProperFilename()))
		if not dest_paths:
			log.error("Error: I got nothing to download!")
			if not songObj.itag and not config.downloadAudio and config.downloadVideo:
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
							return
						config.dl_dir, dl_filename = os.path.split(ans)
						
						log.debug('dl_dir is now %s' % config.dl_dir)
						songObj.constantFileName = dl_filename
						break
		
		config.last_url_download = songObj.url
		config.isDownloadInProgress = True

		# Disable Ui
		self.disableDownloadUi()
	
		# Run download thread
		downloadTask.dl_status = 'downloading'
		self.dl_thread.queue(songObj, config.dl_dir, downloadTask.id)
		
		# Run ID3 Tags Window
		if isMultimediaFile and config.downloadAudio and config.editID3:
			downloadTask.id3_status = 'waiting_for_user_input'
			if luckyMode:
				w = ID3Window.MainWin(songObj.id3tags_file, 'noask')
			else:
				w = ID3Window.MainWin(songObj.id3tags_file)
				
			if w.isValid:
				w.exec_()
				downloadTask.ID3TagsToEdit = w.ID3TagsToEdit if hasattr(w, 'ID3TagsToEdit') else ""
		
		self.id3_task_finishedTask(downloadTask)
		
	def slot_buy(self):
		if self.searchTable.selectedIndexes():
			selectedRows = utils.qt.selectedRowsIndexes(self.searchTable.selectedIndexes())
			if len(selectedRows) > 1:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Please choose one song."), QtGui.QMessageBox.Ok)
				return
			index = selectedRows[0]
			url = str(index.data(QtCore.Qt.UserRole).toString())
		elif len(self.songsObjs) == 1:
			url = self.songsObjs[0].url
		else:
			w = SupportArtistsWindow.MainWin()
			w.exec_()
			return
			
		# retriving url and deep-copying songobj
		songObj = [x for x in self.songsObjs if x.url == url][0]
		songObj = copy.deepcopy(songObj)
		
		w = SupportArtistsWindow.MainWin(songObj)
		w.exec_()
		
	def developer_dump_slot(self, index):
		url = str(index.data(QtCore.Qt.UserRole).toString())
		songObj = [x for x in self.songsObjs if x.url == url][0]
		
		utils.open_with_notepad(pprint.pformat(songObj.__dict__))
			
	def searchTable_doubleClicked_slot(self, index):
		if config.table_doubleClick_action == 'listen':
			self.listen_slot(index)
		if config.table_doubleClick_action == 'download':
			self.download_slot(index)
		if config.table_doubleClick_action == 'developer_dump':
			self.developer_dump_slot(index)
		
	def error_slot(self, e):
		"Error slot for the error signal"
		config.isDownloadInProgress = False
		
		if isinstance(e, NotSupportedFiletypeException):
			QtGui.QMessageBox.critical(self, tr("Error"), tr('The application does not support the %s filetype.') % e.ext, QtGui.QMessageBox.Ok)
			
		elif isinstance(e, NoResultsException):
			if e.isDirectLink:
				QtGui.QMessageBox.critical(self, tr("Error"), tr('There is a network problem: The address may be incorrect, or your internet connection got terminated. Please try again later.'), QtGui.QMessageBox.Ok)
			elif not all(config.search_sources.values()):
				disabled_search_sources = [k for k, v in config.search_sources.items() if not v]
				log.debug('some media sources are disabled (%s). asking user if he wants to enable them...' % ", ".join(disabled_search_sources))
				ans = QtGui.QMessageBox.warning(self, tr("Warning"), tr('No songs were found. However, the following media sources are currently disabled: <br /><br /><b>%s</b><br /><br />Enable them and search again?') % "<br />".join(disabled_search_sources), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
				if ans == QtGui.QMessageBox.Yes:
					log.debug("Enabling all media sources...")
					for k in config.search_sources.keys():
						config.search_sources[k] = True
					Config.config.saveToIni() # IMPROVE: Understand why it is needed here.
					self.search_slot()
					return
			else:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("No songs were found."), QtGui.QMessageBox.Ok)
			self.status_txt.setText(tr("No songs were found."))
		
		elif isinstance(e, FileInUseException):
			QtGui.QMessageBox.critical(self, tr("Error"), tr("The process cannot access the file %s because it is being used by another process.") % e.f, QtGui.QMessageBox.Ok)
			
		elif isinstance(e, YoutubeException):
			if e.errorcode == -100:
				s = tr("The application was unable to fetch the Youtube video: Could not decipher video's secret signature. On the new official youtube clips, a new cipher algorithm is introduced, and we still don't understand it too well. This will be fixed in future releases. For the midtime, you can try download a different clip.")
			else:
				s = tr("The application was unable to fetch the Youtube video. (Error %d: %s)") % (e.errorcode, e.reason)
			QtGui.QMessageBox.critical(self, tr("Error"), s, QtGui.QMessageBox.Ok)
			
		elif isinstance(e, IOError):
			QtGui.QMessageBox.critical(self, tr("Error"), tr("The download has failed. It may be a network connection problem. Please try to rerun this application and try again."), QtGui.QMessageBox.Ok)
		
		# elif isinstance(e, Exception):
			# pass
			
		else:
			s = "Unhandled exception: %s" % unicode(e)
			log.error(s)
			QtGui.QMessageBox.critical(self, tr("Error"), s, QtGui.QMessageBox.Ok)
		
		self.enableSearchUi()
		self.enableDownloadUi()
		
	def slot_downloadAudio_changed_checkbox(self, state):
		config.downloadAudio = bool(state)
		self.trimSilence_checkbox.setEnabled(bool(state))
			
	def slot_downloadVideo_changed_checkbox(self, state):
		config.downloadVideo = bool(state)
			
	def slot_trimSilence_changed_checkbox(self, state):
		config.trimSilence = bool(state)
		
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
		self.searchTable.selectRow(self.songsObjs.index(best))
		self.download_slot(songObj=best, luckyMode=True)
	
	def dl_thread_startedTask(self, id):
		log.debug('dl_thread_startedTask, id=%d' % id)
		taskObj = self.downloadQueue[id]
		remaining_tasks = len([task for task in self.downloadQueue if not task.isDone()])
		
		taskObj.dl_status = 'in_progress'
		self.updateStatusBar(tr("Starting Download..."))
		self.prg_txt.setText("%s (%d/%d)" % (taskObj.songObj.GetProperFilename(), len(self.downloadQueue)-remaining_tasks+1, len(self.downloadQueue)))
		
	def id3_task_finishedTask(self, downloadTask):
		downloadTask.id3_status = 'done'
		self.dl_id3_finishedTask(downloadTask)
		
	def dl_thread_finishedTask(self, id, dl_time, encode_time):
		downloadTask = self.downloadQueue[id]
		downloadTask.dl_status = 'done'
		downloadTask.dl_time = dl_time
		downloadTask.dl_encode_time = encode_time
		self.dl_id3_finishedTask(downloadTask)
		
	def dl_id3_finishedTask(self, downloadTask):
		"Will run when dl_thread return a FINISHED_TASK signal. Will also run when id3 window is closed."
		
		songObj = downloadTask.songObj
		log.debug('dl_id3_finishedTask launched (id=%d, dl_status=%s, id3_status=%s)' % (downloadTask.id, downloadTask.dl_status, downloadTask.id3_status))
		
		# if id3 window is still open, but download is finished
		if downloadTask.id3_status != 'done':
			self.updateStatusBar(tr('Waiting for ID3 Tags to be ready...'))
			return
		# if id3 window is done, but download is still in progress
		if downloadTask.dl_status != 'done':
			return
		
		if downloadTask.ID3TagsToEdit:
			log.debug('Settings ID3 Tags...')
			try:
				self.setID3Tags(songObj, downloadTask.ID3TagsToEdit)
			except:
				log.warning("got self.setID3Tags() error, skipping...")
				log.error(traceback.format_exc())
			self.renameFilesByID3(songObj, downloadTask.ID3TagsToEdit)
		else:
			log.debug('No ID3 Tags to set.')
				
		downloadTask.dl_status = 'done'
		
		if all([task.isDone() for task in self.downloadQueue]):
			self.dl_thread_finished_all()
		else:
			self.systemTray.showMessage(tr("Download completed"), tr('File "%s" is ready!') % songObj.GetProperName())
		
	def dl_thread_finished_all(self):
		"Will run when dl_thread return a FINISHED_ALL signal."
		log.debug('dl_thread_finished_all launched')
		config.isDownloadInProgress = False
		
		# Get unreported tasks
		tasks_to_report = []
		for task in self.downloadQueue:
			if not task.reportedToUser:
				tasks_to_report.append(task)
				task.reportedToUser = True
				
		assert tasks_to_report
				
		# Set Status Bar
		total_time = sum([task.dl_time+task.dl_encode_time for task in tasks_to_report])
		total_dl_time = sum([task.dl_time for task in tasks_to_report])
		total_size = sum([task.songObj.filesize for task in tasks_to_report])
		
		if len(tasks_to_report) > 1:
			self.updateStatusBar(tr('%d files (%s) downloaded in %s') % (len(tasks_to_report), pySmartDL.utils.sizeof_human(total_size), pySmartDL.utils.time_human(total_time, fmt_short=True)))
			s = tr('%d files (%s) downloaded successfully within %s!') % (len(tasks_to_report), pySmartDL.utils.sizeof_human(total_size), pySmartDL.utils.time_human(total_time))
			self.systemTray.showMessage(tr("Download completed"), s)
			log.debug(s)
		else:
			s = tr('File "%s" is ready!') % tasks_to_report[0].songObj.GetProperName()
			self.systemTray.showMessage(tr("Download completed"), s)
			log.debug(s)
		
		# Run Post Download Tasks Window
		self.runPostDownloadTasks(tasks_to_report)
		self.enableDownloadUi()
		
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
			log.error("launch_tracks_explorer: self.artistsObjs is null")
		
	### CUSTOM SIGNALS PROCESSING ###
	
	def updateStatusBar(self, s, append=False):
		"update slot for the updateStatusBar(PyQt_PyObject) signal"
		if append:
			s = unicode(self.status_txt.text()) + unicode(s)
		self.status_txt.setText(s)

	def update_search_table(self, songObj):
		if songObj and songObj.score >= config.relevance_minimum and not songObj.url in [x.url for x in self.songsObjs] and songObj.filesize:
			self.songsObjs.append(songObj)
			log.debug("New SongObj created: %s" % repr(songObj))
			
			# If the filesize and final_filesize are equal, there is no video and
			# no conversation. Therefore, "Video Filesize" needs to be set to None.
			if songObj.filesize == songObj.final_filesize:
				rowData = [songObj.title, songObj.artist, songObj.bitrate/1000, 0,
							float("%.2f" % (songObj.filesize/1024.0**2)),
							songObj.duration, songObj.score, songObj.source, songObj.url]
			else:
				rowData = [songObj.title, songObj.artist, songObj.bitrate/1000,
							float("%.2f" % (songObj.filesize/1024.0**2)),
							float("%.2f" % (songObj.final_filesize/1024.0**2)),
							songObj.duration, songObj.score, songObj.source, songObj.url]
			self.searchTableModel.addRow(rowData)
		elif songObj and not songObj.filesize and songObj.source == 'youtube':
			log.error("Youtube wasn't parsed correctly (filesize=0). search string: %s, videoid: %s" % (songObj.searchString, songObj.videoid))
			
	def update_download_table(self, songObj):
		#pass pass pass
		if songObj and songObj.score >= config.relevance_minimum and not songObj.url in [x.url for x in self.songsObjs] and songObj.filesize:
			self.songsObjs.append(songObj)
			log.debug("New SongObj created: %s" % repr(songObj))
			
			# If the filesize and final_filesize are equal, there is no video and
			# no conversation. Therefore, "Video Filesize" needs to be set to None.
			if songObj.filesize == songObj.final_filesize:
				rowData = [songObj.title, songObj.artist, songObj.bitrate/1000, 0,
							float("%.2f" % (songObj.filesize/1024.0**2)),
							songObj.duration, songObj.score, songObj.source, songObj.url]
			else:
				rowData = [songObj.title, songObj.artist, songObj.bitrate/1000,
							float("%.2f" % (songObj.filesize/1024.0**2)),
							float("%.2f" % (songObj.final_filesize/1024.0**2)),
							songObj.duration, songObj.score, songObj.source, songObj.url]
			self.searchTableModel.addRow(rowData)
		elif songObj and not songObj.filesize and songObj.source == 'youtube':
			log.error("Youtube wasn't parsed correctly (filesize=0). search string: %s, videoid: %s" % (songObj.searchString, songObj.videoid))

	def update_dl_progress_bar(self, i, dlRate, eta, currentBytes, filesize):
		"updates download progress bar"
		
		eta_s = eta % 60
		eta_m = eta / 60
		
		if filesize < 0:
			filesize += 2 * (sys.maxint + 1) # fix int overflow. will work with files up to 4GB.
		
		self.prg_bar.setValue(i)
		if dlRate/1024**2 > 1: # If dlRate is in MBs
			if eta:
				if eta_m:
					self.status_txt.setText(tr("Downloading @ %.2f MB/s, %d:%.2d left... [%s/%s MB]") % (dlRate/1024**2, eta_m, eta_s, "{:,.2f}".format(currentBytes/1024.0**2), "{:,.2f}".format(filesize/1024.0**2)))
				else:
					self.status_txt.setText(tr("Downloading @ %.2f MB/s, %ds left... [%s/%s MB]") % (dlRate/1024**2, eta, "{:,.2f}".format(currentBytes/1024.0**2), "{:,.2f}".format(filesize/1024.0**2)))
			else:
				self.status_txt.setText(tr("Downloading @ %.2f MB/s... [%s/%s MB]") % (dlRate/1024**2, "{:,.2f}".format(currentBytes/1024.0**2), "{:,.2f}".format(filesize/1024.0**2)))
		else: # If dlRate is in KBs
			if eta:
				if eta_m:
					self.status_txt.setText(tr("Downloading @ %.2f KB/s, %d:%.2d left... [%s/%s MB]") % (dlRate/1024, eta_m, eta_s, "{:,.2f}".format(currentBytes/1024.0**2), "{:,.2f}".format(filesize/1024.0**2)))
				else:
					self.status_txt.setText(tr("Downloading @ %.2f KB/s, %ds left... [%s/%s MB]") % (dlRate/1024, eta, "{:,.2f}".format(currentBytes/1024.0**2), "{:,.2f}".format(filesize/1024.0**2)))
			else:
				self.status_txt.setText(tr("Downloading @ %.2f KB/s... [%s/%s MB]") % (dlRate/1024, "{:,.2f}".format(currentBytes/1024.0**2), "{:,.2f}".format(filesize/1024.0**2)))
		
	def update_enc_progress_bar(self, i):
		"updates download progress bar"
		self.prg_bar.setValue(i)
		
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
		self.trimSilence_checkbox.setEnabled(True)
		# self.dl_button.setEnabled(True)
		self.dl_cancel_button.setEnabled(False)
		
		if not self.search_thread.isRunning() and not self.thread3.isRunning():
			self.status_gif.setVisible(False)
			
	def disableDownloadUi(self):
		self.downloadAudio_checkbox.setEnabled(False)
		self.downloadVideo_checkbox.setEnabled(False)
		self.trimSilence_checkbox.setEnabled(False)
		# self.dl_button.setEnabled(False)
		self.dl_cancel_button.setEnabled(True)
		self.status_gif.setVisible(True)
			
	def enableStatusGif(self):
		self.status_gif.setVisible(True)
	
	def disableStatusGif(self):
		if not self.search_thread.isRunning() and not self.thread3.isRunning():
			self.status_gif.setVisible(False)
		
	def setID3Tags(self, songObj, ID3TagsToEdit):
		"Function sets ID3 Tags"
		log.debug("Saving ID3 data to file...")
		audio_path = os.path.join(config.dl_dir, songObj.GetProperFilename('mp3'))
		if not os.path.exists(audio_path):
			log.error('audio_path does not exist: %s' % audio_path)
			QtGui.QMessageBox.critical(self, tr("Error"), tr("We couldn't save the ID3 data. We advise you to get in contact with the developer of this software and send him the debug data."), QtGui.QMessageBox.Ok)
		utils.setID3Tags(ID3TagsToEdit, audio_path)
	
	def renameFilesByID3(self, songObj, ID3TagsToEdit):
		"Renames files by ID3 data"
		old_audio_path = os.path.join(config.dl_dir, songObj.GetProperFilename('mp3'))
		old_video_path = os.path.join(config.dl_dir, songObj.GetProperFilename())
			
		if 'TPE1' in ID3TagsToEdit and ID3TagsToEdit['TPE1'].text[0]:
			songObj.artist = ID3TagsToEdit['TPE1'].text[0]
		if 'TIT2' in ID3TagsToEdit and ID3TagsToEdit['TIT2'].text[0]:
			songObj.title = ID3TagsToEdit['TIT2'].text[0]
			
		new_audio_path = os.path.join(config.dl_dir, songObj.GetProperFilename('mp3'))
		new_video_path = os.path.join(config.dl_dir, songObj.GetProperFilename())
		
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
			
		elif config.downloadVideo and old_video_path.lower() != new_video_path.lower() and songObj.source == 'youtube':
			if os.path.exists(new_video_path):
				os.unlink(new_video_path)
			try:
				shutil.move(old_video_path, new_video_path)
			except shutil.Error:
				log.error(traceback.format_exc())
				log.debug("Got shutil.Error, Not Changing filenames...")
			log.debug("Renaming %s to %s..." % (old_video_path, new_video_path))
			
		else:
			log.debug("Names remained the same. Not Changing filenames...")
	
	def runPostDownloadTasks(self, tasks):
		"Function runs the post-download tasks"
		# could be runMultimedia, openDir, addItunes, addPlaylist, ask
		if len(tasks)>1:
			w = PostDownloadWindow.MainWin(tasks)
			w.exec_()
		else:
			songObj = tasks[0].songObj
			
			act = config.post_download_action
			log.debug("post-download action is %s." % act)
			video_path = os.path.join(config.dl_dir, songObj.GetProperFilename())
			audio_path = os.path.join(config.dl_dir, songObj.GetProperFilename('mp3'))
			isMultimediaFile = False if "non-multimedia" in songObj.source.lower() else True
			
			try:
				assert (config.downloadAudio and os.path.exists(audio_path)) or (config.downloadVideo and os.path.exists(video_path) or (not isMultimediaFile and os.path.exists(video_path)))
				if act == 'ask':
					w = PostDownloadWindow.MainWin(tasks)
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
				w = PostDownloadWindow.MainWin(tasks)
				w.exec_()
		
		if config.show_supportArtists_notice:
			if time.time() > config.last_supportArtists_notice_timestamp + config.interval_between_supportArtists_notices:
				w = SupportArtistsWindow.MainWin()
				w.exec_()
				config.last_supportArtists_notice_timestamp = time.time()

	def updatePlayerLength(self, t):
		t = t/1000
		m = t/60
		s = t-m*60
		self.mediaTimer.setText('%02d:%02d' % (m, s))
		
	def searchTable_rightclick_popup(self, pos):
		if not self.searchTable.selectedIndexes():
			return
			
		selectedRows = utils.qt.selectedRowsIndexes(self.searchTable.selectedIndexes())
		urls = [str(index.data(QtCore.Qt.UserRole).toString()) for index in selectedRows]
		
		songObjs = []
		for url in urls:
			songObjs.append([x for x in self.songsObjs if x.url == url][0])
			
		if len(songObjs) > 1:
			# If more than one song is selected
			menu = QtGui.QMenu()
			act_dl = menu.addAction(tr("Download"))
			action = menu.exec_(self.searchTable.mapToGlobal(pos))
			
			if action == act_dl:
				self.download_slot(songObjs)
		else:
			# If only one song is selected
			songObj = songObjs[0]
			
			menu = QtGui.QMenu()
			act_listen = menu.addAction(tr("Listen"))
			act_dl = menu.addAction(tr("Download"))
			act_copyurl = menu.addAction(tr("Copy Url"))
			act_copyname = menu.addAction(tr("Copy Song Name"))
			if songObj.webpage_url:
				act_copywatchurl = menu.addAction(tr("Copy Watch Url"))
				act_openwatchurl = menu.addAction(tr("Open Watch Url"))
			act_copyall = menu.addAction(tr("Copy Developer Data"))
			
			clipboard = QtGui.QApplication.clipboard()
			action = menu.exec_(self.searchTable.mapToGlobal(pos))
			
			if action == act_listen:
				self.listen_slot()
			if action == act_dl:
				self.download_slot(songObj)
			if action == act_copyurl:
				clipboard.setText(songObj.url)
			if action == act_copyname:
				if songObj.artist and songObj.title:
					clipboard.setText("%s - %s" % (songObj.artist, songObj.title))
				elif songObj.title:
					clipboard.setText(songObj.title)
			if action == act_copyall:
				clipboard.setText(pprint.pformat(songObj.__dict__))
			if songObj.webpage_url:
				if action == act_copywatchurl:
					clipboard.setText(songObj.webpage_url)
				if action == act_openwatchurl:
					webbrowser.open(songObj.webpage_url)
		
	def closeEvent(self, event=None):
		"Runs when the widget is closed"
		if hasattr(self, 'search_thread') and self.search_thread.isRunning():
			self.search_thread.terminate()
		if hasattr(self, 'dl_thread') and self.dl_thread.isRunning():
			self.dl_thread.terminate()
		if hasattr(self, 'player'):
			self.player.clear()
			
class TableModelInterface(QtCore.QAbstractTableModel):
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

class SearchTableModel(TableModelInterface):
	def __init__(self, datain, headerdata, parent=None, *args): 
		TableModelInterface.__init__(self, datain, headerdata, parent, *args)

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
			
		if role == QtCore.Qt.TextAlignmentRole:
			return QtCore.Qt.AlignCenter
			
		if index.column() == 6: # If score column
			if role == QtCore.Qt.DecorationRole:
				value = math.ceil(value*2)/2
				pix_list = []
				
				for i in range(int(value)):
					pix_list.append(QtGui.QPixmap(os.path.join('pics', 'fullstar.png')))
				if not value.is_integer():
					pix_list.append(QtGui.QPixmap(os.path.join('pics', 'halfstar.png')))
				for i in range(5-int(math.ceil(value))):
					pix_list.append(QtGui.QPixmap(os.path.join('pics', 'emptystar.png')))
				
				pix = utils.qt.combine_pixmaps(pix_list)
				if app.isRightToLeft() and value != 0 and value != 5: # If the app is in RTL mode, we need to reverse the pixmap
					pix = pix.transformed(QtGui.QTransform().scale(-1, 1))
				return pix
			else:
				return QtCore.QVariant()
				
		if role != QtCore.Qt.DisplayRole:
			return QtCore.QVariant()
			
		if value:
			if index.column() == 3 or index.column() == 4: # if video/audio size
				value = "{:,.2f}".format(value)
			elif index.column() == 5: # if source length
				if value > 60**2: # more than an hour
					value = "%.1d:%.2d:%.2d" % (value/60**2, (value%60**2)/60, (value%60**2)%60)
				else:
					value = "%.1d:%.2d" % (value/60, value%60)
			elif index.column() == 7: # if source column
				value = value.capitalize()
		else:
			value = '-----'
			
		return QtCore.QVariant(value)
		
class DownloadTableModel(TableModelInterface):
	def __init__(self, datain, headerdata, parent=None, *args): 
		TableModelInterface.__init__(self, datain, headerdata, parent, *args)
	
	def data(self, index, role): 
		if not index.isValid():
			return QtCore.QVariant()
			
		value = self.arraydata[index.row()][index.column()]

		if role == QtCore.Qt.UserRole:
			return self.arraydata[index.row()][0] # Index
		
		if role == QtCore.Qt.BackgroundRole:
			if index.row() % 2:
				return QtCore.QVariant(QtGui.QBrush(QtGui.QColor(*config.table_odd_color)))
			else:
				return QtCore.QVariant(QtGui.QBrush(QtGui.QColor(*config.table_even_color)))
		
		if role == QtCore.Qt.ForegroundRole:
			return QtCore.QVariant(QtGui.QBrush(QtGui.QColor(*config.table_foreground_color)))
			
		if role == QtCore.Qt.TextAlignmentRole:
			return QtCore.Qt.AlignCenter
		
		if role != QtCore.Qt.DisplayRole:
			return QtCore.QVariant()
			
		if value:
			if index.column() == 1: # if index
				value = "#%d" % (value+1)
			if index.column() == 4: # if video/audio size
				value = "{:,.2f}".format(value)
		else:
			value = '-----'
			
		return QtCore.QVariant(value)

if __name__ == '__main__':
	# Setup Environment
	if '__file__' in vars():
		os.chdir(utils.module_path(__file__))
	else:
		os.chdir(utils.module_path())
	logger.start(config)
	sys.excepthook = Main.my_excepthook
	sys.stderr = sys.__stderr__ # Here until youtube-dl issue #1963 will be fixed
	warnings.simplefilter('ignore')
	
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
				qm_path = os.path.join('ts', '%s.qm' % QtCore.QLocale.system().name())
				if not os.path.exists(qm_path):
					log.error('QM file was not found: %s' % qm_path)
					
				trans.load(qm_path)
				qt_trans.load(os.path.join("ts", "qt_" + QtCore.QLocale.system().name()[:2]))
				
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
			else:
				log.debug('Setting language as en_US')
				config.lang = 'en_US'
					
		elif config.lang == 'en_US':
			app.setLayoutDirection(QtCore.Qt.LeftToRight)
			
			# Remove translators, if exist
			try:
				app.removeTranslator(trans)
			except:
				pass
			try:
				app.removeTranslator(qt_trans)
			except:
				pass

		elif config.lang != 'en_US':
			trans = QtCore.QTranslator()
			qt_trans = QtCore.QTranslator()
			
			qm_path = os.path.join('ts', '%s.qm' % config.lang)
			if not os.path.exists(qm_path):
				log.error('QM file was not found: %s' % qm_path)
				
			trans.load(qm_path)
			qt_trans.load(os.path.join('ts', 'qt_' + config.lang[:2]))
			
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
				p = utils.launch_without_console(r'del /S /Q "%s"' % config.temp_dir, shell=True)
				p.wait()
			sys.exit(exitcode)