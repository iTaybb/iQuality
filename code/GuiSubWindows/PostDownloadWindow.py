# Copyright (C) 2012-2015 Itay Brandes 

''' Post-Download Tasks Window '''

import os.path

from PyQt4 import QtCore
from PyQt4 import QtGui
import pySmartDL

import Config; config = Config.config
from logger import log
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, tasks, parent=None):
		super(MainWin, self).__init__(parent)
		
		self.tasks = tasks
		self.songObj = tasks[0].songObj
		
		self.dl_dir =  config.dl_dir
		self.setWindowTitle(tr("Post Download Window"))
		self.setWindowIcon(QtGui.QIcon(os.path.join('pics', 'kmix.png')))
		
		self.video_path = os.path.join(self.dl_dir, self.songObj.GetProperFilename())
		self.audio_path = os.path.join(self.dl_dir, self.songObj.GetProperFilename('mp3'))
		
		self.isAudio = config.downloadAudio and os.path.exists(self.audio_path)
		self.isVideo = self.video_path != self.audio_path and config.downloadVideo \
						and os.path.exists(self.video_path)
		# the video_path != audio_path is because GetProperFilename returns mp3
		# for a music file, and mp4/flv/webm for a video file. If they both are
		# the same, we have only a music file and no video.
		log.debug('PostDownloadWindow: self.video_path: %s, self.isVideo: %s' % (self.video_path, str(self.isVideo)))
		log.debug('PostDownloadWindow: self.audio_path: %s, self.isAudio: %s' % (self.audio_path, str(self.isAudio)))
		
		if not self.isAudio and not self.isVideo:
			log.error("Error: no audio or video files were found.")
			QtGui.QMessageBox.critical(self, tr("Error"), tr("no audio or video files were found."), QtGui.QMessageBox.Ok)
			self.deleteLater()
		
		self.init_widgets()
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		pixmap = QtGui.QPixmap(os.path.join('pics', 'kmix.png')).scaled(130, 130, transformMode=QtCore.Qt.SmoothTransformation)
		self.pix = QtGui.QLabel()
		self.pix.setPixmap(pixmap)
		
		total_time = sum([task.dl_time+task.dl_encode_time for task in self.tasks])
		total_dl_time = sum([task.dl_time for task in self.tasks])
		total_size = sum([task.songObj.filesize for task in self.tasks])
		
		s = ""
		s += tr('The following file(s) have been downloaded successfully:<br />')
		for i, task in enumerate(self.tasks):
			s += '<font color="purple"><b>%s</b></font><br />' % task.songObj.GetProperName()
			if i >= 2:
				s += tr("(and %d more files)<br />") % (len(self.tasks)-3)
				break
		
		s += tr('Total Filesize is %s. Downloaded within %s.<br /><br />What do you wish to do?') % (pySmartDL.utils.sizeof_human(total_size), tr(pySmartDL.utils.time_human(total_time), split_tr=True))
		
		self.label1 = QtGui.QLabel(s)
		self.label2 = QtGui.QLabel()
		button_runAudio = QtGui.QPushButton(QtGui.QIcon(r'pics\play_audio.png'), tr('Play Audio'))
		button_runAudio.clicked.connect(self.slot_audio)
		button_runVideo = QtGui.QPushButton(QtGui.QIcon(r'pics\play_movie.png'), tr('Play Video'))
		button_runVideo.clicked.connect(self.slot_video)
		button_runDirectory = QtGui.QPushButton(QtGui.QIcon(r'pics\folder.png'), tr('Open Directory'))
		button_runDirectory.clicked.connect(self.slot_dir)
		button_addItunes = QtGui.QPushButton(QtGui.QIcon(r'pics\itunes.png'), tr('Add to iTunes'))
		button_addItunes.clicked.connect(self.slot_itunes)
		if not config.is_itunes_installed:
			button_addItunes.setEnabled(False)
			self.label2.setText(tr('<i>The iTunes button is disabled because iTunes is not installed on this system.</i>'))
		button_addPlaylist = QtGui.QPushButton(QtGui.QIcon(r'pics\playlist.png'), tr('Add to a Playlist'))
		button_addPlaylist.clicked.connect(self.slot_playlist)
		button_close = QtGui.QPushButton(tr('Close'))
		button_close.clicked.connect(self.slot_close)
		
		self.saveSelection_CheckBox = QtGui.QCheckBox(tr("Remember selection and do it automatically next time"))
		self.saveSelection_CheckBox.setCheckState(False)
		self.saveSelection_CheckBox.setTristate(False)
		
		self.facebook_image = QtGui.QLabel()
		self.facebook_image.setPixmap(QtGui.QPixmap(r'pics\like.png'))
		self.facebook_label = QtGui.QLabel(tr('<b>Did you enjoy iQuality? Please <a href="%s">like us on facebook</a>, so your friends can benefit this software as well</b>.') % config.facebook_page)
		self.facebook_label.setOpenExternalLinks(True)
		self.facebookLayout = QtGui.QHBoxLayout()
		self.facebookLayout.addWidget(self.facebook_image)
		self.facebookLayout.addWidget(self.facebook_label)
		
		# Decide which buttons we can show on the screen
		buttons = []
		if len(self.tasks) == 1 and self.isAudio:
			buttons.append(button_runAudio)
		if len(self.tasks) == 1 and self.isVideo:
			buttons.append(button_runVideo)
		buttons.append(button_runDirectory)
		if len(self.tasks) == 1 and self.isAudio:
				buttons.append(button_addItunes)
				buttons.append(button_addPlaylist)
		buttons.append(button_close)
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.pix, 0, 0, 3, 1, alignment = QtCore.Qt.AlignCenter)
		mainLayout.addWidget(self.label1, 0, 1, 1, 3)
		for i, button in enumerate(buttons):
			j = 0 # how much we need to extend the button
			if i == len(buttons)-1: # if last button
				j = 2-i%3 # extend by the remaining space
			mainLayout.addWidget(button, i/3+1, i%3+1, 1, 1+j)
		mainLayout.addWidget(self.saveSelection_CheckBox, 10, 0, 1, 4)
		if self.label2.text(): # If the label is blank, we won't show it
			mainLayout.addWidget(self.label2, 11, 0, 1, 4)
		mainLayout.addLayout(self.facebookLayout, 12, 0, 1, 4)

		self.setLayout(mainLayout)

	def slot_audio(self):
		log.debug("Running %s..." % self.audio_path)
		try:
			os.startfile(self.audio_path)
		except WindowsError, e:
			if e[0] == 1155:
				log.error('WindowsError 1155: No application is associated with the specified file for this operation')
				QtGui.QMessageBox.critical(self, tr("Error"), tr("No application is associated with the specified file for this operation."), QtGui.QMessageBox.Ok)
				return

		if self.saveSelection_CheckBox.isChecked():
			config.post_download_action = 'runMultimedia'
		
		self.close()
		
	def slot_video(self):
		log.debug("Running %s..." % self.video_path)
		os.startfile(self.video_path)
		
		if self.saveSelection_CheckBox.isChecked():
			config.post_download_action = 'runMultimedia'
		
		self.close()
		
	def slot_dir(self):
		if config.downloadAudio and os.path.exists(self.audio_path):
			log.debug("Running explorer with %s selected..." % self.audio_path)
			utils.launch_file_explorer(self.audio_path)
		elif self.video_path != self.audio_path and config.downloadVideo and os.path.exists(self.video_path):
			log.debug("Running explorer with %s selected..." % self.video_path)
			utils.launch_file_explorer(self.video_path)
		else: # doesn't suppose to happen
			log.debug('Running explorer "%s"...' % config.dl_dir)
			os.startfile(config.dl_dir)
		
		if self.saveSelection_CheckBox.isChecked():
			config.post_download_action = 'openDir'
			
		self.close()

	def slot_itunes(self):
		log.debug("Adding %s to the iTunes library..." % self.audio_path)
		utils.add_item_to_itunes_playlist(self.audio_path)
		self.statusBar_append = tr("; Saved to iTunes")
		
		if self.saveSelection_CheckBox.isChecked():
			config.post_download_action = 'addItunes'
			
		self.close()
		
	def slot_playlist(self):
		dialog = QtGui.QFileDialog()
		dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
		if config.post_download_playlist_path:
			dialog.setDirectory(os.path.dirname(config.post_download_playlist_path))
		else:
			# The default playlist directory
			dialog.setDirectory(r'%s\My Documents\My Music\My Playlists' % utils.get_home_dir())
		
		f = unicode(dialog.getOpenFileName(caption=tr("Open Playlist"), filter=tr("Supported Playlist Files") + " (*.m3u *.wpl)"))
		f = f.replace('/','\\')
		
		if f:
			try:
				log.debug("Adding %s to the %s playlist..." % (self.audio_path, f))
				utils.add_item_to_playlist(f, self.audio_path)
				self.statusBar_append = tr("; Saved to playlist")
			except (IOError, RuntimeError), e:
				log.error(str(e))
				QtGui.QMessageBox.critical(self, tr("Error"), str(e), QtGui.QMessageBox.Ok)
				return
				
			config.post_download_playlist_path = f
				
			if self.saveSelection_CheckBox.isChecked():
				config.post_download_action = 'addPlaylist'
			
			self.close()
		
	def slot_close(self):
		if self.saveSelection_CheckBox.isChecked():
			config.post_download_action = 'nothing'
		self.close()
