# coding: utf-8
# Copyright (C) 2012-2013 Itay Brandes

'''Core modules and functions of the project'''

import os, sys
import subprocess, _subprocess
import random
import string
import re
import ctypes
from difflib import Differ
import xml.dom.minidom
import xml.parsers.expat
import shutil
import urllib
import urlparse
import hashlib

from win32com.shell import shell
from mutagen.compatid3 import CompatID3 # hack for IDv2.3 tags writing with mutagen
from mutagen.id3 import ID3NoHeaderError

__all__ = ['makeDummyMP3', 'setID3Tags', 'append_bold_changes', 'get_free_space',
			'module_path', 'launch_without_console', 'get_rand_string', 'get_rand_filename',
			'isHebrew', 'isAscii', 'isJibrish', 'fix_faulty_unicode', 'convert_html_entities',
			'combine_files', 'progress_bar', 'delete_duplicates_ordered', 'launch_file_explorer',
			'parse_title_from_filename', 'add_item_to_playlist', 'add_item_to_wpl_playlist',
			'add_item_to_m3u_playlist', 'add_item_to_itunes_playlist', 'move_item_to_top',
			'open_with_notepad', 'url_fix', 'trim_between', 'guess_image_mime_type', 
			'parse_artists_from_artist', 'calc_sha256']

def makeDummyMP3(dir_):
	'''
	Creates a dummy MP3 file with empty ID3 tags.
	@param dir_: Destination file folder.
	@type dir_: string
	
	@return: Dummy MP3 file path.
	@rtype: string
	'''
	path = get_rand_filename(dir_)
	with open(path, 'wb') as f:
		f.write('ID3\x04\x00\x00\x00\x00\x00\x00\xff\xfb\x90\x04\x00\x0f\xf0\x00\x00i\x00\x00\x00\x08\x00\x00\r \x00\x00\x01\x00\x00\x01\xa4\x00\x00\x00 \x00\x004\x80\x00\x00\x04UUU\xff\xfb\x92\x04@\x8f\xf0\x00\x00i\x00\x00\x00\x08\x00\x00\r \x00\x00\x01\x00\x00\x01\xa4\x00\x00\x00 \x00\x004\x80\x00\x00\x04')
	return path

def setID3Tags(ID3Tags, fn):
	'''
	Function sets ID3 Tags using the v2.3 format.
	@param ID3Tags: Dict of ID3 Tags (TIT2, TPE1, TDRC, etc).
	@type ID3Tags: dict
	@param fn: File for appending the ID3 data.
	@type fn: string
	'''
	if not ID3Tags:
		return
	
	try:
		ID3Obj = CompatID3(fn)
	except ID3NoHeaderError:
		with open(fn, 'rb') as f:
			data = f.read()
		data = 'ID3\x04\x00\x00\x00\x00\x00\x00' + data # Adding ID3 data
		with open(fn, 'wb') as f:
			f.write(data)
		ID3Obj = CompatID3(fn)
	
	for tagName, tagData in ID3Tags.items():
		ID3Obj.delall(tagName)
		if tagData:
			ID3Obj.add(tagData)
	
	ID3Obj.update_to_v23()
	ID3Obj.save(v2=3)
	
def parse_title_from_filename(fn):
	"Trying to parse title and artist out of filename"
	delims = ['-', ':', '|', '@']
	oppo_delims = [' by ']
	
	if '-' in fn and fn.count("-") > 1 and fn.count(" - ") == 1:
			artist, title = fn.split(" - ")
	elif [x for x in delims if x in fn]:
		deli = [x for x in delims if x in fn][0]
		t = fn.split(deli, 1)
		artist = t[0]
		title = deli.join(t[1:])
	elif [x for x in oppo_delims if x in fn]:
		deli = [x for x in oppo_delims if x in fn][0]
		t = fn.split(deli, 1)
		title = t[0]
		artist = deli.join(t[1:])
	else:
		title = fn
		artist = ""
	
	title = title.replace('_', ' ').replace('-', ' ').strip()
	artist = artist.replace('_', ' ').replace('-', ' ').strip()
	
	return title, artist
	
