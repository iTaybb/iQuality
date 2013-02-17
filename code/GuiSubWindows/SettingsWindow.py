# Copyright (C) 2012-2013 Itay Brandes 

''' Settings Window '''

import os.path
import re

from PyQt4 import QtCore
from PyQt4 import QtGui

import Config; config = Config.config
from logger import log
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, parent=None):
		super(MainWin, self).__init__(parent)
		
		self.setWindowTitle(tr("Preferences"))
		self.resize(400, 60)
		self.setWindowIcon(QtGui.QIcon(r'pics\settings.png'))
		self.init_widgets()
		
	def init_widgets(self):
		self.dl_dir = QtGui.QLineEdit(config.dl_dir)
		self.folder_button = QtGui.QPushButton(tr("Choose Folder"))
		self.folder_button.clicked.connect(self.slot_choose_dl_dir)
		self.temp_dir = QtGui.QLineEdit(config.temp_dir)
		self.temp_folder_button = QtGui.QPushButton(tr("Choose Folder"))
		self.temp_folder_button.clicked.connect(self.slot_choose_temp_dir)
		self.post_download_action = QtGui.QComboBox()
		self.post_download_action.addItems(map(tr, config.post_download_action_dict.values()))
		self.post_download_action.setCurrentIndex(config.post_download_action_dict.keys().index(config.post_download_action))
		self.post_download_action.currentIndexChanged.connect(self.slot_post_download_action_changed)
		
		# These labels and lineedits are set by self.slot_changed_checkbox
		self.post_download_custom_label = QtGui.QLabel()
		self.post_download_custom_label2 = QtGui.QLabel()
		self.post_download_custom_cmd = QtGui.QLineEdit()
		self.post_download_custom_wait_checkbox = QtGui.QCheckBox(tr("Wait for exit"))
		self.post_download_custom_wait_checkbox.setCheckState(config.post_download_custom_wait_checkbox)
		self.post_download_custom_wait_checkbox.setTristate(False)
		
		self.table_doubleClick_action = QtGui.QComboBox()
		self.table_doubleClick_action.addItems(map(tr, config.table_doubleClick_action_dict.values()))
		self.table_doubleClick_action.setCurrentIndex(config.table_doubleClick_action_dict.keys().index(config.table_doubleClick_action))
		
		self.enableSpellCheck = QtGui.QCheckBox(tr("Enable Spell Check"))
		self.enableSpellCheck.setCheckState(config.enableSpellCheck)
		self.enableSpellCheck.setTristate(False)
		self.prefetch_charts = QtGui.QCheckBox(tr("Fetch song charts at startup"))
		self.prefetch_charts.setCheckState(config.prefetch_charts)
		self.prefetch_charts.setTristate(False)
		self.artist_lookup = QtGui.QCheckBox(tr("Look for discography"))
		self.artist_lookup.setCheckState(config.artist_lookup)
		self.artist_lookup.setTristate(False)
		self.lyrics_lookup = QtGui.QCheckBox(tr("Search for a song by it's lyrics"))
		self.lyrics_lookup.setCheckState(config.lyrics_lookup)
		self.lyrics_lookup.setTristate(False)
		self.search_autocomplete = QtGui.QCheckBox(tr("Search Auto-completion"))
		self.search_autocomplete.setCheckState(config.search_autocomplete)
		self.search_autocomplete.setTristate(False)
		self.parse_links_from_clipboard_at_startup = QtGui.QCheckBox(tr("Parse links from clipboard at startup"))
		self.parse_links_from_clipboard_at_startup.setCheckState(config.parse_links_from_clipboard_at_startup)
		self.parse_links_from_clipboard_at_startup.setTristate(False)
		self.editID3 = QtGui.QCheckBox(tr("Modify ID3 Tags"))
		self.editID3.setCheckState(config.editID3)
		self.editID3.setTristate(False)
		self.editID3.stateChanged.connect(self.slot_changed_checkbox)
		
		self.label1 = QtGui.QLabel(tr("ID3 is a metadata container for MP3 files, which allows for information like the title, artist, album, album art and\nlyrics to be stored on the file itself and later viewed by any modern multimedia player, such as iPod, Windows\nMedia Player and Android phones.\n\niQuality can fetch ID3 tags from the web automatically."))
		# id3_action's values are noask, ask, ask_albumart'
		self.label2 = QtGui.QLabel(tr('After Fetching:'))
		self.id3_autoclose = QtGui.QComboBox()
		self.id3_autoclose.addItems([tr('Leave window open for editing'), tr('Close window while saving changes')])
		if config.id3_action == 'noask':
			self.id3_autoclose.setCurrentIndex(1)
		else:
			self.id3_autoclose.setCurrentIndex(0)
		self.id3_autoclose.currentIndexChanged.connect(self.slot_id3_autoclose_action_changes)
		
		self.label3 = QtGui.QLabel(tr('AlbumArt:'))
		self.id3_autoalbumart = QtGui.QComboBox()
		self.id3_autoalbumart.addItems([tr('Let me choose it'), tr('Choose it automatically for me')])
		if config.id3_action == 'ask_albumart':
			self.id3_autoclose.setCurrentIndex(0)
		else:
			self.id3_autoalbumart.setCurrentIndex(1)
		 
		self.useDilandau = QtGui.QCheckBox(tr("Use %s") % "Dilandau")
		self.useDilandau.setCheckState(config.search_sources['Dilandau'])
		self.useDilandau.setTristate(False)
		self.useMp3Skull = QtGui.QCheckBox(tr("Use %s") % "Mp3Skull")
		self.useMp3Skull.setCheckState(config.search_sources['Mp3skull'])
		self.useMp3Skull.setTristate(False)
		self.useSoundcloud = QtGui.QCheckBox(tr("Use %s") % "SoundCloud")
		self.useSoundcloud.setCheckState(config.search_sources['soundcloud'])
		self.useSoundcloud.setTristate(False)
		self.useYoutube = QtGui.QCheckBox(tr("Use %s") % "Youtube")
		self.useYoutube.setCheckState(config.search_sources['youtube'])
		self.useYoutube.setTristate(False)
		self.useYoutube.stateChanged.connect(self.slot_changed_checkbox)
		self.prefered_youtube_format = QtGui.QComboBox()
		self.prefered_youtube_format.addItems(config.youtube_formats_priority)
		self.label_youtube_format = QtGui.QLabel(tr("Prefered Video Format:"))
		self.prefer720p = QtGui.QCheckBox(tr("Prefer 720p over 1080p"))
		self.prefer720p.setCheckState(not 'hd1080' in config.youtube_quality_priority)
		self.prefer720p.setTristate(False)
		
		self.songs_count_spinBox = QtGui.QSpinBox()
		self.songs_count_spinBox.setMaximum(25)
		self.songs_count_spinBox.setMinimum(5)
		self.songs_count_spinBox.setValue(config.songs_count_spinBox)
		
		self.score_spinBox = QtGui.QDoubleSpinBox()
		self.score_spinBox.setMinimum(0.0)
		self.score_spinBox.setMaximum(5.0)
		self.score_spinBox.setSingleStep(0.5)
		self.score_spinBox.setValue(config.relevance_minimum)

		self.slot_changed_checkbox()
		
		# General Tab
		layout0 = QtGui.QHBoxLayout()
		layout0.addWidget(QtGui.QLabel(tr("Download Dir:")))
		layout0.addWidget(self.dl_dir)
		layout0.addWidget(self.folder_button)
		
		layout1 = QtGui.QHBoxLayout()
		layout1.addWidget(QtGui.QLabel(tr("Post-Download Action:")))
		layout1.addWidget(self.post_download_action)
		layout1.addSpacerItem(QtGui.QSpacerItem(450, 10))
		layout15 = QtGui.QHBoxLayout()
		layout15.addWidget(self.post_download_custom_label2)
		layout15.addWidget(self.post_download_custom_cmd)
		layout15.addWidget(self.post_download_custom_wait_checkbox)
		
		generalTab = QtGui.QWidget()
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		generalLayout = QtGui.QVBoxLayout()
		generalLayout.addLayout(layout0)
		generalLayout.addLayout(layout1)
		generalLayout.addLayout(layout15)
		generalLayout.addWidget(self.post_download_custom_label)
		generalLayout.addSpacerItem(QtGui.QSpacerItem(100, 100))
		generalTab.setLayout(generalLayout)
		
		# Media Sources Tab
		mediaSourcesGroupBox = QtGui.QVBoxLayout()
		layout2 = QtGui.QHBoxLayout()
		layout2.addWidget(self.useDilandau)
		layout2.addWidget(self.useMp3Skull)
		layout2.addWidget(self.useSoundcloud)
		layout3 = QtGui.QHBoxLayout()
		layout3.addWidget(self.useYoutube)
		layout3.addWidget(self.prefer720p)
		layout3.addWidget(self.label_youtube_format)
		layout3.addWidget(self.prefered_youtube_format)
		mediaSourcesGroupBox.addLayout(layout2)
		mediaSourcesGroupBox.addLayout(layout3)
		
		id3GroupBox = QtGui.QGroupBox(tr("ID3 Tags"))
		lay = QtGui.QGridLayout()
		layout4 = QtGui.QHBoxLayout()
		layout4.addWidget(self.editID3)
		layout4.addWidget(self.label2)
		layout4.addWidget(self.id3_autoclose)
		layout4.addWidget(self.label3)
		layout4.addWidget(self.id3_autoalbumart)
		lay.addWidget(self.label1, 0, 0)
		lay.addLayout(layout4, 1, 0)
		id3GroupBox.setLayout(lay)
		
		mediaSourcesTab = QtGui.QWidget()
		mediaSourcesLayout = QtGui.QVBoxLayout()
		mediaSourcesLayout.addLayout(mediaSourcesGroupBox)
		mediaSourcesLayout.addWidget(id3GroupBox)
		mediaSourcesTab.setLayout(mediaSourcesLayout)
		
		# Etc Tab
		etcTab = QtGui.QWidget()
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		etcLayout = QtGui.QGridLayout()
		etcLayout.addWidget(QtGui.QLabel(tr("Temp Files Directory:")), 0, 0, 1, 1)
		etcLayout.addWidget(self.temp_dir, 0, 1, 1, 2)
		etcLayout.addWidget(self.temp_folder_button, 0, 3, 1, 1)
		etcLayout.addWidget(QtGui.QLabel(tr("Table DoubleClick Action:")), 1, 0)
		etcLayout.addWidget(self.table_doubleClick_action, 1, 1)
		etcLayout.addWidget(QtGui.QLabel(tr("Num. of songs:")), 2, 0)
		etcLayout.addWidget(self.songs_count_spinBox, 2, 1)
		etcLayout.addWidget(QtGui.QLabel(tr("Min. Score:")), 3, 0)
		etcLayout.addWidget(self.score_spinBox, 3, 1)
		etcLayout.addWidget(self.artist_lookup, 4, 0)
		etcLayout.addWidget(self.lyrics_lookup, 4, 1)
		etcLayout.addWidget(self.parse_links_from_clipboard_at_startup, 4, 2)
		etcLayout.addWidget(self.enableSpellCheck, 5, 0)
		etcLayout.addWidget(self.prefetch_charts, 5, 1)
		etcLayout.addWidget(self.search_autocomplete, 5, 2)
		etcTab.setLayout(etcLayout)
		
		# Row Layouts
		buttonLayout = QtGui.QHBoxLayout()
		applyButton = QtGui.QPushButton(tr("Apply"))
		applyButton.clicked.connect(self.slot_apply)
		closeButton = QtGui.QPushButton(tr("Dismiss"))
		closeButton.clicked.connect(self.close)
		restoreButton = QtGui.QPushButton(tr("(*) Restore to Default Settings"))
		restoreButton.clicked.connect(self.slot_restore)
		
		buttonLayout.addWidget(applyButton)
		buttonLayout.addWidget(closeButton)
		buttonLayout.addWidget(restoreButton)
		
		# Form Layout
		tabWidget = QtGui.QTabWidget()
		tabWidget.addTab(generalTab, tr("General"))
		tabWidget.addTab(mediaSourcesTab, tr("Media Sources + ID3"))
		tabWidget.addTab(etcTab, tr("Advanced"))
		
		mainLayout = QtGui.QVBoxLayout()
		mainLayout.addWidget(tabWidget)
		mainLayout.addWidget(QtGui.QLabel(tr("<h3>* Must restart the application to apply.</h3>")))
		mainLayout.addLayout(buttonLayout)
		
		self.setLayout(mainLayout)
		
	def slot_choose_dl_dir(self):
		dialog = QtGui.QFileDialog()
		dialog.setFileMode(QtGui.QFileDialog.Directory)
		dialog.setDirectory(self.dl_dir.displayText())
		dl_dir = unicode(dialog.getExistingDirectory(options=QtGui.QFileDialog.ShowDirsOnly))
		dl_dir = dl_dir.replace('/','\\')
		
		if dl_dir:
			if utils.get_free_space(dl_dir) < 200*1024**2: # 200 MB
				log.warning("The Directory has less than 200 MB available. Application may not function properly.")
				QtGui.QMessageBox.warning(self, tr("Warning"), tr("The Directory has less than 200 MB available. Application may not function properly."), QtGui.QMessageBox.Ok)
			log.debug("dl_dir is set to: %s" % dl_dir)
			self.dl_dir.setText(dl_dir)
			
	def slot_choose_temp_dir(self):
		dialog = QtGui.QFileDialog()
		dialog.setFileMode(QtGui.QFileDialog.Directory)
		dialog.setDirectory(self.temp_dir.displayText())
		temp_dir = unicode(dialog.getExistingDirectory(options=QtGui.QFileDialog.ShowDirsOnly))
		temp_dir = temp_dir.replace('/','\\')
		
		if temp_dir:
			if utils.get_free_space(temp_dir) < 200*1024**2: # 200 MB
				log.warning("The Directory has less than 200 MB available. Application may not function properly.")
				QtGui.QMessageBox.warning(self, tr("Warning"), tr("The Directory has less than 200 MB available. Application may not function properly."), QtGui.QMessageBox.Ok)
			log.debug("temp_dir is set to: %s" % temp_dir)
			self.temp_dir.setText(temp_dir)
	
	def slot_changed_checkbox(self, state=None):
		if config.post_download_action == 'customLaunch':
			self.post_download_custom_label2.setText(tr("Command:"))
			self.post_download_custom_cmd.setEnabled(True)
			self.post_download_custom_label2.setEnabled(True)
			self.post_download_custom_wait_checkbox.setEnabled(True)
			
			if config.post_download_custom_cmd:
				self.post_download_custom_cmd.setText(config.post_download_custom_cmd)
			else:
				self.post_download_custom_cmd.setText(r'"C:\Program Files\AnyApp\encoder.exe" -i "%AUDIO%" -o C:\Encoded\song.mp3')
			
			self.post_download_custom_label.setText(tr("You may use the %AUDIO% var in the command. Will be launched only on audio songs."))
			
		elif config.post_download_action == 'addPlaylist':
			self.post_download_custom_label2.setText(tr("Playlist Path:"))
			
			if config.post_download_playlist_path:
				self.post_download_custom_cmd.setText(config.post_download_playlist_path)
			else:
				log.error("in config.post_download_action after sanity check, however playlist path is not valid")
			
			
			self.post_download_custom_cmd.setEnabled(True)
			self.post_download_custom_label2.setEnabled(True)
			self.post_download_custom_label.setText(tr("Supported Playlist Files are .m3u and .wpl."))
			self.post_download_custom_wait_checkbox.setEnabled(False)
			
		else:
			self.post_download_custom_label2.setText(tr("Command:"))
			self.post_download_custom_cmd.setEnabled(False)
			self.post_download_custom_label2.setEnabled(False)
			self.post_download_custom_wait_checkbox.setEnabled(False)
			
			if config.post_download_custom_cmd:
				self.post_download_custom_cmd.setText(config.post_download_custom_cmd)
			else:
				self.post_download_custom_cmd.setText(r'"C:\Program Files\AnyApp\encoder.exe" -i "%AUDIO%" -o C:\Encoded\song.mp3')
				
			self.post_download_custom_label.setText(tr("<i>The command line is disabled because it is not set as the post-download action.</i>"))
			
		if not self.useYoutube.isChecked():
			self.prefered_youtube_format.setEnabled(False)
			self.label_youtube_format.setEnabled(False)
			self.prefer720p.setEnabled(False)
		else:
			self.prefered_youtube_format.setEnabled(True)
			self.label_youtube_format.setEnabled(True)
			self.prefer720p.setEnabled(True)
			
		if not self.editID3.isChecked():
			self.label2.setEnabled(False)
			self.id3_autoclose.setEnabled(False)
			self.label3.setEnabled(False)
			self.id3_autoalbumart.setEnabled(False)
		else:
			self.label2.setEnabled(True)
			self.id3_autoclose.setEnabled(True)
			if self.id3_autoclose.currentIndex() == 1: # if noask
				self.label3.setEnabled(False)
				self.id3_autoalbumart.setEnabled(False)
			else:
				self.label3.setEnabled(True)
				self.id3_autoalbumart.setEnabled(True)
	
	def slot_id3_autoclose_action_changes(self, i):
		if i == 1 and self.id3_autoalbumart.currentIndex() == 0:
		# if autoclose is True and albumart is set to "ask user", we should change it to "do it automatically", as if the window is closing itself automatically, it can't ask the user for input.
			self.id3_autoalbumart.setCurrentIndex(1)
		self.slot_changed_checkbox()
			
	def slot_post_download_action_changed(self, i):
		val = config.post_download_action_dict.keys()[i]
		if val == 'addItunes' and not config.is_itunes_installed:
			QtGui.QMessageBox.critical(self, tr("Error"), tr("iTunes is not installed on this system."), QtGui.QMessageBox.Ok)
			self.post_download_action.setCurrentIndex(config.post_download_action_dict.keys().index(config.post_download_action))
		elif val == 'addPlaylist':
			dialog = QtGui.QFileDialog()
			dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
			if config.post_download_playlist_path:
				dialog.setDirectory(os.path.dirname(config.post_download_playlist_path))
			else:
				dialog.setDirectory(os.path.expanduser(r'~\My Documents\My Music\My Playlists')) # The default playlist directory
			
			f = unicode(dialog.getOpenFileName(caption=tr("Open Playlist"), filter=tr("Supported Playlist Files") + " (*.m3u *.wpl)"))
			f = f.replace('/','\\')
			
			if f:
				config.post_download_playlist_path = f
			elif not config.post_download_playlist_path:
				# if new playlist is not choosed, and there is NO playlist path in the config file, we should revert the post_download_action to the last one.
				self.post_download_action.setCurrentIndex(config.post_download_action_dict.keys().index(config.post_download_action))
				return
		
		config.post_download_action = val
		self.slot_changed_checkbox()
	
	def slot_apply(self):
		### SANITY CHECKS ###
		if config.post_download_action == 'addPlaylist':
			pl_path = unicode(self.post_download_custom_cmd.displayText()).strip()
			if not pl_path or pl_path.count('"')%2 != 0 or not os.path.exists(pl_path):
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Your Post-Download action is \"Add to a Playlist\", however the path is empty, malformed or does not exist."), QtGui.QMessageBox.Ok)
				return
		
		if config.post_download_action == 'customLaunch':
			cmd = unicode(self.post_download_custom_cmd.displayText()).strip()
			if not cmd or cmd.count('"')%2 != 0:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Your Post-Download action is \"Run an application\", however the command line is empty or malformed."), QtGui.QMessageBox.Ok)
				return
			
			if cmd[0] == '"':
				exe_path = cmd.split('"')[1]
			else:
				exe_path = cmd.split()[0]
			if not os.path.exists(exe_path):
				QtGui.QMessageBox.critical(self, tr("Error"), tr("Your Post-Download action is \"Run an application\", however the application \"%s\" could not be found.") % exe_path, QtGui.QMessageBox.Ok)
				return
		
		if not any([self.useDilandau.isChecked(), self.useMp3Skull.isChecked(), self.useYoutube.isChecked(), self.useSoundcloud.isChecked()]):
			QtGui.QMessageBox.critical(self, tr("Error"), tr("All media sources are disabled. Please choose at least one."), QtGui.QMessageBox.Ok)
			return
			
		if not re.search(r'^([a-zA-Z]:)?(\\[^<>:"/\\|?*]+)+\\?$', self.dl_dir.displayText()): # valid path regex
			QtGui.QMessageBox.critical(self, tr("Error"), tr("The filename, directory name, or volume label syntax is incorrect. Please specify a valid download directory."), QtGui.QMessageBox.Ok)
			return
			
		if not re.search(r'^([a-zA-Z]:)?(\\[^<>:"/\\|?*]+)+\\?$', self.temp_dir.displayText()): # valid path regex
			QtGui.QMessageBox.critical(self, tr("Error"), tr("The filename, directory name, or volume label syntax is incorrect. Please specify a valid temp directory."), QtGui.QMessageBox.Ok)
			return
		
		### SAVING ###
		log.debug("Saving New Preferences...")
		config.dl_dir = unicode(self.dl_dir.displayText()).strip()
		config.table_doubleClick_action = config.table_doubleClick_action_dict.keys()[self.table_doubleClick_action.currentIndex()]
		config.post_download_action = config.post_download_action_dict.keys()[self.post_download_action.currentIndex()] # perhaps not needed, as config.post_download_action is saved at each post_download_action_changed event.
		if config.post_download_action == 'customLaunch':
			config.post_download_custom_cmd = unicode(self.post_download_custom_cmd.displayText()).strip()
		if config.post_download_action == 'addPlaylist':
			config.post_download_playlist_path = unicode(self.post_download_custom_cmd.displayText()).strip()
		if self.id3_autoclose.currentIndex() == 1:
			config.id3_action = 'noask'
		elif self.id3_autoalbumart.currentIndex() == 1:
			config.id3_action = 'ask'
		else:
			config.id3_action = 'ask_albumart'
		config.search_autocomplete = self.search_autocomplete.isChecked()
		config.enableSpellCheck = self.enableSpellCheck.isChecked()
		config.search_sources['Dilandau'] = self.useDilandau.isChecked()
		config.search_sources['Mp3skull'] = self.useMp3Skull.isChecked()
		config.search_sources['soundcloud'] = self.useSoundcloud.isChecked()
		config.search_sources['youtube'] = self.useYoutube.isChecked()
		utils.move_item_to_top(str(self.prefered_youtube_format.currentText()), config.youtube_formats_priority)
		
		if self.prefer720p.isChecked():
			if 'hd1080' in config.youtube_quality_priority:
				config.youtube_quality_priority.remove('hd1080')
		else:
			if not 'hd1080' in config.youtube_quality_priority:
				config.youtube_quality_priority.insert(0, 'hd1080')
		config.editID3 = self.editID3.isChecked()
		config.prefetch_charts = self.prefetch_charts.isChecked()
		config.artist_lookup = self.artist_lookup.isChecked()
		config.lyrics_lookup = self.lyrics_lookup.isChecked()
		config.parse_links_from_clipboard_at_startup = self.parse_links_from_clipboard_at_startup.isChecked()
		config.songs_count_spinBox = self.songs_count_spinBox.value()
		config.relevance_minimum = self.score_spinBox.value()
		config.temp_dir = self.temp_dir.displayText()
		config.post_download_custom_wait_checkbox = self.post_download_custom_wait_checkbox.isChecked()
		self.close()
	
	def slot_restore(self):
		log.debug("Restoring Prefenreces to default...")
		config.restoreToDefault()
		QtGui.QMessageBox.information(self, tr("Information"), tr("You must restart the application in order to restore the default settings."), QtGui.QMessageBox.Ok)
		self.close()