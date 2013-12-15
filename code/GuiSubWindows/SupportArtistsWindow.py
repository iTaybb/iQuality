# Copyright (C) 2012-2013 Itay Brandes 

''' Support The Artists Window '''

from PyQt4 import QtCore
from PyQt4 import QtGui

import Config; config = Config.config
from logger import log
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, songObj="", parent=None):
		super(MainWin, self).__init__(parent)
		self.resize(400, 200)
		
		self.songObj = songObj
		
		self.setWindowTitle(tr("Support the Artists"))
		self.setWindowIcon(QtGui.QIcon(r'pics\folder_heart.png'))
		
		self.init_widgets()
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		pixmap = QtGui.QPixmap(r'pics\i_buy_music.png').scaled(330, 108, transformMode=QtCore.Qt.SmoothTransformation)
		self.pix = QtGui.QLabel()
		self.pix.setPixmap(pixmap)
		
		self.label1 = QtGui.QLabel(tr('Musicians deserve to make a living from their music based on how many people own or, for lack of a better term, consume it.\nIf you like the music and can afford a few bucks to spend on it, please consider purchasing it and directly support the artists.'))
		self.label1.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Ignored)
		self.label1.setWordWrap(True)
	
		button_bandcamp_search = QtGui.QPushButton(QtGui.QIcon(r'pics\folder_heart.png'), "")
		if self.songObj:
			button_bandcamp_search.setText(tr('Buy in Bandcamp Store'))
		else:
			button_bandcamp_search.setText(tr('Open Bandcamp Store'))
		button_bandcamp_search.clicked.connect(self.slot_bandcamp_search)
		
		if self.songObj and self.songObj.source == 'bandcamp':
			button_open_webpage_url = QtGui.QPushButton(QtGui.QIcon(r'pics\folder_heart.png'), tr('Open the track\'s landing page on %s') % self.songObj.source)
			button_open_webpage_url.clicked.connect(self.slot_open_webpage_url)
			
		button_search_apple = QtGui.QPushButton(QtGui.QIcon(r'pics\folder_heart.png'), "")
		if self.songObj:
			button_search_apple.setText(tr('Buy in iTunes Store'))
		else:
			button_search_apple.setText(tr('Open iTunes Store'))
		
		button_search_apple.clicked.connect(self.slot_apple_search)
		button_amazon_search = QtGui.QPushButton(QtGui.QIcon(r'pics\folder_heart.png'), "")
		if self.songObj:
			button_amazon_search.setText(tr('Buy in Amazon Music Store'))
		else:
			button_amazon_search.setText(tr('Open Amazon Music Store'))
		button_amazon_search.clicked.connect(self.slot_amazon_search)
		button_close = QtGui.QPushButton(tr('Close'))
		button_close.clicked.connect(self.slot_close)
		
		self.saveSelection_CheckBox = QtGui.QCheckBox(tr("Do not show this message again"))
		self.saveSelection_CheckBox.setCheckState(not config.show_supportArtists_notice)
		self.saveSelection_CheckBox.setTristate(False)
		
		# Decide which buttons we can show on the screen
		buttons = []
		if self.songObj and self.songObj.source == 'bandcamp':
			buttons.append(button_open_webpage_url)
		else:
			buttons.append(button_bandcamp_search)
		buttons.append(button_amazon_search)
		buttons.append(button_search_apple)
		buttons.append(button_close)
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.pix, 0, 0, 2, 1, alignment = QtCore.Qt.AlignCenter)
		mainLayout.addWidget(self.label1, 0, 1, 1, 3)
		for i, button in enumerate(buttons):
			j = 0 # how much we need to extend the button
			if i == len(buttons)-1: # if last button
				j = 2-i%3 # extend by the remaining space
			mainLayout.addWidget(button, i/3+1, i%3+1, 1, 1+j)
		mainLayout.addWidget(self.saveSelection_CheckBox, 10, 0, 1, 4)

		self.setLayout(mainLayout)

	def slot_open_webpage_url(self):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.songObj.webpage_url))
		
	def slot_apple_search(self):
		if not self.songObj:
			QtGui.QDesktopServices.openUrl(QtCore.QUrl(r"http://www.apple.com/itunes/charts/songs/"))
			return
			
		title = self.songObj.title
		if self.songObj.artist:
			title += " - %s" % self.songObj.artist
		title = title.encode("utf8")
		url = "http://www.apple.com/search/?q=%s" % title
		
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
		
	def slot_amazon_search(self):
		if not self.songObj:
			QtGui.QDesktopServices.openUrl(QtCore.QUrl(r"http://www.amazon.com/MP3-Music-Download/b?ie=UTF8&node=163856011"))
			return
			
		title = self.songObj.title
		if self.songObj.artist:
			title += " - %s" % self.songObj.artist
		title = title.encode("utf8").replace(' ', '+')
		url = r"http://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%%3Dpopular&field-keywords=%s" % title
		
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
		
	def slot_bandcamp_search(self):
		if not self.songObj:
			QtGui.QDesktopServices.openUrl(QtCore.QUrl(r"http://www.bandcamp.com/"))
			return
			
		title = self.songObj.title
		if self.songObj.artist:
			title += " - %s" % self.songObj.artist
		title = title.encode("utf8").replace(' ', '+')
		url = r"http://www.bandcamp.com/search?q=%s" % title
		
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
		
	def slot_close(self):
		config.show_supportArtists_notice = not self.saveSelection_CheckBox.isChecked()
		self.close()
