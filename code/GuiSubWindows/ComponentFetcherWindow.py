# Copyright (C) 2012-2013 Itay Brandes 

''' Component Fetcher Window '''

import os
import subprocess
import zipfile

from PyQt4 import QtCore
from PyQt4 import QtGui

import Config; config = Config.config
from logger import log
import Main
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, components, parent=None):
		super(MainWin, self).__init__(parent)
		self.setWindowTitle(tr("Components Updater"))
		self.resize(400, 125)
		self.setWindowIcon(QtGui.QIcon(r'pics\updater.png'))
		
		self.components = components
		self.init_widgets()
		
		QtCore.QTimer.singleShot(200, self.start_update)
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		pixmap = QtGui.QPixmap(r'pics\updater.png').scaled(100, 100, transformMode=QtCore.Qt.SmoothTransformation)
		self.pix = QtGui.QLabel()
		self.pix.setPixmap(pixmap)
		self.prg_bar = QtGui.QProgressBar()
		self.label1 = QtGui.QLabel(tr("Connecting to update servers..."))
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.pix, 0, 0, 2, 1)
		mainLayout.addWidget(self.label1, 0, 1, alignment=QtCore.Qt.AlignBottom)
		mainLayout.addWidget(self.prg_bar, 1, 1, alignment=QtCore.Qt.AlignTop)
		self.setLayout(mainLayout)
		
	def start_update(self):
		bin_path = r'C:\Scripts\iQuality\code\bin'
		
		if not os.path.exists(bin_path):
			os.makedirs(bin_path)

		d = Main.WebParser.WebServices.get_components_data()

		for component in self.components:
			urls, archive_hash, file_to_extract, file_hash = d[component]
			
			log.debug("Downloading Component %s..." % component)
			self.label1.setText(tr("Downloading %s...") % component)
			obj = Main.SmartDL(urls, logger=log)
			obj.start()
			
			while not obj.isFinished():
				self.prg_bar.setValue(int(obj.get_progress()*100))
				
			self.label1.setText(tr("Unpacking %s...") % component)
			
			computed_hash = utils.calc_sha256(obj.get_dest())
			if archive_hash != computed_hash:
				log.error('Hash for %s is NOT valid (%s != %s).' % (component, archive_hash, computed_hash))
				QtGui.QMessageBox.warning(self, tr("Warning"), tr("Hash check failed for %s. Please contact with the program's developer.") % component, QtGui.QMessageBox.Ok)
					
			ext = os.path.splitext(obj.get_dest())[1].lower()
			if ext == '.zip':
				zip = zipfile.ZipFile(obj.get_dest())
				zip.extract(file_to_extract, bin_path)
			elif ext == '.7z':
				cmd = r'%s\7za.exe e %s -ir!%s -y -o"%s"' % (bin_path, obj.get_dest(), file_to_extract, bin_path)
				subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			else:
				log.error('could not extract %d archive.' % ext)
				
		self.close()