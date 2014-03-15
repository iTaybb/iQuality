# coding: utf-8
# Copyright (C) 2012 Itay Brandes

from win32com.shell import shell
import os.path

def launch_file_explorer(path, files):
	'''
	Given a absolute base path and names of its children (no path), open
	up one File Explorer window with all the child files selected
	
	Taken from http://mail.python.org/pipermail/python-win32/2012-September/012533.html
	'''
	files = [os.path.basename(f) for f in files]
	# folder_pidl = shell.SHILCreateFromPath(path,0)[0]
	folder_pidl = shell.SHGetDesktopFolder().ParseDisplayName(0,0,path)
	# folder_pidl = shell.SHParseDisplayName(path,0)[0]
	
	desktop = shell.SHGetDesktopFolder()
	shell_folder = desktop.BindToObject(folder_pidl, None,shell.IID_IShellFolder)
	name_to_item_mapping = dict([(desktop.GetDisplayNameOf(item, 0), item) for item in shell_folder])
	to_show = []
	for file in files:
		if name_to_item_mapping.has_key(file):
			to_show.append(name_to_item_mapping[file])
		# else:
			# raise Exception('File: "%s" not found in "%s"' % (file, path))
		
	shell.SHOpenFolderAndSelectItems(folder_pidl, to_show, 0)
	
launch_file_explorer('G:\\testing', [u'The Official Pokémon Website.mp3'])