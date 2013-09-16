import sys
import os
import shutil
from glob import glob
import pdb
from zipfile import ZipFile

from distutils.core import setup
from esky import bdist_esky
from esky.bdist_esky import Executable
import py2exe

# win32com.shell workaround START
# taken from: http://www.py2exe.org/index.cgi/win32com.shell

# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
try:
    # py2exe 0.6.4 introduced a replacement modulefinder.
    # This means we have to add package paths there, not to the built-in
    # one.  If this new modulefinder gets integrated into Python, then
    # we might be able to revert this some day.
    # if this doesn't work, try import modulefinder
    try:
        import py2exe.mf as modulefinder
    except ImportError:
        import modulefinder
    import win32com, sys
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    for extra in ["win32com.shell"]: #,"win32com.mapi"
        __import__(extra)
        m = sys.modules[extra]
        for p in m.__path__[1:]:
            modulefinder.AddPackagePath(extra, p)
except ImportError:
    # no build path setup, no worries.
    pass
	
# win32com.shell workaround END

def do_magic_in_file(_file, regex, x, y):
	'''
	Search in _file for regex (basic only). When found, replace in that line 'x' with 'y'.
	'''
	with open(_file, 'r') as f:
		data = f.readlines()
	for i,val in enumerate(data):
		if regex in val:
			if x in val:
				print "found %s at line %d. replacing '%s' with '%s'..." % (val.strip(), i+1, x, y)
				data[i] = val.replace(x, y)
			else:
				print "found %s, didn't found %s." % (regex, x)
			
			with open(_file, 'w') as f:
				f.writelines(data)
				
inno_setup_iscc_path = r'C:\Program Files\Inno Setup 5\iscc.exe' if os.path.exists(r'C:\Program Files\Inno Setup 5\iscc.exe') else r'C:\Program Files (x86)\Inno Setup 5\iscc.exe'
rar_path = r'C:\Program Files\WinRAR\WinRar.exe' if os.path.exists(r'C:\Program Files\WinRAR\WinRar.exe') else r'C:\Program Files (x86)\WinRAR\WinRar.exe'
msvcp90_dll_folder = r"C:\Program Files\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT" if os.path.exists(r"C:\Program Files\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT") else r"C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT"
if not os.path.exists(msvcp90_dll_folder):
	msvcp90_dll_folder = r"C:\Windows\winsxs\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.30729.4137_none_508fc1d4bcbb3eca"
code_dir = r"C:\Scripts\iQuality"
bump_rev = True
make_installer = True
update_iss_version = True
GUI_ONLY = True
override_app_version = "0.20" # None for no overriding, a new version number for overriding (string)
override_app_date = '17/09/13' # None for no overriding, a new date for overriding (string)

# Sanity checks
if not os.path.exists(code_dir):
	sys.exit(r'Error: %s doesn\'t exist' % code_dir)
if not os.path.exists(inno_setup_iscc_path):
	sys.exit("Error: inno_setup_iscc_path was not found")
if not os.path.exists(rar_path):
	sys.exit("Error: rar_path was not found")
if not os.path.exists(msvcp90_dll_folder):
	sys.exit("Error: msvcp90_dll_folder was not found")

os.chdir(code_dir)
sys.path.append(os.path.join(code_dir, "code"))
sys.path.append(msvcp90_dll_folder)

__version__ = str(__import__('Config').__version__)
__date__ = str(__import__('Config').__date__)
rev = __import__('Config').__rev__
if 'bdist_esky' in sys.argv:
	if override_app_version:
		do_magic_in_file(r'code\Config.py', "__version__ =", __version__, override_app_version)
		__version__ = override_app_version
	if override_app_date:
		do_magic_in_file(r'code\Config.py', "__date__ =", __date__, override_app_date)
		__date__ = override_app_date
	if make_installer and update_iss_version:
		x = [x for x in open('install.iss').readlines() if '#define MyAppVersion' in x]
		if not x:
			sys.exit("Didn't find MyAppVersion in install.iss file'")
		iis_MyAppVersion = x[0].split()[2].strip('"')
		do_magic_in_file(r'install.iss', "#define MyAppVersion", iis_MyAppVersion, __version__)


	new_rev = rev+1
	if bump_rev:	
		do_magic_in_file(r'code\Config.py', "__rev__", str(rev), str(new_rev))

	print "Building iQuality (rev %d)..." % new_rev
	print "Setting show_ads to True"
	do_magic_in_file(r'code\Config.py', "'show_ads':", "False", "True")

	os.chdir(r'code\ts')
	os.system(r'C:\Python27\lib\site-packages\PyQt4\lrelease.exe ts.pro')
	
os.chdir(code_dir)

