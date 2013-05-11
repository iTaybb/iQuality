# Copyright (C) 2012-2013 Itay Brandes

'''
Useful decorators for general useage.
'''

from functools import wraps
import threading
import time
import traceback
import socket

__all__ = ['count_runtime', 'retry', 'memoize', 'log_exceptions']

def count_runtime(f):
	"Decorator for counting runtime."
	@wraps(f)
	def timed(*args, **kw):
		t1 = time.time()
		result = f(*args, **kw)
		t2 = time.time()
		
		print '%s: %2.2f sec' % (f.__name__, t2-t1)
		#print '%r (%r, %r) %2.2f sec' % (f.__name__, args, kw, t2-t1)
		return result
	
	return timed
	
def log_exceptions(e, logger):
	"Decorator that logs any exceptions."
	def deco_log(f):
		@wraps(f)
		def f_log(*args, **kwargs):
			try:
				return f(*args, **kwargs)
			except socket.timeout:
				logger.debug('timeout: function %s timed out.' % f.__name__)
			except:
				logger.error(traceback.format_exc())
		return f_log  # true decorator
	return deco_log
	
def retry(ExceptionToCheck, tries=2, delay=2, backoff=1, logger=None):
	'''Retry calling the decorated function using an exponential backoff.

	http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
	original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
	'''
	def deco_retry(f):
		@wraps(f)
		def f_retry(*args, **kwargs):
			mtries, mdelay = tries, delay
			try_one_last_time = True
			while mtries > 1:
				try:
					return f(*args, **kwargs)
					try_one_last_time = False
					break
				except ExceptionToCheck, e:
					msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
					if logger:
						logger.warning(msg)
					else:
						print msg
					time.sleep(mdelay)
					mtries -= 1
					mdelay *= backoff
			if try_one_last_time:
				return f(*args, **kwargs)
			return
		return f_retry  # true decorator
	return deco_retry
	
class memoize(object):
	'''
	Thread-safe memoize decorator with timeout.
	Based on: http://code.activestate.com/recipes/325905-memoize-decorator-with-timeout/
	'''
	_caches = {}
	_timeouts = {}

	def __init__(self, timeout=60, threadsafe=True):
		self.timeout = timeout
		self.threadsafe = threadsafe
		
	def collect(self):
		"""Clear cache of results which have timed out"""
		for func in self._caches:
			cache = {}
			for key in self._caches[func]:
				if (time.time() - self._caches[func][key][1]) < self._timeouts[func]:
					cache[key] = self._caches[func][key]
			self._caches[func] = cache

	def __call__(self, f):
		self.cache = self._caches[f] = {}
		self._timeouts[f] = self.timeout
		
		@wraps(f)
		def func(*args, **kwargs):
			if self.threadsafe:
				lock = threading.Lock()
			kw = kwargs.items()
			kw.sort()
			key = (args, tuple(kw))
			try:
				v = self.cache[key]
				# print "cache"
				if (time.time() - v[1]) > self.timeout:
					raise KeyError
			except KeyError:
				# print "new"
				if self.threadsafe:
					result = f(*args, **kwargs)
					with lock:
						v = self.cache[key] = result,time.time()
				else:
					v = self.cache[key] = f(*args, **kwargs),time.time()
			return v[0]
		func.func_name = f.func_name
		
		return func