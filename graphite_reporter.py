#!/bin/env python
import socket
import time
import re
from commons import *

def sanitize(text):
	return re.sub('[^0-9a-zA-Z]+', '_', text)

class GraphiteReporter:

	def __init__(self, host='127.0.0.1', port=2003):
		"""initialize reporter with graphite carbon connection information"""
		self.host = host
		self.port = port

	def report(self, dataDict):
		print("graphite reporter reporting")
		lines = []
		now = int(time.time())
		for k, v in dataDict.iteritems():
			ok = v.get(K_SUCCESS)
			# send "ok" value as percentage (100 as in "100% uptime")
			lines.append("uptester.%s %s %d"%(sanitize(k), 100 if ok else 0, now))
		message = '\n'.join(lines) + '\n' #all lines must end in a newline
		# send message, reconnect every time for simplest possible error-recovery
		try:
			sock = socket.socket()
			sock.connect((self.host, self.port))
			sock.sendall(message)
			sock.close()
		except socket.error:
			print("Couldn't connect to %s on port %s, is carbon-cache.py running?"%(self.host, self.port))

