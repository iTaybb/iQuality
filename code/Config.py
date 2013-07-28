# coding: utf-8
# Copyright (C) 2012-2013 Itay Brandes

'''
A configuration class. Settings in the 'd' dict are the default settings.
To initilize the configuration class, just run:
		config = ConfigInterface(d, ini_file, vars_to_save)
where:
		d is the dict of the default settings.
		ini_file is the ini file path.
		vars_to_save is a list with items from the 'd' dict that we want to save in the ini file.
recommended approch in classes would be:
		import Config; config = Config.config

After intilization, we can access the dict members as if they were the class members:
		print config.appStyle
		config.appStyle = "A"

Supported vars are the bultin ones. For custom classes, the __str__ call must return the construct code of the class. The script will save the vars as str(x), and then will try to eval() them.
The code can handle defaultdict values, where the str() call will be translated to the construct code automatically:
defaultdict(<type 'bool'>, {}) --> defaultdict(bool, {})
defaultdict(<method-wrapper 'next' of itertools.repeat object at 0x018EF6F0>, {}) --> defaultdict(itertools.repeat(True).next, {})

Script will save the .ini file in every varaible assignment (if it's in the vars_to_have list).
You can explicitly call config.loadFromIni() or config.saveToIni(), but it's not needed.
Also you may use the 'restoreToDefault()' function in order to restore the settings (remove the .ini file).
A restart of the application will be required.
'''

import os
import codecs
import configparser # python3 ConfigParser, backported to python2.
from collections import defaultdict, OrderedDict
import itertools
import re
import threading

from win32com.shell import shell, shellcon

__version__ = "0.191"
__rev__ = 185 # auto-generated
__date__ = '09/07/13'
__author__ = 'Itay Brandes (Brandes.Itay@gmail.com)'

class ConfigInterface(object):
	'Look Above'
	def __init__(self, d, ini_path, vars_to_save, vars_to_eval):
		self.d = d
		self.original_dict = d.copy()
		self.ini_path = ini_path
		self.vars_to_save = vars_to_save
		self.vars_to_eval = vars_to_eval
		
		self.timerIsRunning = False
		self.loadFromIni()

	def loadFromIni(self):
		'Loads data from INI file'
		if not os.path.exists(self.ini_path):
			return
			
		obj = configparser.RawConfigParser()
		obj.optionxform = unicode # Enable case sensitive
		try:
			obj.readfp(codecs.open(self.ini_path, 'rb', 'utf-8'))
		except configparser.MissingSectionHeaderError:
			# os.unlink(self.ini_path)
			return
		
		if not 'Settings' in obj.sections():
			return
		
		for k, v in obj.items('Settings'):
			if k in vars_to_override:
				continue
				
			if k in vars_to_eval:
				self.d[k] = eval(v)
			else:
				self.d[k] = v
	
	def saveToIni(self):
		'Saves data to INI file'
		self.timerIsRunning = False

		obj = configparser.RawConfigParser()
		obj.optionxform = unicode # Enable case sensitive
		obj.add_section('Settings')
		
		items_dict = {k:v for k, v in self.d.items() if k in self.vars_to_save}
		
		for k, v in items_dict.items():
			if isinstance(v, defaultdict):
				def_factory_name = v.default_factory.__name__ # bool
				if def_factory_name == 'next':
					v = re.sub("<(.+)>", "itertools.repeat(True).next", unicode(v))
				else:
					v = re.sub("<(.+)>", def_factory_name, unicode(v))
			obj.set('Settings', k, v)
		
		with codecs.open(self.ini_path, 'wb', 'utf-8') as f:
			obj.write(f)
	
	def restoreToDefault(self):
		'Restores configuration to the default values'
		self.d = self.original_dict
		if os.path.exists(self.ini_path):
			os.unlink(self.ini_path)

	def __getattr__(self, key):
		return self.d[key]
	
	def __setattr__(self, key, value):
		if key in self.__dict__.keys() or key in ['d', 'ini_path', 'vars_to_save', 'original_dict', 'vars_to_eval', 'timerIsRunning']:
		# if it does exist, or one of the newly created ini_path, d, vars_to_save and original_dict.
			self.__dict__[key] = value
		else:
			self.__dict__['d'][key] = value
			
			# The saveToIni function saves all the dict's items to an ini file at every
			# object's setattr call. If 80 setattr calls are made in the last 120ms, then
			# the file will be written from scratch every time. The time is here to limit
			# the calls, and make the function more efficient.
			if not self.timerIsRunning:
				self.timerIsRunning = True
				threading.Timer(1.5, self.saveToIni).start() # will run self.saveToIni in 1.5 seconds.
				
### CODE ###
try:
	config.ini_path
