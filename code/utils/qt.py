# Copyright (C) 2012-2015 Itay Brandes

'''
Module for custom-made Qt objects.
'''

import sys
import math

from PyQt4 import QtCore
from PyQt4 import QtGui

def selectedRowsIndexes(selectedIndexes):
	'''
	Gets a selectedIndexes list. returns the selectedRowsIndexes
	'''
	selectedRows = []
	selectedRowsObjs = []
	for index in selectedIndexes:
		if not index.row() in selectedRows:
			selectedRowsObjs.append(index)
			selectedRows.append(index.row())
			
	return selectedRowsObjs

class MovieSplashScreen(QtGui.QSplashScreen):
	'''
	An extended QSplashScreen module that allows QMovies.
	
	Use it like this:
	>>> splash_movie = QtGui.QMovie('loading.gif')
	>>> self.splash = MovieSplashScreen(splash_movie, QtCore.Qt.WindowStaysOnTopHint)
	
	Then run the show() and hide() methods.
	>>> self.splash.show()
	>>> self.splash.hide()
	'''
	def __init__(self, movie, flags=0, parent = None):
		movie.jumpToFrame(0)
		pixmap = QtGui.QPixmap(movie.frameRect().size())
		
		QtGui.QSplashScreen.__init__(self, parent, pixmap)
		self.movie = movie
		self.movie.frameChanged.connect(self.repaint)

	def showEvent(self, event):
		self.movie.start()

	def hideEvent(self, event):
		self.movie.stop()

	def paintEvent(self, event):
		painter = QtGui.QPainter(self)
		pixmap = self.movie.currentPixmap()
		self.setMask(pixmap.mask())
		painter.drawPixmap(0, 0, pixmap)

	def sizeHint(self):
		return self.movie.scaledSize()

class WidgetOverlay(QtGui.QWidget):
	'''
	An overlay thay will show a "loading" animation as an overlay ON a widget.
	
	Use it like this:
	>>> self.overlay = WidgetOverlay(self.widget_we_want_to_apply_overlay)
	
	The window that shows the widget inform the class on resizeEvent:
	>>> class MainWindow(QtGui.QMainWindow):
	...     def __init__(self, parent = None):
	...         pass
	...
	...     def resizeEvent(self, event):
    ...         self.overlay.resize(event.size())
    ...         event.accept()
	
	Then run the show() and hide() methods.
	>>> self.overlay.hide()
	>>> self.overlay.show()
	'''
	
	def __init__(self, parent = None):
		QtGui.QWidget.__init__(self, parent)
		palette = QtGui.QPalette(self.palette())
		palette.setColor(palette.Background, QtCore.Qt.transparent)
		self.setPalette(palette)

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255, 127)))
		painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
		
		for i in range(6):
			if (self.counter / 5) % 6 == i:
				painter.setBrush(QtGui.QBrush(QtGui.QColor(127 + (self.counter % 5)*32, 127, 127)))
			else:
				painter.setBrush(QtGui.QBrush(QtGui.QColor(127, 127, 127)))
			painter.drawEllipse(
				self.width()/2 + 30 * math.cos(2 * math.pi * i / 6.0) - 10,
				self.height()/2 + 30 * math.sin(2 * math.pi * i / 6.0) - 10,
				20, 20)
		
		painter.end()

	def showEvent(self, event):
		# print self.palette()
		self.timer = self.startTimer(50)
		self.counter = 0

	def timerEvent(self, event):
		self.counter += 1
		self.update()
		if self.counter == 60000:
			self.killTimer(self.timer)
			self.hide()

class DoublePixmap(QtGui.QPixmap):

	'''
	Use like:
	double_pixmap = DoublePixmap(200,100)

	double_pixmap.setLeftPixmap(IMAGE1)
	double_pixmap.setRightPixmap(IMAGE2)

	label = QtGui.QLabel()
	label.setPixmap(double_pixmap)
	'''
	_left_pm = None
	_right_pm = None

	@property
	def left_pixmap(self):
		if self._left_pm is None:
			self._left_pm = QtGui.QPixmap()
		return self._left_pm
		
	@property
	def right_pixmap(self):
		if self._right_pm is None:
			self._right_pm = QtGui.QPixmap()
		return self._right_pm

	def setLeftPixmap(self, pm):
		self._left_pm = QtGui.QPixmap(pm)
		self.adjust_sizes()

	def setRightPixmap(self, pm):
		self._right_pm = QtGui.QPixmap(pm)
		self.adjust_sizes()

	def adjust_sizes(self):
		width = self.width()
		height = self.height()
		
		left_rectF = QtCore.QRectF(0, 0, width/2, height)      #the left half
		right_rectF = QtCore.QRectF(width/2, 0, width, height) #the right half

		self.fill(QtCore.Qt.transparent)
		painter = QtGui.QPainter(self)
		painter.setBackgroundMode(QtCore.Qt.TransparentMode) 
		painter.drawPixmap(
			left_rectF, 
			self.left_pixmap, 
			QtCore.QRectF(self.left_pixmap.rect())
			)
		painter.drawPixmap(
			right_rectF, 
			self.right_pixmap, 
			QtCore.QRectF(self.right_pixmap.rect())
			)
			
class BlankItemDelegate(QtGui.QStyledItemDelegate):
	def __init__(self, parent):
		super(BlankItemDelegate, self).__init__(parent)
			
def tr(sourceText, disambiguation=None, inspectContext=False, split_tr=False):
	'''
	Wrapper for QCoreApplication.translate that acts like the QObject.tr() function.
	returns python's unicode type instead of QString.
	Used for enhanced readability { unicode(self.tr('s')) --> tr('s') }
	
	split_tr is to attempt translating any word seperately.
	
	Useful in Python 2.x only.
	'''
	if inspectContext:
		callingframe = sys._getframe(1)
		context = callingframe.f_locals['self'].__class__.__name__
	else:
		context = "@default"
	if split_tr:
		return " ".join([unicode(QtCore.QCoreApplication.translate(context, part, disambiguation)) for part in sourceText.split(' ')])
	return unicode(QtCore.QCoreApplication.translate(context, sourceText, disambiguation))

def combine_pixmaps(pix_list):
	"combines pixmaps"
	# QRect(aleft, atop, awidth, aheight)

	new_pix = QtGui.QPixmap(sum([x.width() for x in pix_list]), max([x.height() for x in pix_list]))
	new_pix.fill(QtCore.Qt.transparent)
	
	painter = QtGui.QPainter(new_pix)
	painter.setRenderHint(QtGui.QPainter.Antialiasing)
	
	currect_x_value = 0
	for pix in pix_list:
		rect = QtCore.QRectF(currect_x_value, 0, pix.width(), pix.height())
		painter.drawPixmap(rect, pix, QtCore.QRectF(pix.rect()))
		
		currect_x_value += pix.width()

	return new_pix