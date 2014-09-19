# coding: utf-8
# Copyright (C) 2012-2014 Itay Brandes

'''
Module for program custom exceptions and warnings.
'''

import Config; config = Config.config

__version__ = Config.__version__
__date__ = Config.__date__
__author__ = 'Itay Brandes (akari.il@gmail.com)'

### EXCEPTIONS ###
class NoResultsException(Exception):
	def __init__(self, isDirectLink=False):
		self.isDirectLink = isDirectLink
	
class NoInternetConnectionException(Exception): pass

class NoDnsServerException(Exception): pass
	
class NotSupportedFiletypeException(Exception):
	def __init__(self, ext):
		self.ext = ext

class FileInUseException(Exception):
	def __init__(self, f):
		self.f = f
		
class YoutubeException(Exception):
	def __init__(self, errorcode, reason):
		self.errorcode = int(errorcode)
		self.reason = reason
		
		'''
		This is regular Youtube error codes. The following
		are extras that the application adds:
		
		* Error -100: Could not decipher video's secret signature.
		'''
	def __str__(self):
		return "Error %d: %s" % (self.errorcode, self.reason)

### WARNINGS ###
class NoSpaceWarning(Warning):
	def __init__(self, drive, space):
		self.drive = drive
		self.space = int(space)
	def __str__(self):
		return "Drive: %s, Space Remaining: %d" % (self.drive, self.space)
		
class ComponentsFaultyWarning(Warning):
	def __init__(self, components):
		self.components = components

class NewerVersionWarning(Warning):
	def __init__(self, newest, current=__version__, eskyObj=None):
		self.newest = newest
		self.current = current
		self.esky = eskyObj
	def __str__(self):
		return "Version v%s is the latest version. You have v%s." % (self.newest, self.current)