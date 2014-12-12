# Copyright (C) 2012-2015 Itay Brandes 

''' Charts Explorer Window '''

import os.path
from collections import OrderedDict

from PyQt4 import QtCore
from PyQt4 import QtGui

import Config; config = Config.config
from logger import log
from GuiThreads import ChartsLookupThread
import WebParser.WebServices
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, parent=None):
		super(MainWin, self).__init__(parent)

		self.setWindowTitle(tr("Charts Explorer"))
		self.resize(525, 350)
		self.setWindowIcon(QtGui.QIcon(os.path.join('pics', 'charts.png')))
		
		self.charts = {
						'English': OrderedDict({
												tr('Billboard Top 100 (English)'): WebParser.WebServices.parse_billboard,
												tr('UK Top 40 (English)'): WebParser.WebServices.parse_uktop40
												}),
						'Hebrew': OrderedDict({
												tr('Galgalatz Top 20 (Hebrew)'): WebParser.WebServices.parse_glgltz,
												tr('Charts.co.il Top 20 (Hebrew)'): WebParser.WebServices.parse_chartscoil
												})
						}
		
		self.init_widgets()
		
		tr('All Languages') # here for translator to catch the phrase
		
	def spawn_thread(self):
		thread = ChartsLookupThread()
		thread.output.connect(self.slot_results)
		thread.error.connect(self.slot_error)
		
		# the thread object needs to be binded to the window object, else it'll terminate when this function ends
		self.thread = thread
		
		return thread
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		pixmap = QtGui.QPixmap(r'pics\charts.png').scaled(100, 100, transformMode=QtCore.Qt.SmoothTransformation)
		self.pix = QtGui.QLabel()
		self.pix.setPixmap(pixmap)
		
		self.label1 = QtGui.QLabel(tr("Here you can find track lists from well-known universal charts.\n\nYou may choose a track from the list below, and iQuality will download it for you."))
		self.label1.setWordWrap(True)
		
		self.label2 = QtGui.QLabel(tr("Language:"))
		
		self.lang_combo = QtGui.QComboBox()
		self.lang_combo_options = self.charts.keys() + ['All Languages']
		self.lang_combo.addItems(map(tr, self.lang_combo_options))
		self.lang_combo.setCurrentIndex(self.charts.keys().index(config.lang_names[config.lang]))
		self.lang_combo.currentIndexChanged.connect(self.slot_lang_combo_changed)
		
		self.treeWidget = QtGui.QTreeWidget()
		self.treeWidget.setHeaderHidden(True)
		self.treeWidget.itemExpanded.connect(self.slot_expended)
		self.treeWidget.itemDoubleClicked.connect(self.slot_clicked)
		
		for k, v in self.charts[config.lang_names[config.lang]].items():
			item = self.addArtist(self.treeWidget.invisibleRootItem(), k, v)

		buttonLayout = QtGui.QHBoxLayout()
		applyButton = QtGui.QPushButton(tr("Choose"))
		applyButton.clicked.connect(self.slot_apply)
		closeButton = QtGui.QPushButton(tr('Dismiss'))
		closeButton.clicked.connect(self.slot_close)
		buttonLayout.addWidget(applyButton)
		buttonLayout.addWidget(closeButton)
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.label1, 0, 0, 1, 2)
		mainLayout.addWidget(self.label2, 1, 0, alignment = QtCore.Qt.AlignRight)
		mainLayout.addWidget(self.lang_combo, 1, 1, alignment = QtCore.Qt.AlignLeft)
		mainLayout.addWidget(self.pix, 0, 2, 2, 1, alignment = QtCore.Qt.AlignCenter)
		mainLayout.addWidget(self.treeWidget, 2, 0, 1, 3)
		mainLayout.addLayout(buttonLayout, 3, 0)
		self.setLayout(mainLayout)
		
	def slot_lang_combo_changed(self, i):
		val = self.lang_combo_options[i]
		
		self.treeWidget.clear()
		
		if val == 'All Languages':
			items = []
			for chart in self.charts:
				items.extend(self.charts[chart].items())
		else:
			items = self.charts[val].items()
		
		for k, v in items:
			item = self.addArtist(self.treeWidget.invisibleRootItem(), k, v)
			
	def slot_results(self, tracks, item):
		item.takeChildren()
		
		for i, track in enumerate(tracks):
			self.addTrack(item, "%d. %s" % (i+1, track), 'track:%s' % track)
			
	def slot_error(self, reason, item):
		QtGui.QMessageBox.warning(self, tr("Error"), "<h2>%s</h2>" % reason, QtGui.QMessageBox.Ok)
		
		item.takeChildren()
		blankItem = QtGui.QTreeWidgetItem(item, [tr('No tracks available.')])
		blankItem.setFlags(QtCore.Qt.NoItemFlags)
		
	def slot_expended(self, item):
		obj = item.data(0, QtCore.Qt.UserRole).toPyObject()
		
		# if there's a "loading" gif (which means that this entry was never fetched)
		if item.child(0).data(0, QtCore.Qt.UserRole).toString() == 'special:loading':
			self.spawn_thread().lookup(obj, item)

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