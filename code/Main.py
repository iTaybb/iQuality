# Copyright (C) 2012-2013 Itay Brandes

'''Main Script Module'''

import os
import sys
import traceback
import time
import math

import regobj

import HTTPQuery
from SmartDL import SmartDL
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
			config.temp_dir = r"%s\iQuality" % os.environ["Temp"] # if temp folder cannot be created, we should set it to default.
			
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
		
	# Free space check
	freespace = utils.get_free_space(config.temp_dir)
	if freespace < 200*1024**2: # 200 MB
		drive = os.path.splitdrive(config.temp_dir)[0]
		log.warning("There are less than 200MB available in drive %s (%.2fMB left)." % (drive, freespace/1024.0**2))
		_warnings.append(NoSpaceWarning(drive, freespace))
	
	# Phonon version check
	try:
		from PyQt4.phonon import Phonon
		log.debug("Phonon version is %s" % Phonon.phononVersion())
		# mimeTypes = [str(name) for name in Phonon.BackendCapabilities.availableMimeTypes()]
		# log.debug("Available Mime Types are %s" % str(mimeTypes))
	except ImportError:
		log.warning("Could not load the phonon module")

	# iTunes' availablity check
	itunesPath = r'%s\My Documents\My Music\iTunes\iTunes Media\Automatically Add to iTunes' % utils.get_home_dir()
	if not os.path.exists(itunesPath):
		config.is_itunes_installed = False
		if config.post_download_action == 'addItunes':
			config.post_download_action = 'ask'
		log.warning("iTunes Media not found. setting is_itunes_installed to False")
		
	# Context Menu check
	try:
		if config.id3editor_in_context_menu and not 'iQuality' in regobj.HKCR.mp3file.shell:
			log.debug("Registering Context Menu Object...")
			utils.register_with_context_menu()
		if not config.id3editor_in_context_menu and 'iQuality' in regobj.HKCR.mp3file.shell:
			log.debug("Unregistering Context Menu Object...")
			utils.unregister_with_context_menu()
	except:
		log.error(traceback.format_exc())
			
	# Configuration sanity checks
	if config.post_download_action == 'customLaunch':
		cmd = config.post_download_custom_cmd
		if not cmd or cmd.count('"')%2 != 0:
			log.warning("config.post_download_custom_cmd is empty, malformed. changing to config.post_download_action to 'ask'.")
			config.post_download_action = 'ask'
			
		exe_path = cmd.split('"')[1] if cmd[0] == '"' else cmd.split()[0]
		if not os.path.exists(exe_path):
			log.warning("config.post_download_custom_cmd's \"%s\" does not exist. changing to config.post_download_action to 'ask'." % exe_path)
			config.post_download_action = 'ask'
			
	if config.post_download_action == 'addPlaylist':
		pl_path = config.post_download_playlist_path
		if not pl_path or pl_path.count('"')%2 != 0 or not os.path.exists(pl_path):
			log.warning("config.post_download_playlist_path is empty, malformed or does not exist. changing to config.post_download_action to 'ask'.")
			config.post_download_action = 'ask'
			
	### ONLINE CHECKS ###
	timestamp = math.fabs(time.time() - config.last_sanity_check_timestamp)
	if timestamp > 30*60: # if the last check was before more than 30 minutes
		# Newest version check
		try:
			newest_version = WebParser.WebServices.get_newestversion()
			if newest_version > float(__version__):
				log.warning("A new version of iQuality is available (%s)." % newest_version)
				_warnings.append(NewerVersionWarning(newest_version))
		except IOError as e:
			log.error("Could not check for the newest version (%s)" % str(e))
		
		# External Components Check
		if not os.path.exists('bin/'):
			os.makedirs('bin/')
			
		hash_failed = []
		not_exists = []
		
		d = WebParser.WebServices.get_components_data()
		for name, t in d.items():
			urls, archive_hash, file_to_extract, file_hash = t
			
			if not os.path.exists(r'bin\%s' % file_to_extract):
				log.warning('External component was not found: %s' % name)
				not_exists.append(name)
				continue
			
			computed_hash = utils.calc_sha256(r'bin\%s' % file_to_extract)
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