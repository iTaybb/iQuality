# Copyright (C) 2012-2015 Itay Brandes 

''' Tracks Explorer Window '''

from PyQt4 import QtCore
from PyQt4 import QtGui

import Config; config = Config.config
from logger import log
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, parent=None):
		super(MainWin, self).__init__(parent)
		self.setWindowTitle(tr("Search Help Window"))
		self.resize(500, 350)
		self.setWindowIcon(QtGui.QIcon(r'pics\support.png'))
		
		self.init_widgets()
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		pixmap = QtGui.QPixmap(r'pics\support.png').scaled(90, 90, transformMode=QtCore.Qt.SmoothTransformation)
		self.pix = QtGui.QLabel()
		self.pix.setPixmap(pixmap)
		
		s = tr('''
		Using the search field, one can search a song, whole albums, discography, tracks from worldwide top 100 charts and more. The following options are available:

		1. <b>Regular search</b>:
		Type the song name and press "Search".
		
		For example, <i><font color="brown">Swedish House Mafia - Don't You Worry Child</font></i>.
		
		2. <b>Download a video/audio from Youtube</b>:
		Type the Youtube link and press "Search".
		Youtube playlists are also supported.
		
		For example, <i><font color="brown">http://www.youtube.com/watch?v=zMMKhLC2ATw</font></i>

		3. <b>Search in discography</b>:
		Type the exact artist name and press "Search". If an artist will be found, a window will pop up with the artist's discography.
		
		For example, <i><font color="brown">Adele</font></i>.

		4. <b>Search song by its lyrics</b>:
		Type the lyrics sentence and press "Search". If a song will be found, iQuality will ask you if it's the song you searched for.
		
		For example, <i><font color="brown">let the skyfall when it crumbles</font></i>.

		5. <b>Get a random song from the top 100 charts</b>:
		Make sure the search field is empty and press "Search".
		''')
		s = s.replace('\n', r'<br \>').strip(r'<br \>')
		
		self.label1 = QtGui.QLabel(s)
		self.label1.setWordWrap(True)

		buttonLayout = QtGui.QHBoxLayout()
		closeButton = QtGui.QPushButton(tr("Close Window"))
		closeButton.clicked.connect(self.slot_close)
		buttonLayout.addWidget(closeButton)
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.label1, 0, 0)
		# mainLayout.addWidget(self.pix, 0, 1)
		mainLayout.addLayout(buttonLayout, 2, 0, 1, 2)
		self.setLayout(mainLayout)
		
	def slot_close(self):
		self.close()