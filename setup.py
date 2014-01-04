import os
import shutil
from glob import glob
import platform
from zipfile import ZipFile

from distutils.core import setup
from esky.bdist_esky import Executable

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
    import win32com
    import sys

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
    """
    Search in _file for regex (basic only). When found, replace in that line 'x' with 'y'.
    """
    with open(_file, 'r') as f:
        data = f.readlines()
    for i, val in enumerate(data):
        if regex in val:
            if x in val:
                print "found %s at line %d. replacing '%s' with '%s'..." % (val.strip(), i + 1, x, y)
                data[i] = val.replace(x, y)
            else:
                print "found %s, didn't found %s." % (regex, x)

            with open(_file, 'w') as f:
                f.writelines(data)


# Locate path of existing installations
if os.path.exists(r'C:\Program Files\Inno Setup 5\iscc.exe'):
    inno_setup_iscc_path = r'C:\Program Files\Inno Setup 5\iscc.exe'
else:
    inno_setup_iscc_path = r'C:\Program Files (x86)\Inno Setup 5\iscc.exe'

if os.path.exists(r'C:\Program Files\WinRAR\WinRar.exe'):
    rar_path = r'C:\Program Files\WinRAR\WinRar.exe'
else:
    rar_path = r'C:\Program Files (x86)\WinRAR\WinRar.exe'

if os.path.exists(r"C:\Program Files\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT"):
    msvcp90_dll_folder = r"C:\Program Files\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT"
elif os.path.exists(r"C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT"):
    msvcp90_dll_folder = r"C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT"
else:
    msvcp90_dll_folder = r"C:\Windows\winsxs\x86_microsoft." \
                         r"vc90.crt_1fc8b3b9a1e18e3b_9.0.30729.4137_none_508fc1d4bcbb3eca"

assert os.path.exists(inno_setup_iscc_path), "Can't find the Inno Setup on your computer"
assert os.path.exists(rar_path), "Can't find the WinRAR setup on your computer"
assert os.path.exists(msvcp90_dll_folder), "Can't find the Microsoft VC setup on your computer"

code_dir = r"C:\Scripts\iQuality"
bump_rev = True
make_installer = True
update_iss_version = True
update_iss_arch_reference = True
GUI_ONLY = True
override_app_version = "0.212"  # None for no overriding, a new version number for overriding (string)
override_app_date = '21/12/13'  # None for no overriding, a new date for overriding (string)
python_path = os.path.dirname(sys.executable)

# Sanity checks override_app_version = "0.212"
if not os.path.exists(code_dir):
    sys.exit("Error: %s doesn't exist" % code_dir)
if not os.path.exists(inno_setup_iscc_path):
    sys.exit("Error: inno_setup_iscc_path was not found")
if not os.path.exists(rar_path):
    sys.exit("Error: rar_path was not found")
if not os.path.exists(msvcp90_dll_folder):
    sys.exit("Error: msvcp90_dll_folder was not found")

os.chdir(code_dir)
sys.path.append(os.path.join(code_dir, "code"))
sys.path.append(msvcp90_dll_folder)

arch = platform.architecture()[0]
if arch == '32bit':
    __arch__ = 'win32'
elif arch == '64bit':
    # Fix the install.iss file
    __arch__ = 'win-amd64'
else:
    __arch__ = 'unknown'
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
    if make_installer and update_iss_arch_reference:
        x = [x for x in open('install.iss').readlines() if '#define BuildArch' in x]
        if not x:
            sys.exit("Didn't find BuildArch in install.iss file'")
        BuildArch = x[0].split()[2].strip('"')
        do_magic_in_file(r'install.iss', "#define BuildArch", BuildArch, __arch__)
    new_rev = rev + 1
    if bump_rev:
        do_magic_in_file(r'code\Config.py', "__rev__", str(rev), str(new_rev))

    print "Building iQuality (rev %d)..." % new_rev
    print "Setting show_ads to True"
    do_magic_in_file(r'code\Config.py', "'show_ads':", "False", "True")

    os.chdir(r'code\ts')
    os.system(r'%s\lib\site-packages\PyQt4\lrelease.exe ts.pro' % python_path)

os.chdir(code_dir)

