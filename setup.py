from distutils.core import setup
import py2exe
import sys
import os
import shutil
from glob import glob
import pdb

def do_magic_in_file(_file, regex, x, y):
	'''
	Search in _file for regex (basic only). When found, replace in that line 'x' with 'y'.
	'''
	with open(_file, 'r') as f:
		data = f.readlines()
	for i,val in enumerate(data):
		if regex in val:
			print "found %s at line %d. replacing '%s' with '%s'..." % (val.strip(), i, x, y)
			data[i] = val.replace(x, y)
			
			with open(_file, 'w') as f:
				f.writelines(data)

inno_setup_iscc_path = r'C:\Program Files\Inno Setup 5\iscc.exe'
rar_path = r'C:\Program Files\WinRAR\WinRar.exe'

# Script must be at C:\Scripts\iQuality
os.chdir(r"C:\Scripts\iQuality")
sys.path.append(r"C:\Scripts\iQuality\DLLs")
sys.path.append(r"C:\Scripts\iQuality\code")
# sys.argv.append('py2exe')

rev = __import__('Config').__rev__
new_rev = rev+1
do_magic_in_file(r'code\Config.py', "__rev__", str(rev), str(new_rev))

print "Building iQuality (rev %d)..." % new_rev
print "Setting show_ads to True"
do_magic_in_file(r'code\Config.py', "'show_ads':", "False", "True")

if os.path.exists('build'):
	os.system('rd /S /Q build')
if os.path.exists('dist'):
	os.system('rd /S /Q dist')
	
'''
win32com.shell workaround START
taken from: http://www.py2exe.org/index.cgi/win32com.shell
'''
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
	
'''
win32com.shell workaround END
'''

setup(
	data_files = [
					('phonon_backend', [r'C:\Python27\Lib\site-packages\PyQt4\plugins\phonon_backend\phonon_ds94.dll']),
					('imageformats', glob(r'C:\Python27\Lib\site-packages\PyQt4\plugins\imageformats\*.dll')),
					("pics", glob(r'code\pics\*.*')),
					("ts", glob(r'code\ts\*.qm')),
					("", glob(r'*.txt')+[r'code\public.key'])
					],
	windows = [{"script": r"code\Gui.py", 
				"icon_resources": [(1, r'code\pics\iQUACK.ico')],
				"dest_base": "iQuality"},
				],
	options = {"py2exe":{
						"includes": ["mutagen.id3", "mutagen.easyid3", 'sip', 'win32api', 'lxml.etree', 'lxml._elementpath', 'gzip'], 
						'excludes': ['doctest', 'pdb', 'unittest', '_ssl',
						'pyreadline', 'locale', 'optparse', 'calender'],
						'compressed': 'True',
						"optimize": 2,
						'bundle_files': 3,
						'dll_excludes': ['w9xpopen.exe']
						}},
	zipfile = None,
	)

print "Setting show_ads to False"
do_magic_in_file(r'code\Config.py', "'show_ads':", "True", "False")

# sys.exit()
	
os.system('rd /S /Q build')
assert len(os.listdir('dist')) > 0
os.system('ren dist build')
print "Deleting metadata, logs, batches, python bytecode files..."
os.chdir(r"C:\Scripts\iQuality\build")
os.system('del /F /S /Q *distro.txt')
os.system('del /F /S /Q stats.txt')
os.system('del /F /S /Q todo.txt')
os.chdir(r"C:\Scripts\iQuality")
os.system('"%s" install.iss' % inno_setup_iscc_path)

os.chdir(r"C:\Scripts\iQuality\dist")
exe_fn = [x for x in os.listdir('.') if x.endswith('.exe')]
assert len(exe_fn) == 1
exe_fn = exe_fn[0].split('.exe')[0]
os.system('"%s" a -m0 -afzip %s.zip *' % (rar_path, exe_fn))
assert os.path.exists("%s.zip" % exe_fn)

print "\n\n"
print "-"*55
print "\n\tSuccessfully complied %s!\n" % exe_fn
print "-"*55
raw_input("\nPress any key to continue . . .")