# Copyright (C) 2012-2013 Itay Brandes

'''
Logger class for the project.
Must call logger.start() to start logging, and logger.stop() to terminate the logger.
'''

import os
import sys
import logging, logging.handlers

log = logging.getLogger('mainLog')
log2 = logging.getLogger('minorLog')

def start(config):
	"Function sets up the logging environment."
	
	if not os.path.exists(os.path.dirname(config.logfile_path)):
		os.makedirs(os.path.dirname(config.logfile_path))
	logging.raiseExceptions = False # suppresses "No handlers could be found for logger X.Y.Z". Note that in python3 this behavior is changed, so we need to change this line if we ever port the project to python3.
	logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
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
	
def add_coloring_to_emit_windows(fn):
	# add methods we need to the class
	def _out_handle(self):
		import ctypes
		return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
	out_handle = property(_out_handle)

	def _set_color(self, code):
		import ctypes
		# Constants from the Windows API
		self.STD_OUTPUT_HANDLE = -11
		hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
		ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

	setattr(logging.StreamHandler, '_set_color', _set_color)

	def new(*args):
		FOREGROUND_BLUE      = 0x0001 # text color contains blue.
		FOREGROUND_GREEN     = 0x0002 # text color contains green.
		FOREGROUND_RED       = 0x0004 # text color contains red.
		FOREGROUND_INTENSITY = 0x0008 # text color is intensified.
		FOREGROUND_WHITE     = FOREGROUND_BLUE|FOREGROUND_GREEN |FOREGROUND_RED
	   # winbase.h
		STD_INPUT_HANDLE = -10
		STD_OUTPUT_HANDLE = -11
		STD_ERROR_HANDLE = -12

		# wincon.h
		FOREGROUND_BLACK     = 0x0000
		FOREGROUND_BLUE      = 0x0001
		FOREGROUND_GREEN     = 0x0002
		FOREGROUND_CYAN      = 0x0003
		FOREGROUND_RED       = 0x0004
		FOREGROUND_MAGENTA   = 0x0005
		FOREGROUND_YELLOW    = 0x0006
		FOREGROUND_GREY      = 0x0007
		FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

		BACKGROUND_BLACK     = 0x0000
		BACKGROUND_BLUE      = 0x0010
		BACKGROUND_GREEN     = 0x0020
		BACKGROUND_CYAN      = 0x0030
		BACKGROUND_RED       = 0x0040
		BACKGROUND_MAGENTA   = 0x0050
		BACKGROUND_YELLOW    = 0x0060
		BACKGROUND_GREY      = 0x0070
		BACKGROUND_INTENSITY = 0x0080 # background color is intensified.
		
		DEFAULT_CONSOLE_COLOR = FOREGROUND_GREY

		levelno = args[1].levelno
		if(levelno>=50): # CRITICAL
			color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY 
		elif(levelno>=40): # ERROR
			color = FOREGROUND_RED | FOREGROUND_INTENSITY
		elif(levelno>=30): # WARNING
			color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
		elif(levelno>=20): # INFO
			color = FOREGROUND_GREEN
		elif(levelno>=10): # DEBUG
			color = DEFAULT_CONSOLE_COLOR
		else:
			colo = DEFAULT_CONSOLE_COLOR
		args[0]._set_color(color)

		ret = fn(*args)
		args[0]._set_color(DEFAULT_CONSOLE_COLOR)
		return ret
	return new