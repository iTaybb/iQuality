import os.path
import re
import time

import utils
from logger import log
import Config; config = Config.config

def FFMpeg(input, output, bitrate, bin_path=os.path.join(config.ext_bin_path, 'ffmpeg.exe'), fmt='mp3'):
	# Yields filesize_counter
	cmd = r'%s -y -i "%s" -vn -ac 2 -b:a %s -f %s "%s"' % (bin_path, input, str(bitrate), fmt, output)
	log.debug("Running '%s'" % cmd)
	proc = utils.launch_without_console(cmd)
	
	yield 0
	old_encoded_fs_counter = 0
	while True:
		out = proc.stderr.read(54)
		if not out:
			break
		# size=    2930kB time=00:03:07.49 bitrate= 128.0kbits/s
		if 'size=' in out and 'time=' in out:
			encoded_fs_counter = out.split('size=')[1].split('kB')[0].strip()
			if encoded_fs_counter.isdigit():
				encoded_fs_counter = int(encoded_fs_counter)
				if encoded_fs_counter > old_encoded_fs_counter:
					old_encoded_fs_counter = encoded_fs_counter
					yield encoded_fs_counter
		time.sleep(0.1)
	proc.wait()
	
def SoX(input, output, bin_path=os.path.join(config.ext_bin_path, 'sox.exe')):
	# Yields progress
	
	_real_input = input
	_real_output = output
	
	if not input.endswith('.mp3'):
		t_path = "%s.tmp.mp3" % input
		if os.path.exists(t_path):
			os.unlink(t_path)
		os.rename(input, t_path)
		input = t_path
		
	if not output.endswith('.mp3'):
		t_path = "%s.dtmp.mp3" % output
		if os.path.exists(t_path):
			os.unlink(t_path)
		output = t_path
			
	cmd = r'%s -S "%s" "%s" silence 1 0.1 1%% reverse silence 1 0.1 1%% reverse' % (bin_path, input, output)
	log.debug("Running '%s'" % cmd)
	proc = utils.launch_without_console(cmd)
	
	yield 0
	samples = 1
	in_value = 0
	out_value = 0
	while True:
		# print out
		out = proc.stderr.readline()
		if not out:
			break
		
		# Duration       : 00:04:24.06 = 11644870 samples = 19804.2 CDDA sectors
		# from PyQt4 import QtCore; import pdb; QtCore.pyqtRemoveInputHook(); pdb.set_trace()
		match = re.search(r"samples [=~] ([\d.]+) CDDA", out)
		if match:
			samples = float(match.group(1))
			break
			
	while True:
		# print out
		out = proc.stderr.read(70)
		if not out:
			break
		
		# In:100%  00:04:23.96 [00:00:00.09] Out:11.6M [      |      ] Hd:0.0 Clip:400
		if 'In:' in out:
			t = out.split('In:')[1].split('.')[0].strip()
			if t.isdigit() and int(t) > in_value:
				in_value = int(t)
		
		# In:100%  00:04:23.96 [00:00:00.09] Out:11.6M [      |      ] Hd:0.0 Clip:400
		if 'Out:' in out:
			t = out.split('Out:')[1].split(' ')[0].strip()
			try:
				if 'k' in t:
					out_value = t.split('k')[0]
					out_value = float(out_value)*1000
				elif 'M' in t:
					out_value = t.split('M')[0]
					out_value = float(out_value)*1000000
			except:
				pass
		
		# print "@@@%f@@@" % out_value
		progress = in_value*0.3+(out_value/samples*100)*0.7+1
		# print "samples: %s, progress: %s, out: %s" % (samples, progress, out.strip('\r'))
		if 0 >= progress >= 100:
			yield progress
		elif in_value>1:
			yield in_value*0.3
		
		time.sleep(0.1)
	proc.wait()
	
	if _real_output != output:
		if os.path.exists(_real_output):
			os.unlink(_real_output)
		os.rename(output, _real_output)