py2exe_data_files = [
						('phonon_backend', [r'C:\Python27\Lib\site-packages\PyQt4\plugins\phonon_backend\phonon_ds94.dll']),
						('imageformats', glob(r'C:\Python27\Lib\site-packages\PyQt4\plugins\imageformats\*.dll')),
						("pics", glob(r'code\pics\*.*')),
						("ts", glob(r'code\ts\*.qm')),
						("", glob('*.md')+[r'code\public.key'])
							]

freeze_includes = ["mutagen.id3", "mutagen.easyid3", 'sip', 'win32api', 'lxml.etree', 'lxml._elementpath', 'gzip']
freeze_excludes = ['doctest', 'unittest', 'pdb', '_ssl', 'pyreadline', 'locale', 'calender']

py2exe_options = {
					"includes": freeze_includes, 
					'excludes': freeze_excludes,
					'compressed': 'True',
					"optimize": 2,
					'bundle_files': 3,
					'dll_excludes': ['w9xpopen.exe']
						}
bdist_esky_options_py2exe = {
								"freezer_options": py2exe_options,
								"freezer_module": "py2exe"
								}
								
iquality_exe = Executable(
	name = 'iQuality',
	gui_only = GUI_ONLY,
	description = 'High Quality Songs Downloader',
	script = os.path.join(code_dir, "code", "Gui.py"),
	icon_resources = [(1, os.path.join(code_dir, "code", "pics", "iQUACK.ico"))]
	)

setup(
	name = "iQuality",
	version = __version__,
	description='High Quality Songs Downloader',
	author='Itay Brandes',
	author_email='brandes.itay@gmail.com',
	url='http://iquality.itayb.net/',
	data_files = py2exe_data_files,
	# windows = [{"script": os.path.join(code_dir, "code", "Gui.py"),
				# 'uac_info': "requireAdministrator",
				# "icon_resources": [(1, os.path.join(code_dir, "code", "pics", "iQUACK.ico"))],
				# "dest_base": "iQuality"},
				# ],
	scripts = [iquality_exe],
	options = {"py2exe": py2exe_options, "bdist_esky": bdist_esky_options_py2exe},
	zipfile = None,
	)
	
if 'bdist_esky' in sys.argv:
	print "Setting show_ads to False"
	do_magic_in_file(r'code\Config.py', "'show_ads':", "True", "False")

	# extract zipfile
	fn = "iQuality-%s.win32" % __version__
	zip = ZipFile(r"dist\%s.zip" % fn)
	zip.extractall(r"dist\%s" % fn)

	# fix to esky's proper structure
	os.makedirs(r"dist\%s\appdata" % fn)
	shutil.move(r'dist\%s\%s' % (fn, fn), r'dist\%s\appdata' % fn)

	os.makedirs(r"dist\%s\phonon_backend" % fn)
	shutil.copy(r'C:\Python27\Lib\site-packages\PyQt4\plugins\phonon_backend\phonon_ds94.dll', r"dist\%s\phonon_backend" % fn)

	shutil.copytree(r'C:\Python27\Lib\site-packages\PyQt4\plugins\imageformats', r"dist\%s\imageformats" % fn)

if make_installer and not 'bdist_esky_patch' in sys.argv:
	if 'bdist_esky' in sys.argv:
		os.chdir(r"C:\Scripts\iQuality")
		os.system('"%s" install.iss' % inno_setup_iscc_path)
		
		os.chdir(r"C:\Scripts\iQuality\dist")
		os.system('"%s" a -m0 -afzip iQuality-%s-installer.zip iQuality-%s-installer.exe' % (rar_path, __version__, __version__))
		# assert os.path.exists("%s.zip" % exe_fn)

		print "\n\n"
		print "-"*70
		print "\n\tSuccessfully complied %s! (bdist_esky)\n" % fn
		print "-"*70

	if 'py2exe' in sys.argv:
		assert len(os.listdir('dist')) > 0
		
		os.chdir(r"C:\Scripts\iQuality")
		os.system('"%s" install.iss' % inno_setup_iscc_path)

		os.chdir(r"C:\Scripts\iQuality\dist-installer")
		exe_fn = [x for x in os.listdir('.') if x.endswith('.exe')]
		assert len(exe_fn) == 1
		exe_fn = exe_fn[0].split('.exe')[0]
		os.system('"%s" a -m0 -afzip %s.zip *' % (rar_path, exe_fn))
		assert os.path.exists("%s.zip" % exe_fn)

		print "\n\n"
		print "-"*55
		print "\n\tSuccessfully complied %s!\n" % exe_fn
		print "-"*55
	
if os.path.exists(os.path.join(code_dir, 'build')):
	os.system('rd /S /Q "%s"' % os.path.join(code_dir, 'build'))
	
# raw_input("\nPress any key to continue . . .")