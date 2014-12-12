# Copyright (C) 2012-2015 Itay Brandes

'''Main Script Module'''

import os
import sys
import traceback
import time
import urllib2
import math

import esky
from PyQt4 import QtCore

import HTTPQuery
import WebParser
import Config; config = Config.config
from logger import log
from CustomExceptions import NoSpaceWarning, NewerVersionWarning, NoInternetConnectionException, NoDnsServerException, ComponentsFaultyWarning
import utils

__version__ = Config.__version__
__rev__ = Config.__rev__
__date__ = Config.__date__
__author__ = 'Itay Brandes (Brandes.Itay@gmail.com)'
		
### FUNCTIONS ###
def my_excepthook(_type, value, tback):
	'''
	Can be used as an override to the default excepthook by running
	"sys.excepthook = my_excepthook"
	
	Will log exceptions and then call the default excepthook.
	'''
	log.exception("".join(traceback.format_exception(_type, value, tback)))
	# sys.__excepthook__(_type, value, tback)
	
def init():
	"Initizing the environment"
	# Making sure temp folder is accessable.
	if not os.path.exists(config.temp_dir):
		try:
			os.makedirs(config.temp_dir)
		except (IOError, WindowsError):
			config.temp_dir = os.path.join(os.environ["Temp"], "iQuality") # if temp folder cannot be created, we should set it to default.
			
	# setting ext_bin directory
	if hasattr(sys, "frozen"):
		# the ext_bin folder will be one level upper
		splitted_dirs = config.ext_bin_path.split('\\')
		config.ext_bin_path = "\\".join(splitted_dirs[:-2]+[splitted_dirs[-1]])
		
	log.debug("ext_bin_path: %s" % config.ext_bin_path)
		
	if not os.path.exists(config.ext_bin_path):
		os.makedirs(config.ext_bin_path)
	
	# Checking internet connection
	returncode = utils.launch_without_console('ping 8.8.8.8 -n 1').wait()
	if returncode > 0:
		log.error("Got NoInternetConnectionException()")
		raise NoInternetConnectionException()
		
	returncode = utils.launch_without_console('ping www.google.com -n 1').wait()
	if returncode > 0:
		log.error("Got NoDnsServerException()")
		raise NoDnsServerException()

def sanity_check():
	"Sanity Check for script."
	config.count_application_runs += 1
	_warnings = []
	
	### LOCAL CHECKS ###
	
	# Windows version check
	winver = sys.getwindowsversion()
	log.debug('Running iQuality v%s (r%d) on Windows %d.%d.%d %s' % (__version__, __rev__, winver.major, winver.minor, winver.build, winver.service_pack))
	
	# Python version check
	if sys.version_info < (2, 6) or sys.version_info >= (3, 0):
		msg = "must use python 2.7"
		log.critical(msg)
		raise Exception(msg)
	log.debug('CPython version is %d.%d.%d' % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro))
	log.debug('PyQt version is %s, Qt version is %s' % (QtCore.PYQT_VERSION_STR, QtCore.QT_VERSION_STR))
		
	# youtube-dl check
	try:
		import youtube_dl
		log.debug("youtube-dl version is %s" % youtube_dl.version.__version__)
	except ImportError:
		log.warning("Could not load the youtube-dl module")
		
	# Phonon version check
	try:
		from PyQt4.phonon import Phonon
		if Phonon.BackendCapabilities.isMimeTypeAvailable('video/x-flv'):
			log.debug('Phonon version is %s. video/x-flv is supported.' % Phonon.phononVersion())
		else:
			log.warning('Phonon version is %s. video/x-flv is not supported.' % Phonon.phononVersion())
	except ImportError:
		log.warning("Could not load the phonon module")
	
	# Free space check
	freespace = utils.get_free_space(config.temp_dir)
	if freespace < 200*1024**2: # 200 MB
		drive = os.path.splitdrive(config.temp_dir)[0]
		log.warning("There are less than 200MB available in drive %s (%.2fMB left)." % (drive, freespace/1024.0**2))
		_warnings.append(NoSpaceWarning(drive, freespace))

	# iTunes' availablity check
	itunesPath = r'%s\My Documents\My Music\iTunes\iTunes Media\Automatically Add to iTunes' % utils.get_home_dir()
	if not os.path.exists(itunesPath):
		config.is_itunes_installed = False
		if config.post_download_action == 'addItunes':
			config.post_download_action = 'ask'
		log.warning("iTunes Media not found. setting is_itunes_installed to False")
		
	# Context Menu check
	try: # IMPROVE: REMOVE THE TRY-EXCEPT BLOCK
		if config.id3editor_in_context_menu and not utils.check_context_menu_status():
			log.debug("Registering Context Menu Object...")
			try:
				utils.register_with_context_menu()
			except WindowsError, e:
				if e.winerror == 5: # Access is denied
					log.debug("Access is denied. Setting id3editor_in_context_menu to False.")
					config.id3editor_in_context_menu = False
				else:
					raise
		if not config.id3editor_in_context_menu and utils.check_context_menu_status():
			log.debug("Unregistering Context Menu Object...")
			try:
				utils.unregister_with_context_menu()
			except WindowsError, e:
				if e.winerror == 5: # Access is denied
					log.debug("Access is denied. Setting id3editor_in_context_menu to True.")
					config.id3editor_in_context_menu = True
				else:
					raise
	except:
		log.error(traceback.format_exc())
		
	### ONLINE CHECKS ###
	timestamp = math.fabs(time.time() - config.last_sanity_check_timestamp)
	if timestamp > config.interval_between_network_sanity_checks:
	# if the last check was before more than interval_between_network_sanity_checks
		# Newest version check - esky
		if hasattr(sys, "frozen"):
			try:
				eskyObj = esky.Esky(sys.executable, config.esky_zipfiles_download_page)
				v = eskyObj.find_update()
				if v:
					log.warning("A new version of iQuality is available (%s, via esky)." % v)
					_warnings.append(NewerVersionWarning(v, eskyObj.version, eskyObj))
					# print "Found %s --> %s (%s)!" % (app.version, v, app.version_finder.version_graph.get_best_path(app.version,v))
			except IOError as e:
				log.error("Could not check for the newest version (%s)" % unicode(e))
		
		# External Components Check
		hash_failed = []
		not_exists = []
		
		d = WebParser.WebServices.get_components_data()
		for name, t in d.items():
			urls, archive_hash, file_to_extract, file_hash = t
			
			if not os.path.exists(os.path.join(config.ext_bin_path, file_to_extract)):
				log.warning('External component was not found: %s' % name)
				not_exists.append(name)
				continue
			
			computed_hash = utils.calc_sha256(os.path.join(config.ext_bin_path, file_to_extract))
			if file_hash != computed_hash:
				log.warning('External components hash check failed for %s' % name)
				hash_failed.append(name)
				continue
		if hash_failed or not_exists:
			_warnings.append(ComponentsFaultyWarning(hash_failed+not_exists))
		else:
			log.debug('External components hash check passed')
			
		if not _warnings:
			config.last_sanity_check_timestamp = time.time()
	else:
		log.debug('Last successful sanity check was launched %d minutes ago. Skipping...' % math.ceil(timestamp/60))
	
	return _warnings