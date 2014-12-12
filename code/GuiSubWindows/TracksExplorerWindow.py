# Copyright (C) 2012-2015 Itay Brandes 

''' Tracks Explorer Window '''

from PyQt4 import QtCore
from PyQt4 import QtGui

import Config; config = Config.config
from logger import log
from GuiThreads import ArtistLookupThread, AlbumLookupThread
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, artists, parent=None):
		super(MainWin, self).__init__(parent)
		self.artists = artists
		self.artist = self.artists[0].name
		
		self.setWindowTitle(tr("Tracks Explorer - %s") % self.artist)
		self.resize(400, 300)
		self.setWindowIcon(QtGui.QIcon(r'pics\cdaudio.png'))
		
		self.init_widgets()
		
	def spawn_thread(self, s):
		if s == 'release':
			thread = ArtistLookupThread()
			thread.output.connect(self.release_results)
			thread.error.connect(self.slot_error)
		elif s == 'recording':
			thread = AlbumLookupThread()
			thread.output.connect(self.recording_results)
			thread.error.connect(self.slot_error)
		else:
			log.exception('no thread %s')
		
		# the thread object needs to be binded to the window object, else it'll terminate when this function ends
		self.thread = thread
		
		return thread
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		pixmap = QtGui.QPixmap(r'pics\cdaudio.png').scaled(100, 100, transformMode=QtCore.Qt.SmoothTransformation)
		self.pix = QtGui.QLabel()
		self.pix.setPixmap(pixmap)
		
		self.label1 = QtGui.QLabel(tr("You've searched a specific artist name, so we fetched the artist's discography for you.\n\nYou may choose a track from the list below, and iQuality will download it for you."))
		self.label1.setWordWrap(True)
		
		self.treeWidget = QtGui.QTreeWidget()
		self.treeWidget.setHeaderHidden(True)
		self.treeWidget.itemExpanded.connect(self.slot_expended)
		self.treeWidget.itemDoubleClicked.connect(self.slot_clicked)
		
		if len(self.artists) == 1:
			self.spawn_thread('release').search(self.artists[0], self.treeWidget.invisibleRootItem())
		else:	
			for artist in self.artists:
				screen_output = "%s - %s" % (artist.name, artist.disambiguation) if artist.disambiguation else artist.name
				item = self.addArtist(self.treeWidget.invisibleRootItem(), screen_output, artist)

		buttonLayout = QtGui.QHBoxLayout()
		applyButton = QtGui.QPushButton(tr("Choose"))
		applyButton.clicked.connect(self.slot_apply)
		closeButton = QtGui.QPushButton(tr('Dismiss'))
		closeButton.clicked.connect(self.slot_close)
		buttonLayout.addWidget(applyButton)
		buttonLayout.addWidget(closeButton)
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.label1, 0, 0)
		mainLayout.addWidget(self.pix, 0, 1, alignment = QtCore.Qt.AlignCenter)
		mainLayout.addWidget(self.treeWidget, 1, 0, 1, 2)
		mainLayout.addLayout(buttonLayout, 2, 0)
		self.setLayout(mainLayout)
		
	def release_results(self, albums, singles, others, item):
		item.takeChildren()
		
		for album in albums:
			title = album.title
			if album.date:
				year = album.date.split('-')[0]
				title += " (%s)" % year

			self.addAlbum(item, title, album)
		for single in singles:
			self.addTrack(item, single.title, 'track:%s - %s' % (self.artist, single.title))
		
		if not albums and not singles:
			for others in others:
				title = others.title
				if others.date:
					year = others.date.split('-')[0]
					title += " (%s)" % year
				
				self.addAlbum(item, title, others)
			
	def recording_results(self, tracks, item):
		item.takeChildren()
		
		for track in tracks:
			self.addTrack(item, track, 'track:%s - %s' % (self.artist, track))
			
	def slot_error(self, s, item):
		QtGui.QMessageBox.warning(self, tr("Error"), "<h2>%s</h2>" % s, QtGui.QMessageBox.Ok)
		
		item.takeChildren()
		blankItem = QtGui.QTreeWidgetItem(item, [tr('No tracks available.')])
		blankItem.setFlags(QtCore.Qt.NoItemFlags)
		
	def slot_expended(self, item):
		obj = item.data(0, QtCore.Qt.UserRole).toPyObject()
		
		# if there's a "loading" gif (which means that this entry was never fetched)
		if item.child(0).data(0, QtCore.Qt.UserRole).toString() == 'special:loading':
			if isinstance(obj, utils.cls.MetadataArtist):
				self.spawn_thread('release').search(obj, item)
			elif isinstance(obj, utils.cls.MetadataRelease):
				self.spawn_thread('recording').search(obj, item)

	def slot_clicked(self, item, i):
		val = unicode(item.data(0, QtCore.Qt.UserRole).toString())
		if val.startswith('track:'):
			val = val.split('track:', 1)[1]
			self.output = val
			self.close()
		
	def slot_close(self):
		self.close()
		
	def slot_apply(self, s):
		if not self.treeWidget.selectedItems():
			QtGui.QMessageBox.critical(self, tr("Error"), tr("Please choose a song."), QtGui.QMessageBox.Ok)
		item = self.treeWidget.selectedItems()[0]
		
		val = unicode(item.data(0, QtCore.Qt.UserRole).toString())
		if val.startswith('track:'):
			val = val.split('track:', 1)[1]
			self.output = val
			self.close()

	def addArtist(self, parent, title, data):
		item = QtGui.QTreeWidgetItem(parent, [title])
		item.setIcon(0, QtGui.QIcon(r'pics\personal.png'))
		item.setData(0, QtCore.Qt.UserRole, data)
		self.addLoadingGif(item)
		return item
		
	def addAlbum(self, parent, title, data):
		item = QtGui.QTreeWidgetItem(parent, [title])
		item.setIcon(0, QtGui.QIcon(r'pics\folder.png'))
		item.setData(0, QtCore.Qt.UserRole, data)
		self.addLoadingGif(item)
		return item

	def addTrack(self, parent, title, data):
		item = QtGui.QTreeWidgetItem(parent, [title])
		item.setIcon(0, QtGui.QIcon(r'pics\play.png'))
		item.setData(0, QtCore.Qt.UserRole, data)
		return item
		
	def addLoadingGif(self, parent):
		loadingItem = QtGui.QTreeWidgetItem(parent, [tr('      Loading...')])
		loadingItem.setData(0, QtCore.Qt.UserRole, 'special:loading')
		loadingItem.setFlags(QtCore.Qt.NoItemFlags)
		
		loading_gif = QtGui.QLabel()
		if QtGui.QApplication.layoutDirection() == QtCore.Qt.RightToLeft:
			'''
			Fix for bug http://bpaste.net/show/s5h3Gs7IjIL8U6cTWqHi/
			gif won't start if layoutDirection is RightToLeft
			'''
			loading_gif.setLayoutDirection(QtCore.Qt.LeftToRight)
			loading_gif.setAlignment(QtCore.Qt.AlignRight)
		alignment = QtCore.Qt.AlignCenter
		movie = QtGui.QMovie(r"pics\loading.gif")
		movie.setScaledSize(QtCore.QSize(16, 16))
		loading_gif.setMovie(movie)
		movie.start()
		
		self.treeWidget.setItemWidget(loadingItem, 0, loading_gif)