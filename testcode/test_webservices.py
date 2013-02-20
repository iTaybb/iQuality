# coding: utf-8
import os, sys
import subprocess
import urllib2
import zipfile
from urlparse import parse_qs, urlparse, urlunparse


sys.path.append(r'C:\Scripts\iQuality\code')
import Main
from Main import utils
import Config; config = Config.config

#
# Test code
#

def test_connection():
	return subprocess.check_call('ping www.google.com -n 1', stdout=subprocess.PIPE)
	
def test_google_spellcheck():
	ans = Main.WebParser.WebServices.spell_fix('britn spirs')
	assert ans == "britney spears"
	
def test_google_spellcheck():
	ans = Main.WebParser.WebServices.google_autocomplete('naruto')
	assert len(ans) > 5
	
def test_google_images_search():
	ans = Main.WebParser.WebServices.googleImageSearch('naruto shippuden')
	assert isinstance(ans, list)
	assert len(ans) >= 3
	
	for url in ans:
		urllib2.urlopen(url).close()

def test_lyricsGrabber_LyricsMode():
	ans = Main.WebParser.LyricsGrabber.parse_LyricsMode('Call Me Maybe', 'Carly Rae Jaspen').next()
			
	assert "I threw a wish in the well" in ans.lyrics
	assert ans.artist.lower() == "carly rae jepsen"
	assert ans.title.lower() == "call me maybe"
	
def test_lyricsGrabber_onlylyrics():
	ans = Main.WebParser.LyricsGrabber.parse_onlylyrics('Overfly', 'Luna Haruna').next()
			
	assert "Takaku takaku" in ans.lyrics
	assert ans.artist.lower() == "luna haruna"
	assert ans.title.lower() == "overfly"
	
def test_lyricsGrabber_ChartLyrics():
	ans = Main.WebParser.LyricsGrabber.parse_LyricsMode('Rehab', 'Rihanna').next()

	assert "Baby, baby" in ans.lyrics
	assert ans.artist.lower() == "rihanna"
	assert ans.title.lower() == "rehab"
	
def test_lyricsGrabber_shironet():
	ans = Main.WebParser.LyricsGrabber.parse_shironet(u'עידן רייכל - שובי אל ביתי').next()
	
	assert u"שובי אל ביתי" in ans.lyrics
	assert ans.artist in [u"הפרוייקט של עידן רייכל", u"הפרויקט של עידן רייכל", u"עידן רייכל"]
	assert ans.title == u"שובי אל ביתי"
	
def test_MetadataGrabber_shironet_artist():
	ans = Main.WebParser.MetadataGrabber.shironet_artist_search(u'הפרויקט של עידן רייכל')
	artist = ans[0]
	
	assert int(artist.id) == 1333
	assert artist.has_albums
	
def test_MetadataGrabber_shironet_artist_songs():
	ans = Main.WebParser.MetadataGrabber.shironet_artist_songs("1333")
	tracks = [x.title for x in ans]

	assert len(tracks) > 20
	assert u"חלומות של אחרים" in tracks
	assert u"בין קירות ביתי" in tracks
	
def test_MetadataGrabber_shironet_artist_albums():
	ans = Main.WebParser.MetadataGrabber.shironet_artist_albums("1333")
	albums = [x.title for x in ans]
	
	assert len(albums) >= 4
	assert u"ממעמקים" in albums
	assert u"הביתה, הלוך חזור" in albums
	
def test_MetadataGrabber_shironet_album_songs():
	ans = Main.WebParser.MetadataGrabber.shironet_album_songs("1333", "87")
	
	assert len(ans) == 14
	assert u"רוב השעות" in ans
	assert "Maisha" in ans
	
def test_MetadataGrabber_shironet_songs_by_lyrics():
	ans = Main.WebParser.MetadataGrabber.parse_shironet_songs_by_lyrics(u"ויש שעות שמלאות כולן בריח שלה")
	
	assert ans == u"הפרויקט של עידן רייכל - רוב השעות"
	
def test_MetadataGrabber_songlyrics_songs_by_lyrics():
	ans = Main.WebParser.MetadataGrabber.parse_songlyrics_songs_by_lyrics("let the skyfall when it crumbles")
	
	assert ans == "Adele - Skyfall"
	
def test_MetadataGrabber_musicbrainz():
	ans = Main.WebParser.MetadataGrabber.parse_musicBrainz('Bebot', 'The Black Eyed Peas')
	
	date, country, artist, tag, title = ans['7c07d727-e1a6-47e8-82fa-ed802e95f523'].values()
	assert artist == "The Black Eyed Peas"
	assert date == '2005-06-07'
	assert country == 'US'
	assert tag in ['pop', 'hip-hop']
	assert title == 'Monkey Business'

def test_MetadataGrabber_musicbrainz_artist_search():
	ans = Main.WebParser.MetadataGrabber.musicbrainz_artist_search('adele')
	
	assert 'cc2c9c3c-b7bc-4b8b-84d8-4fbd8779e493' in [x.id for x in ans]
	
