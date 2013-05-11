# Copyright (C) 2012-2013 Itay Brandes 

''' Component Fetcher Window '''

import os
import subprocess
import time
import zipfile
import subprocess

from PyQt4 import QtCore
from PyQt4 import QtGui

import Config; config = Config.config
from logger import log
import Main
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, mode, components, parent=None):
		super(MainWin, self).__init__(parent)
		self.setWindowTitle(tr("Components Updater"))
		self.resize(400, 125)
		self.setWindowIcon(QtGui.QIcon(r'pics\updater.png'))
		# self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowMinMaxButtonsHint)
		
		self.components = components
		self.retries = 3
		self.init_widgets()
		
		if mode == 'update':
			QtCore.QTimer.singleShot(200, self.start_update)
		elif mode == 'install':
			QtCore.QTimer.singleShot(200, self.start_install)
		
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
		
	def start_install(self):
		d = Main.WebParser.WebServices.get_packages_data()
		
		for i, component in enumerate(self.components):
			urls, file_hash, install_param = d[component]
			
			log.debug("Downloading Component %s [%d/%d]..." % (component, i+1, len(self.components)))
			self.label1.setText(tr("Downloading %s [%d/%d]...") % (component, i+1, len(self.components)))
			
			for j in range(self.retries):
				obj = Main.SmartDL(urls, logger=log)
				obj.start()
				
				while not obj.isFinished():
					QtGui.QApplication.processEvents()
					self.prg_bar.setValue(int(obj.get_progress()*100))
					time.sleep(0.1)
				if obj._failed:
					QtGui.QMessageBox.critical(self, tr("Error"), tr("The download has failed. It may be a network connection problem. Please try to rerun this application and try again."), QtGui.QMessageBox.Ok)
					self.close()
				self.prg_bar.setValue(100)
					
				computed_hash = utils.calc_sha256(obj.get_dest())
				if file_hash == computed_hash:
					log.debug('Hash for %s is valid.' % component)
					break
				else:
					log.warning('Hash for %s is NOT valid (%s != %s). Retrying (%d/%d)...' % (component, file_hash, computed_hash, j+1, self.retries))	
				
			if file_hash != computed_hash:
				log.error('Hash for %s is NOT valid (%s != %s).' % (component, file_hash, computed_hash))
				QtGui.QMessageBox.warning(self, tr("Warning"), tr("Hash check failed for %s. Please contact with the program's developer.") % component, QtGui.QMessageBox.Ok)
				self.close()
				
			path = obj.get_dest()
			install_params = [path] + install_param
				
			self.label1.setText(tr("Installing %s...") % component)
			subprocess.call(install_params, shell=True)
			QtGui.QApplication.processEvents()
		
		self.close()
		
	def start_update(self):
		bin_path = 'bin'
		
		if not os.path.exists(bin_path):
			os.makedirs(bin_path)

		d = Main.WebParser.WebServices.get_components_data()

		for i, component in enumerate(self.components):
			urls, archive_hash, file_to_extract, file_hash = d[component]
			
			log.debug("Downloading Component %s [%d/%d]..." % (component, i+1, len(self.components)))
			self.label1.setText(tr("Downloading %s [%d/%d]...") % (component, i+1, len(self.components)))
			for j in range(self.retries):
				obj = Main.SmartDL(urls, logger=log)
				obj.start()
				
				while not obj.isFinished():
					QtGui.QApplication.processEvents()
					self.prg_bar.setValue(int(obj.get_progress()*100))
					time.sleep(0.1)
				if obj._failed:
					QtGui.QMessageBox.critical(self, tr("Error"), tr("The download has failed. It may be a network connection problem. Please try to rerun this application and try again."), QtGui.QMessageBox.Ok)
					self.close()
				self.prg_bar.setValue(100)
					
				self.label1.setText(tr("Unpacking %s...") % component)
				
				computed_hash = utils.calc_sha256(obj.get_dest())
				if archive_hash == computed_hash:
					log.debug('Hash for %s is valid.' % component)
					break
				else:
					log.warning('Hash for %s is NOT valid (%s != %s). Retrying (%d/%d)...' % (component, archive_hash, computed_hash, j+1, self.retries))	
				
			if archive_hash != computed_hash:
				log.error('Hash for %s is NOT valid (%s != %s).' % (component, archive_hash, computed_hash))
				QtGui.QMessageBox.warning(self, tr("Warning"), tr("Hash check failed for %s. Please contact with the program's developer.") % component, QtGui.QMessageBox.Ok)
				self.close()
					
			ext = os.path.splitext(obj.get_dest())[1].lower()
			if ext == '.zip':
				zipObj = zipfile.ZipFile(obj.get_dest())
				zipObj.extract(file_to_extract, bin_path)
			elif ext == '.7z':
				cmd = r'"%s\7za.exe" e "%s" -ir!%s -y -o"%s"' % (bin_path, obj.get_dest(), file_to_extract, bin_path)
				subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			else:
				log.error('could not extract %s archive.' % ext)
				
		self.close()