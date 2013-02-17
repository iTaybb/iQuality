# Copyright (C) 2012-2013 Itay Brandes

'''
Logger class for the project.
Must call logger.start() to start logging, and logger.stop() to terminate the logger.
'''

import logging, logging.handlers
import sys

log = logging.getLogger('mainLog')
log2 = logging.getLogger('minorLog')

def start(config):
	"Function sets up the logging environment."
	logging.raiseExceptions = False # suppresses "No handlers could be found for logger X.Y.Z". Note that in python3 this behavior is changed, so we need to change this line if we ever port the project to python3.
	log.setLevel(logging.DEBUG)
	log2.setLevel(logging.DEBUG)
	formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%d-%m-%y %H:%M:%S')
	
	if config.logfile_enable:
		filehandler = logging.handlers.RotatingFileHandler(config.logfile_path, maxBytes=config.logfile_maxsize, backupCount=config.logfile_backupCount)
		filehandler.setLevel(logging.DEBUG)
		filehandler.setFormatter(formatter)
		log.addHandler(filehandler)
		
	if config.logfile2_enable:
		filehandler = logging.handlers.RotatingFileHandler(config.logfile2_path, maxBytes=config.logfile2_maxsize, backupCount=config.logfile2_backupCount)
		filehandler.setLevel(logging.DEBUG)
		filehandler.setFormatter(formatter)
		log2.addHandler(filehandler)
		
	if not hasattr(sys, "frozen"): # if not py2exe
		console = logging.StreamHandler()
		console.setLevel(logging.DEBUG)
		console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s')) # nicer format for console
		log.addHandler(console)
		
		console = logging.StreamHandler()
		console.setLevel(logging.DEBUG)
		console.setFormatter(logging.Formatter('[calcScore] %(message)s')) # nicer format for console
		log2.addHandler(console)

	# Levels are: debug, info, warning, error, critical.
	log.debug("Started logging to %s [maxBytes: %d, backupCount: %d]" % (config.logfile_path, config.logfile_maxsize, config.logfile_backupCount))
	log2.debug("Started calcScore logging to %s [maxBytes: %d, backupCount: %d]" % (config.logfile2_path, config.logfile2_maxsize, config.logfile2_backupCount))

def stop():
	"Function closes and cleans up the logging environment."
	logging.shutdown()
	
def create_debugging_logger():
	"Creates a debugging logger that prints to console."
	t_log = logging.getLogger('testingLog')
	t_log.setLevel(logging.DEBUG)
	console = logging.StreamHandler()
	console.setLevel(logging.DEBUG)
	# console.setFormatter(logging.Formatter('[%(levelname)s@%(thread)d] %(message)s'))
	console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
	t_log.addHandler(console)
	return t_log