def test_MetadataGrabber_musicbrainz_release_search():
	albums, singles, others = Main.WebParser.MetadataGrabber.musicbrainz_release_search('cc2c9c3c-b7bc-4b8b-84d8-4fbd8779e493')
	
	assert '19' in [album.title for album in albums]
	assert '21' in [album.title for album in albums]
	
def test_MetadataGrabber_musicbrainz_recording_search():
	ans = Main.WebParser.MetadataGrabber.musicbrainz_recording_search('c45e0e0e-48c9-4441-aac3-2f2b34202d3c')
	
	assert "Rolling in the Deep" in ans
	assert "Lovesong" in ans

def test_parse_dilandau():
	ans = Main.WebParser.LinksGrabber.parse_dilandau('Flo Rida - Whistle')
	
	for i in range(3):
		x = ans.next().url
		assert x.startswith('http://')
		urllib2.urlopen(utils.url_fix(x))
		
def test_parse_Mp3skull():
	ans = Main.WebParser.LinksGrabber.parse_Mp3skull('LMFAO - Sexy and I know It')
	
	for i in range(3):
		x = ans.next().url
		assert x.startswith('http://')
		urllib2.urlopen(utils.url_fix(x))
		
def test_parse_soundcloud_api1():
	ans = Main.WebParser.LinksGrabber.parse_soundcloud_api1('Johnny Concept')
	
	for i in range(3):
		x = ans.next().url
		assert x.startswith('http://')
		urllib2.urlopen(utils.url_fix(x))
		
def test_parse_soundcloud_api2():
	ans = Main.WebParser.LinksGrabber.parse_soundcloud_api2(u'קרן פלס')
	
	for i in range(3):
		x = ans.next().url
		assert x.startswith('http://')
		urllib2.urlopen(utils.url_fix(x))
		
def test_parse_youtube_search():
	ans = Main.WebParser.LinksGrabber.search_Youtube('Psy - Gangnam Style', 10)
	
	global video_ids
	video_ids = [parse_qs(urlparse(watchurl).query)['v'][0] for watchurl in ans]
	assert len(video_ids) == 10
	for id in video_ids:
		assert len(id) == 11
		
def test_parse_youtube_videoinfo():
	" Uses get_video_info API "
	# run AFTER test_parse_youtube_search
	global video_ids
	global youtube_download_links
	youtube_download_links = []
	
	for id in video_ids:
		ans = Main.WebParser.LinksGrabber.get_youtube_dl_links(id)
		for stream in ans['fmt_stream_map']:
			url = stream['url']
			youtube_download_links.append(url)
			
def test_parse_youtube_downloadlinks():
	# run AFTER test_parse_youtube_videoinfo
	global youtube_download_links
	for url in youtube_download_links:
		assert 'youtube.com/videoplayback' in url
		assert 'signature=' in url
		urllib2.urlopen(url).close()

def test_parse_billboard():
	ans = Main.WebParser.WebServices.parse_billboard()
	assert len(ans) == 100
	assert len(ans[0]) > 2
	
def test_parse_uktop40():
	ans = Main.WebParser.WebServices.parse_uktop40()
	assert len(ans) == 40
	assert len(ans[0]) > 2
	
def test_parse_glgltz():
	ans = Main.WebParser.WebServices.parse_glgltz()
	assert 18 <= len(ans) <= 22
	assert len(ans[0]) > 2
	assert Main.utils.isHebrew(ans[0]) or Main.utils.isHebrew(ans[1]) or Main.utils.isHebrew(ans[2])
	
def test_parse_chartscoil():
	ans = Main.WebParser.WebServices.parse_chartscoil()
	assert 10 <= len(ans) <= 25
	assert len(ans[0]) > 2
	assert Main.utils.isHebrew(ans[0]) or Main.utils.isHebrew(ans[1]) or Main.utils.isHebrew(ans[2])

def test_get_currentusers():
	ans = Main.WebParser.WebServices.get_currentusers()
	assert isinstance(ans, int)
	
def test_get_newest_version():
	ans = Main.WebParser.WebServices.get_newestversion()
	assert isinstance(ans, float)
	
def test_get_components_data():
	d = Main.WebParser.WebServices.get_components_data()
	for name, t in d.items():
		urls, archive_hash, file_to_extract, file_hash = t
		
		for url in urls:
			obj = Main.SmartDL(url)
			obj.start()
			obj.wait()
			assert archive_hash == utils.calc_sha256(obj.get_dest())
		
		ext = os.path.splitext(obj.get_dest())[1].lower()
		assert ext in ['.zip', '.7z']
		
		tmpfile = utils.get_rand_filename(config.temp_dir)
		
		if ext == '.zip':
			zip = zipfile.ZipFile(obj.get_dest())
			zip.extract(file_to_extract, config.temp_dir)
		if ext == '.7z':
			cmd = r'7za.exe e %s -ir!%s -y -o"%s"' % (obj.get_dest(), file_to_extract, config.temp_dir)
			subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

		assert file_hash == utils.calc_sha256(r"%s\%s" % (config.temp_dir, file_to_extract))