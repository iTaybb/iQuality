# Copyright (C) 2012-2014 Itay Brandes 

''' Updater Window '''

import os
import subprocess
import time
import zipfile
import esky

from PyQt4 import QtCore
from PyQt4 import QtGui
from pySmartDL import SmartDL

import Config; config = Config.config
from logger import log
import Main
import utils
tr = utils.qt.tr

class MainWin(QtGui.QDialog):
	def __init__(self, mode, components, newest_version=None, parent=None):
		super(MainWin, self).__init__(parent)
		self.setWindowTitle(tr("Components Updater"))
		self.resize(400, 125)
		self.setWindowIcon(QtGui.QIcon(os.path.join('pics', 'updater.png')))
		self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowMinMaxButtonsHint)
		
		if isinstance(components, esky.Esky):
			self.eskyObj = components
		else:
			self.components = components
		self.newest_version = newest_version
		self.retries = 3
		self.init_widgets()
		
		if mode == 'update_app':
			QtCore.QTimer.singleShot(200, self.start_app_update)
		elif mode == 'update_component':
			QtCore.QTimer.singleShot(200, self.start_component_update)
		elif mode == 'install_package':
			QtCore.QTimer.singleShot(200, self.start_package_install)
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		pixmap = QtGui.QPixmap(os.path.join('pics', 'updater.png')).scaled(100, 100, transformMode=QtCore.Qt.SmoothTransformation)
		self.pix = QtGui.QLabel()
		self.pix.setPixmap(pixmap)
		self.prg_bar = QtGui.QProgressBar()
		self.label1 = QtGui.QLabel(tr("Connecting to update servers..."))
		self.label2 = QtGui.QLabel("")
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.pix, 0, 0, 3, 1)
		mainLayout.addWidget(self.label1, 0, 1, alignment=QtCore.Qt.AlignBottom)
		mainLayout.addWidget(self.prg_bar, 1, 1, alignment=QtCore.Qt.AlignTop)
		mainLayout.addWidget(self.label2, 2, 1, alignment=QtCore.Qt.AlignTop)
		self.setLayout(mainLayout)
		
	def start_app_update(self):
		fn = self.eskyObj.version_finder.version_graph.get_best_path(self.eskyObj.version, self.newest_version)[0]
			
		log.debug("Updating to v%s..." % self.newest_version)
		self.label1.setText(tr("Updating to v%s...") % self.newest_version)
		self.label2.setText(tr("File: <i>%s</i>") % fn)
		
		try:
			printed_size = 0
			for d in self.eskyObj.fetch_version_iter(self.newest_version):
				QtGui.QApplication.processEvents()
				if d['status'] == 'downloading':
					if printed_size != d['size']:
						self.label1.setText(tr("Updating to v%s (%.2f MB)...") % (self.newest_version, d['size']/1024.0**2))
						printed_size = d['size']
					self.prg_bar.setValue(100.0*d['received']/d['size'])
			self.prg_bar.setValue(100)
			
			self.eskyObj.install_version(self.newest_version)
			self.eskyObj.cleanup()
			
			Main.WebParser.WebServices.inform_esky_update(fn, self.newest_version)
			
			win = SetAutoUpdate(self.newest_version)
			win.exec_()
			
			config.saveToIni()
			utils.restart_app()
		except esky.EskyVersionError:
			QtGui.QMessageBox.critical(self, tr("Error"), tr("The update task failed. Please go to <a href=\"%s\">our website</a> and download the update manually.") % config.website, QtGui.QMessageBox.Ok)
			
		self.close()
		
	def start_package_install(self):
		d = Main.WebParser.WebServices.get_packages_data()
		
		for i, component in enumerate(self.components):
			urls, file_hash, install_param = d[component]
			fn = urls[0].split('/')[-1]
			
			log.debug("Downloading Component %s [%d/%d]..." % (component, i+1, len(self.components)))
			self.label1.setText(tr("Downloading %s...") % component)
			self.label2.setText(tr("File: <i>%s</i> [%d/%d]") % (fn, i+1, len(self.components)))
			
			for j in range(self.retries):
				obj = SmartDL(urls, logger=log)
				obj.start(blocking=False)
				
				b = True
				while not obj.isFinished():
					if b:
						self.label1.setText(tr("Downloading %s (%.2f MB)...") % (component, obj.filesize/1024.0**2))
						b = False
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
				return
				
			path = obj.get_dest()
			install_params = [path] + install_param
				
			self.label1.setText(tr("Installing %s...") % component)
			subprocess.call(install_params, shell=True)
			QtGui.QApplication.processEvents()
		
		self.close()
		
	def start_component_update(self):
		if not os.path.exists(config.ext_bin_path):
			os.makedirs(config.ext_bin_path)

		d = Main.WebParser.WebServices.get_components_data()

		for i, component in enumerate(self.components):
			urls, archive_hash, file_to_extract, file_hash = d[component]
			fn = urls[0].split('/')[-1]
			
			log.debug("Downloading Component %s [%d/%d]..." % (component, i+1, len(self.components)))
			self.label1.setText(tr("Downloading %s...") % component)
			self.label2.setText(tr("File: <i>%s</i> [%d/%d]") % (fn, i+1, len(self.components)))
			
			obj = SmartDL(urls, logger=log)
			obj.add_hash_verification('sha256', archive_hash)
			obj.start(blocking=False)
			
			b = True
			while not obj.isFinished():
				if b:
					self.label1.setText(tr("Downloading %s (%.2f MB)...") % (component, obj.filesize/1024.0**2))
					b = False
				QtGui.QApplication.processEvents()
				self.prg_bar.setValue(int(obj.get_progress()*100))
				time.sleep(0.1)
			if obj._failed:
				QtGui.QMessageBox.critical(self, tr("Error"), tr("The download has failed. It may be a network connection problem. Please try to rerun this application and try again."), QtGui.QMessageBox.Ok)
				self.close()
			self.prg_bar.setValue(100)
				
			self.label1.setText(tr("Unpacking %s...") % component)
					
			ext = os.path.splitext(obj.get_dest())[1].lower()
			if ext == '.zip':
				zipObj = zipfile.ZipFile(obj.get_dest())
				zipObj.extract(file_to_extract, config.ext_bin_path)
			elif ext == '.7z':
				cmd = r'"%s\7za.exe" e "%s" -ir!%s -y -o"%s"' % (config.ext_bin_path, obj.get_dest(), file_to_extract, config.ext_bin_path)
				subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			else:
				log.error('could not extract %s archive.' % ext)
				
		self.close()
		