def parse_artists_from_artist(artist):
	'''Trying to parse different artist names from the artist field
	
	Possible variants:
	A,B
	A with B
	A and B
	A & B
	A Feat. B
	A Featuring B
	A וB
	A עם B
	'''
	delims = ['with', 'and', 'featuring', 'feat.', 'feat', '&',
			  'With', 'And', 'Featuring', 'Feat.', 'Feat',
			  
				u' ו', u' עם ', u' מארח את ', u' מארחת את ', u' מארחים את ']
	artists = []
				
	while [x for x in delims if x in artist]:
		deli = [x for x in delims if x in artist][0]
		x, artist = artist.split(deli, 1)
		artists.append(x)
	artists.append(artist)
	artists = [x.strip() for x in artists]
	
	return sorted(artists)
		
parse_artists_from_artist("A")

def append_bold_changes(s1, s2):
	"Adds <b></b> tags to words that are changed"
	l1 = s1.split(' ')
	l2 = s2.split(' ')
	dif = list(Differ().compare(l1, l2))
	return " ".join(['<b>'+i[2:]+'</b>' if i[:1] == '+' else i[2:] for i in dif if not i[:1] in '-?'])
	
def get_free_space(folder):
	"Returns folder/drive free space (in bytes)"
	drive = os.path.splitdrive(folder)[0]
	free_bytes = ctypes.c_ulonglong(0)
	ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive), None, None, ctypes.pointer(free_bytes))
	return free_bytes.value

def module_path(_file=__file__):
	"Function returns script dir. Works in console and py2exe mode."
	if hasattr(sys, "frozen"): # if compiled into py2exe
		return os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
	return os.path.dirname(unicode(_file, sys.getfilesystemencoding()))

def launch_without_console(cmd):
	"Function launches a process without spawning a window. Returns subprocess.Popen object."
	suinfo = subprocess.STARTUPINFO()
	suinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
	p = subprocess.Popen(cmd, -1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=suinfo)
	return p

def get_rand_string(length=8):
	"Function returns a random string of a specific length."
	return "".join(random.choice(string.letters + string.digits) for i in range(length))

def get_rand_filename(dir_=os.getcwd()):
	"Function returns a non-existent random filename."
	tempfile = r"%s\%s.tmp" % (dir_, get_rand_string())
	while os.path.exists(tempfile):
		tempfile = r"%s\%s.tmp" % (dir_, get_rand_string())
	return tempfile
	
def isHebrew(s):
	"Function checks if a string contains hebrew chars."
	return any(u"\u0590" <= c <= u"\u05EA" for c in s)

def isAscii(s):
	"Function checks is the string is ascii."
	try:
		s.decode('ascii')
	except (UnicodeEncodeError, UnicodeDecodeError):
		return False
	return True

def isJibrish(s):
	"Function checks is the string is Jibrish."
	if not isinstance(s, unicode):
		return False
	jibrish_letters_count = len(filter(lambda c: 128 <= ord(c) <= 256, s))
	return 1.0*jibrish_letters_count/len(s) > 0.5

def fix_faulty_unicode(s, encoding='cp1255'):
	'''
	Function fixes faulty strings, if any
	
	u'\xf9\xec\xe5\xed' --> u'\u05e9\u05dc\u05d5\u05dd'
	'''
	if not isinstance(s, unicode): #String is not unicode
		return s
	if s and isJibrish(s):
		return s.encode('latin-1').decode(encoding)
	return s
	
def url_fix(s, charset='utf-8'):
    '''
	Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.  This
    function can fix some of the problems in a similar way browsers
    handle data entered by the user:

    >>> url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffskl?rung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    :param charset: The target charset for the URL if the url was
                    given as unicode string.
					
	taken from werkzeug.utils
    '''
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))
	