py2exe_data_files = [
    ('phonon_backend', [r'%s\Lib\site-packages\PyQt4\plugins\phonon_backend\phonon_ds94.dll' % python_path]),
    ('imageformats', glob(r'%s\Lib\site-packages\PyQt4\plugins\imageformats\*.dll' % python_path)),
    ("pics", glob(r'code\pics\*.*')),
    ("ts", glob(r'code\ts\*.qm')),
    ("", glob('*.md') + [r'code\public.key'])
]

freeze_includes = ["mutagen.id3", "mutagen.easyid3", 'sip', 'win32api', 'lxml.etree', 'lxml._elementpath', 'gzip']
freeze_excludes = ['doctest', 'unittest', 'pdb', 'pyreadline', 'calender']

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
    name='iQuality',
    gui_only=GUI_ONLY,
    description='High Quality Songs Downloader',
    script=os.path.join(code_dir, "code", "Gui.py"),
    icon_resources=[(1, os.path.join(code_dir, "code", "pics", "iQUACK.ico"))]
)

setup(
    name="iQuality",
    version=__version__,
    description='High Quality Songs Downloader',
    author='Itay Brandes',
    author_email='brandes.itay+iquality@gmail.com',
    url='http://iquality.itayb.net/',
    data_files=py2exe_data_files,
    # windows = [{"script": os.path.join(code_dir, "code", "Gui.py"),
    # 'uac_info': "requireAdministrator",
    # "icon_resources": [(1, os.path.join(code_dir, "code", "pics", "iQUACK.ico"))],
    # "dest_base": "iQuality"},
    # ],
    scripts=[iquality_exe],
    options={"py2exe": py2exe_options, "bdist_esky": bdist_esky_options_py2exe},
    zipfile=None,
    classifiers=[
        "Topic :: Multimedia :: Video",
        "Development Status :: 4 - Beta Development",
        "Environment :: %s (MS Windows)" % __arch__,
        "License :: Free for non-commercial use",
        "Programming Language :: Python :: 2.7"
    ],
)

if 'bdist_esky' in sys.argv:
    print "Setting show_ads to False"
    do_magic_in_file(r'code\Config.py', "'show_ads':", "True", "False")

    # extract zipfile
    if __arch__ == 'amd64':
        fn = "iQuality-%s.%s" % (__version__, 'win-amd64')
    else:
        fn = "iQuality-%s.%s" % (__version__, __arch__)

    zip = ZipFile(os.path.join("dist", "%s.zip" % fn))
    zip.extractall(os.path.join("dist", fn))

    # fix to esky's proper structure
    os.makedirs(r"dist\%s\appdata" % fn)
    shutil.move(r'dist\%s\%s' % (fn, fn), r'dist\%s\appdata' % fn)

    os.makedirs(r"dist\%s\phonon_backend" % fn)
    shutil.copy(r'%s\Lib\site-packages\PyQt4\plugins\phonon_backend\phonon_ds94.dll' % python_path,
                r"dist\%s\phonon_backend" % fn)

    shutil.copytree(r'%s\Lib\site-packages\PyQt4\plugins\imageformats' % python_path,
                    r"dist\%s\imageformats" % fn)

if make_installer and not 'bdist_esky_patch' in sys.argv:
    if 'bdist_esky' in sys.argv:
        os.chdir(r"C:\Scripts\iQuality")
        os.system('"%s" install.iss' % inno_setup_iscc_path)

        os.chdir(r"C:\Scripts\iQuality\dist")
        os.system('"%s" a -m0 -afzip iQuality-%s-installer.zip iQuality-%s-installer.exe' % (
            rar_path, __version__, __version__))
        # assert os.path.exists("%s.zip" % exe_fn)

        print "\n\n"
        print "-" * 70
        print "\n\tSuccessfully complied %s! (bdist_esky)\n" % fn
        print "-" * 70

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
        print "-" * 55
        print "\n\tSuccessfully complied %s!\n" % exe_fn
        print "-" * 55

if os.path.exists(os.path.join(code_dir, 'build')):
    os.system('rd /S /Q "%s"' % os.path.join(code_dir, 'build'))

    # raw_input("\nPress any key to continue . . .")