except NameError: # if not already initialized
	import utils
	tr = utils.qt.tr
	
	d = {
		### GUI ###
		'windowTitle': "iQuality v%s beta" % __version__,
		'bottomLabel': u"iQuality© v%s beta by Itay Brandes (r%d, released on %s)" % (__version__, __rev__, __date__), # used only on credits_text
		'appStyle': "plastique", # "windows", "motif", "cde", "plastique", "windowsxp", or "macintosh".
		'mainWindow_resolution': (1000, 475),
		'table_DefaultSectionSize': 19,
		'table_font': ("Segoe UI", 10), # QtGui.QFont
		'mainWindow_styleSheet': "",
		'table_styleSheet': "background: #C9C5BD;",
		'table_odd_color': (206, 206 ,206), # QtGui.QColor
		'table_even_color': (189, 189, 189), # QtGui.QColor
		'table_foreground_color': (115, 115, 115), # QtGui.QColor
		
		'status_txt_font': ("Segoe UI", 20, 75), # QtGui.QFont, 75 is QtGui.QFont.Bold
		'browser_height': 85,
		'show_ads': False, # auto-generated
		
		### WebServices ###
		'website': "http://iquality.itayb.net",
		'facebook_page': 'http://www.facebook.com/iQualitySoftware',
		'browser_website': "http://iquality.itayb.net/version-{0}.php?v=%s" % __version__,
		'online_users_counter_webpage': "http://iquality.itayb.net/visitors.php?echo=1",
		'newest_version_API_webpage': "http://iquality.itayb.net/vars.php?show=newest_version",
		'components_json_url': 'http://iquality.itayb.net/components.json',
		'packages_json_url': 'http://iquality.itayb.net/packages.json',
		'use_local_json_files': False, # for dev only
		'local_json_files_path': r'C:\Scripts\iquality-misc\json', # for dev only

		### Script ###
		'temp_dir': r"%s\iQuality" % os.environ["Temp"],
		'id3tags_whitemark': "Downloaded by iQuality v%s (grab at http://iquality.itayb.net). If you've liked this track, please consider purchasing it and support the artists." % __version__,
		'logfile_enable': True,
		'logfile_path': r"%s\debug.log" % utils.module_path(__file__),
		'logfile_maxsize': 100*1024, # 100KB
		'logfile_backupCount': 0,
		'logfile2_enable': True,
		'logfile2_path': r"%s\debug.calcScore.log" % utils.module_path(__file__),
		'logfile2_maxsize': 250*1024, # 250KB
		'logfile2_backupCount': 0,
		'pubkey_path': r"%s\public.key" % utils.module_path(__file__),
		
		### Thread Counts ###
		'buildSongObjs_processes': 7,
		'search_processes': 3,
		'DownloadFile_Parall_processes': 6,
		'GoogleImagesGrabber_processes': 3,
		
		### Processes & Timeouts ###
		'is_ServerSupportHTTPRange_timeout': 8,
		'get_filesize_timeout': 6,
		'LinksGrabber_timeout': 8,
		'metadata_timeout': 5,
		'webservices_timeout': 4,
		'GoogleImagesGrabber_timeout': 5,
		'GoogleImagesGrabber_maxsize': 650*1024, # 650KB
		'get_id3info_timeout': 4,
		'memoize_timeout': 30*60, # 30 mins
		'id3_noask_wait_interval': 4,
		'interval_between_network_sanity_checks': 5*60, # IMPROVE: make the interval.
		'interval_between_supportArtists_notices': ((60**2)*24)*10, # 10 days
		
		### ETC ###
		'lang': '',
		'lang_rtl': {'en_US': False, 'he_IL': True}, # bool is for Is RightToLeft (Hebrew, Arabic)
		'lang_names': {'en_US': 'English', 'he_IL': 'Hebrew'},

		'WebParser_ignoredSites': ['4shared.com', 'soundcloud.com', 'free.fr', 'gendou.com', 'ringtonematcher.com', 'fileden.com'],
		'youtube_quality_priority': ['hd1080', 'hd720', 'large', 'medium', 'small'],
		'youtube_formats_priority': ['mp4', 'webm', 'flv'],
		'youtube_listen_quality_priority': ['medium', 'large' 'small'],
		'youtube_listen_formats_priority': ['flv'],
		'youtube_audio_bitrates': {'hd1080': 192000, 'hd720': 192000, 'large': 128000, 'medium': 128000, 'small': 96000},
		# call keys() to get the available sources list. query each value for it's state. True means Enabled, False means Disabled.
		'search_sources': defaultdict(itertools.repeat(True).next, {'Dilandau': True, 'Mp3skull': True, 'soundcloud': True,
																		'bandcamp': True, 'youtube': True}),
		'search_sources_const': ['Dilandau', 'Mp3skull', 'soundcloud', 'bandcamp', 'youtube'],
		
		'songs_count_spinBox': 15,
		'relevance_minimum': 2.0,
		'listen_volumeSlider_volume': 1.0,
		
		'generic_http_headers': {'User-Agent' :'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'},
		
		'allowd_web_protocols': ['http', 'https', 'ftp'],

		### Etc ###
		'enableSpellCheck': True,
		'downloadAudio': True,
		'downloadVideo': False,
		'trimSilence': False,
		'editID3': True,
		'search_autocomplete': True,
		'prefetch_charts': True,
		'parse_links_from_clipboard_at_startup': True,
		'artist_lookup': True,
		'lyrics_lookup': True,
		'id3editor_in_context_menu': True,
		
		# Table DoubleClick Task
		'table_doubleClick_action_dict': OrderedDict({'listen': tr('Listen'),
													'download': tr('Download'), 
													'nothing': tr('Nothing')}),
		'table_doubleClick_action': "listen",
		
		# Post Download Task
		'post_download_action_dict': OrderedDict({'runMultimedia': tr('Run Multimedia File'),
													'openDir': tr('Open Directory'), 
													'addItunes': tr('Add to iTunes'),
													'addPlaylist': tr('Add to a Playlist'),
													'customLaunch': tr('Run an application'),
													'ask': tr('Ask'),
													'nothing': tr('Nothing')}),
		'post_download_action': "ask",
		
		# ID3 Tags Task
		'id3_action_dict': OrderedDict({'noask': tr('Choose albumart for me & close window afterwards'),
										'ask': tr('Choose albumart for me, but the window open'),
										'ask_albumart': tr('Let me choose an albumart')}),		
		'id3_action': 'ask_albumart',
		
		'is_itunes_installed': True, # will be checked on sanity check
		'post_download_playlist_path': "",
		'post_download_custom_cmd': "",
		'post_download_custom_wait_checkbox': True,
		
		# Statistics
		'count_application_runs': 1,
		'count_download': 0,
		'show_supportArtists_notice': True,
		'last_supportArtists_notice_timestamp': 0,
		'last_sanity_check_timestamp': 0, # timestamp of the last successful full sanity check
		
	### Credits ###
	'credits_text': u'''
%s

This application uses code parts from the following frameworks, and we thank them for their help:
Python
Qt Project
PyQt
FFmpeg
Mutagen
SoX
BeautifulSoup
py2exe
Inno Setup
MusicBrainz
Google API (for spell checking)
Google Images (for album art)
Billboard (For Hot 100 Chart)
Galgalatz (For Hebrew Top 25 Chart)
Charts.co.il (For Hebrew Top 20 Chart)

Graphics:
Sarai Abergel

The Videos & Audio sources:
%s

The lyrics sources:
LyricsMode.com
ChartLyrics.com
SongLyrics.com
OnlyLyrics.com
shironet.mako.co.il

iQuality Copyright© 2012-2013 by Itay Brandes (iTayb). All rights reserved.
'''}
	d['credits_text'] = d['credits_text'] % (d['bottomLabel'], "\n".join(d['search_sources'].keys()))
	
	# that's probably the only way to get the UNICODE home folder on windows.
	home_folder = shell.SHGetFolderPath(0, shellcon.CSIDL_PROFILE, None, 0)
	default_dl_dir_win7 = r"%s\Downloads" % home_folder
	default_dl_dir_winxp = r"%s\My Documents\Downloads" % home_folder
	if os.path.exists(default_dl_dir_win7):
		d['dl_dir'] = default_dl_dir_win7
	elif os.path.exists(default_dl_dir_winxp):
		d['dl_dir'] = default_dl_dir_winxp
	else:
		d['dl_dir'] = "C:\\"
	d['ver'] = __version__

	ini_path = r'%s\config.ini' % utils.module_path(__file__)
	vars_to_save = ['dl_dir', 'temp_dir', 'ver', 'youtube_formats_priority', 'post_download_custom_cmd',
					'table_doubleClick_action', 'enableSpellCheck', 'downloadAudio', 'downloadVideo',
					'songs_count_spinBox', 'relevance_minimum', 'editID3', 'post_download_playlist_path',
					'post_download_action', 'lang', 'search_sources', 'youtube_quality_priority',
					'id3_action', 'count_application_runs', 'count_download', 'listen_volumeSlider_volume',
					'post_download_custom_wait_checkbox', 'prefetch_charts',
					'artist_lookup', 'lyrics_lookup', 'search_autocomplete', 'parse_links_from_clipboard_at_startup',
					'id3editor_in_context_menu', 'last_sanity_check_timestamp', 'trimSilence',
					'show_supportArtists_notice', 'last_supportArtists_notice_timestamp']
	vars_to_eval = ['relevance_minimum', 'downloadAudio', 'downloadVideo', 'ver', 'youtube_quality_priority',
					'youtube_formats_priority', 'enableSpellCheck', 'songs_count_spinBox', 'search_sources',
					'editID3', 'count_application_runs', 'count_download', 'listen_volumeSlider_volume',
					'post_download_custom_wait_checkbox', 'prefetch_charts',
					'artist_lookup', 'lyrics_lookup', 'search_autocomplete', 'parse_links_from_clipboard_at_startup',
					'id3editor_in_context_menu', 'last_sanity_check_timestamp', 'trimSilence',
					'show_supportArtists_notice', 'last_supportArtists_notice_timestamp']
	vars_to_override = ['ver']

	config = ConfigInterface(d, ini_path, vars_to_save, vars_to_eval)