def convert_html_entities(s):
	"Converts html entitles to ascii"
	matches = re.findall("&#\d+;", s)
	if len(matches) > 0:
		hits = set(matches)
		for hit in hits:
			name = hit[2:-1]
			try:
				entnum = int(name)
				s = s.replace(hit, unichr(entnum))
			except ValueError:
				pass
	
	matches = re.findall("&#[xX][0-9a-fA-F]+;", s)
	if len(matches) > 0:
		hits = set(matches)
		for hit in hits:
			hex = hit[3:-1]
			try:
				entnum = int(hex, 16)
				s = s.replace(hit, unichr(entnum))
			except ValueError:
				pass
	
	matches = re.findall("&\w+;", s)
	hits = set(matches)
	amp = "&amp;"
	if amp in hits:
		hits.remove(amp)
	for hit in hits:
		name = hit[1:-1]
		if htmlentitydefs.name2codepoint.has_key(name):
			s = s.replace(hit, unichr(htmlentitydefs.name2codepoint[name]))
	s = s.replace(amp, "&")
	return s 

def guess_image_mime_type(f):
	'''
	Function guesses an image mime type.
	Supported filetypes are JPG, BMP, PNG.
	'''
	with open(f, 'rb') as f:
		data = f.read(11)
	if data[:4] == '\xff\xd8\xff\xe0' and data[6:] == 'JFIF\0':
		return 'image/jpeg'
	elif data[1:4] == "PNG":
		return 'image/png'
	elif data[:2] == "BM":
		return 'image/x-ms-bmp'
	else:
		return 'image/unknown-type'

def combine_files(parts, path): # IMPROVE: remove it from here
	'''
	Function combines file parts.
	@param parts: List of file paths.
	@param path: Destination path.
	'''
	with open(path, 'wb') as output:
		for part in parts:
			with open(part, 'rb') as f:
				output.writelines(f.readlines())
			os.remove(part)
			
def progress_bar(progress, length=20):
	'''
	Function creates a textual progress bar.
	@param progress: Float number between 0 and 1 describes the progress.
	@param length: The length of the progress bar in chars. Default is 20.
	'''
	length -= 2 # The brackets are 2 chars long.
	return "[" + "#"*int(progress*length) + "-"*(length-int(progress*length)) + "]"

def delete_duplicates_ordered(seq):
	"Removing duplicates from a sequence preserving order"
	seen = set()
	seen_add = seen.add
	return [x for x in seq if x not in seen and not seen_add(x)]
			
def add_item_to_playlist(f, item):
	"wrapper for add_item_to_m3u_playlist and add_item_to_itunes_playlist"
	if os.path.splitext(f)[1] == '.m3u':
		add_item_to_m3u_playlist(f, item)
	elif os.path.splitext(f)[1] == '.wpl':
		add_item_to_wpl_playlist(f, item)
	else:
		raise RuntimeError('Playlist file is not supported.')
		
def add_item_to_wpl_playlist(wpl, item):
	"Function adds an item to a wpl playlist (application/vnd.ms-wpl)"
	if not os.path.exists(item):
		raise IOError('%s does not exists.' % item)
	if not os.path.exists(wpl):
		raise IOError('%s does not exists.' % wpl)
	
	try:
		doc = xml.dom.minidom.parse(wpl)
	except xml.parsers.expat.ExpatError:
		raise IOError('%s is not a valid wpl file.' % wpl)
	seq = doc.getElementsByTagName('smil')[0].getElementsByTagName('body')[0].getElementsByTagName('seq')[0]
	
	if not item in seq.toxml():
		x = doc.createElement('media')
		x.setAttribute("src", item)
		seq.appendChild(x)
		
		output = doc.toprettyxml()
		
		# fix for toprettyxml()
		# taken from http://ronrothman.com/public/leftbraned/xml-dom-minidom-toprettyxml-and-silly-whitespace/
		fix = re.compile(r'((?<=>)(\n[\t]*)(?=[^<\t]))|(?<=[^>\t])(\n[\t]*)(?=<)')
		fixed_output = re.sub(fix, '', output)
		
		wpl_bak = wpl + ".bak"
		if os.path.exists(wpl_bak):
			os.unlink(wpl_bak)
		shutil.copyfile(wpl, wpl_bak)
		
		try:
			with open(wpl, 'w') as f:
				f.write(fixed_output.encode('utf-8'))
			os.unlink(wpl_bak)
		except Exception, e:
			# restore the backup
			if os.path.exists(wpl):
				os.unlink(wpl)
			shutil.copyfile(wpl_bak, wpl)
			os.unlink(wpl_bak)
			
			# raise the original exception
			raise e

