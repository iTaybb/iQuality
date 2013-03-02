# coding: utf-8
import os, sys

sys.path.append(r'C:\Scripts\iQuality\code')
import Main

def test_codeLength():
	dirs = [r"C:\Scripts\iQuality\code", r"C:\Scripts\iQuality\testcode"]
	exclude = []
	count = 0
	
	py_files = []
	for d in dirs:
		for root, dirs, files in os.walk(d):
			files = [r"%s\%s" % (root, f) for f in files if f.endswith('.py')]
			if files:
				py_files.extend(files)

	for path in py_files:
		with open(path,'rb') as f:
			count += len(f.readlines())

	print "Project iQuality has %d code lines." % count
	assert 500 < count < 10000

def test_PyEnviron():
	try:
		import win32api
		import win32com
		import PyQt4
		import py2exe
		from bs4 import BeautifulSoup
		import mutagen
		import mutagen.compatid3
		'''
		this is a workaround for mutagen for writing IDv2.3 tags.
		grab from http://bazaar.launchpad.net/~musicbrainz-developers/picard/trunk/annotate/head%3A/picard/formats/mutagenext/compatid3.py
		or https://groups.google.com/forum/?fromgroups#!topic/quod-libet-development/krPCx4hhM_Q
		put in mutagen's installed folder.
		'''
		import configparser
		#this is the python3 version of ConfigParser. a backport for python2 is available.
		import pytest
		import rsa

	except ImportError, e:
		raise Exception("Depencency not found: %s" % str(e))
		
	if sys.version_info < (2, 6) or sys.version_info >= (3, 0):
		raise Exception("must use python 2.7")

if __name__ == '__main__':
	test_codeLength()
	raw_input("Press enter to continue . . .")