class SetAutoUpdate(QtGui.QDialog):
	def __init__(self, version, parent=None):
		super(SetAutoUpdate, self).__init__(parent)
		self.setWindowTitle(tr("Information"))
		# self.resize(400, 125)
		self.setWindowIcon(QtGui.QIcon(r'pics\updater.png'))
		self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowMinMaxButtonsHint)
		
		self.version = version
		
		self.init_widgets()
		
	def init_widgets(self):
		# Layouts
		mainLayout = QtGui.QGridLayout()
		
		self.label = QtGui.QLabel(tr("iQuality v%s was installed successfully. You now have the latest update.\n") % self.version)
		self.checkbox = QtGui.QCheckBox(tr("Auto-update the software next time"))
		self.checkbox.setCheckState(config.auto_update)
		self.checkbox.setTristate(False)
		self.checkbox.stateChanged.connect(self.slot_changed_checkbox)
		self.close_button = QtGui.QPushButton(tr("Ok"))
		self.close_button.clicked.connect(self.close)
		
		# QGridLayout.addWidget (self, QWidget, int row, int column, int rowSpan, int columnSpan, Qt.Alignment alignment = 0)
		mainLayout.addWidget(self.label, 0, 1, alignment=QtCore.Qt.AlignBottom)
		mainLayout.addWidget(self.checkbox, 1, 1, alignment=QtCore.Qt.AlignTop)
		mainLayout.addWidget(self.close_button, 2, 1, alignment=QtCore.Qt.AlignTop)
		
		self.setLayout(mainLayout)
		
	def slot_changed_checkbox(self, state):
		config.auto_update = bool(state)