def add_item_to_m3u_playlist(m3u, item):
	"Function adds an item to a m3u playlist (audio/x-mpegurl)"
	if not os.path.exists(item):
		raise IOError('%s does not exists.' % item)
	if not os.path.exists(m3u):
		raise IOError('%s does not exists.' % m3u)
		
	with open(m3u, 'r+') as f:
		data = f.read()
		if not item in data:
			f.seek(0, 1) # workaround for issue 1521491
			
			f.write("#EXTINF:0,%s\n" % item.split('\\')[-1])
			f.write(item + "\n\n")

def add_item_to_itunes_playlist(item):
	"Adds item to iTunes playlist"
	dst = os.path.expanduser(r'~\My Documents\My Music\iTunes\iTunes Media\Automatically Add to iTunes')
	
	if not os.path.exists(item):
		raise IOError('%s does not exists' % item)
	if not os.path.exists(dst):
		raise IOError('%s does not exists' % dst)
	
	shutil.copy(item, dst)

def create_win_shortcut(src, dst):
	"Creates a windows shortcut (.lnk file). Requires win32api"
	shell = win32com.client.Dispatch("WScript.Shell")
	shortcut = shell.CreateShortCut(dst)
	shortcut.Targetpath = src
	shortcut.save()
	
def move_item_to_top(val, l):
	"Function moves an item to the top"
	l.insert(0, l.pop(l.index(val)))

def open_with_notepad(s):
	"Function gets a string and shows it on notepad"
	with open(get_rand_filename(), 'w') as f:
		f.write(s)
		subprocess.Popen(['notepad', f.name])

def trim_between(s, x='(', y=')'):
	'''
	Trims everything in s between x and y
	
	f("Skrillex (Dubstep Remix)") ==> "Skrillex"
	'''
	while s.count(x) == s.count(y) > 0 and s.find(x) < s.find(y):
		s = s[:s.find(x)] + s[s.find(y)+1:]
		s = s.replace('  ',' ')
	return s
	
def launch_file_explorer(path, files=None):
	'''
	Given a absolute base path and names of its children (no path), open
	up one File Explorer window with all the child files selected
	
	Taken from http://mail.python.org/pipermail/python-win32/2012-September/012533.html
	'''
	if not files:
		path, files = os.path.split(path)
		files = [files]
	else:
		files = [os.path.basename(f) for f in files]
		
	if sys.getwindowsversion().major == 5: #if windows xp
		folder_pidl = shell.SHILCreateFromPath(path, 0)[0]
		desktop = shell.SHGetDesktopFolder()
		shell_folder = desktop.BindToObject(folder_pidl, None, shell.IID_IShellFolder)
		name_to_item_mapping = dict([(desktop.GetDisplayNameOf(item, 0), item) for item in shell_folder])
		to_show = []
		for f in files:
			if name_to_item_mapping.has_key(f):
				to_show.append(name_to_item_mapping[f])
			# else:
				# raise Exception('f: "%s" not found in "%s"' % (f, path))
			
		shell.SHOpenFolderAndSelectItems(folder_pidl, to_show, 0)
	else: # no SHILCreateFromPath in windows 7
		f = r"%s\%s" % (path, files[0])
		f_mbcs = f.encode('mbcs')
		if os.path.exists(f_mbcs):
			os.system(r'explorer /select,"%s"' % f_mbcs)
		else:
			os.startfile(path)
			
def calc_sha256(path):
	"Gets a file and calculates it's sha224 digest."
	with open(path, 'rb') as f:
		hash = hashlib.sha256(f.read()).hexdigest()
	return hash