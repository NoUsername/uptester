#!/bin/env python
import subprocess
from threading import Thread, Timer
import traceback
import copy
import time
import six
from datetime import timedelta
from queue import Queue
from commons import *

class KeepAlivePing:
	"""
	processes incoming "pings" and matches them against configured timeout intervals.
	one "ping" is expected per time interval, if that doesn't happen the "onFail" is triggered.

	useful to monitor recurring external events which "ping" this monitoring server when they are done.
	this way you will notice if some event did not happen in the expected period.
	"""

	def __init__(self, config, state, persistenceCallback, statusCallback):
		self.state = copy.deepcopy(state)
		self.persistenceCallback = persistenceCallback
		self.queue = Queue()
		self.statusCallback = statusCallback
		self.configByToken = dict()
		for k, v in six.iteritems(config):
			data = copy.deepcopy(v)
			data['name'] = k
			token = v.get(K_TOKEN)
			if token in self.configByToken:
				raise Exception("token '%s' used multiple times, must be unique!"%token)
			self.configByToken[token] = data
			if k not in self.state:
				nextOpenInterval = time.time()
				self.state[k] = dict(lastPing=0, nextOpenInterval=nextOpenInterval, fails=0, alerted=False)
		self.worker = Thread(target=self.worker)
		self.worker.daemon = True
		self.worker.start()
		self.onTimer()
	
	def onToken(self, token):
		self.queue.put(dict(token=token))

	def onTimer(self):
		Timer(60, self.onTimer).start()
		self.queue.put(dict(timer=True))

	def onFail(self, conf, state):
		state[K_FAILS] = state[K_FAILS] + 1

	def checkExpiredSingle(self, conf):
		now = time.time()
		name = conf.get('name')
		state = self.state.get(name)
		lastPing = state.get('lastPing')
		interval = conf.get(K_INTERVAL, 1)
		intervalLength = timedelta(minutes=interval).total_seconds()
		nextOpenInterval = state.get('nextOpenInterval')
		if now > nextOpenInterval + intervalLength:
			print("keepAlive for '%s' failed"%name)
			# current interval was missed
			runFailCommand(conf, state)
			state['nextOpenInterval'] = nextOpenInterval + intervalLength * int((now - nextOpenInterval) / intervalLength)

	def checkExpired(self):
		for token, conf in six.iteritems(self.configByToken):
			self.checkExpiredSingle(conf)
		self.persistenceCallback(self.state)
		self.publishStateUpdate()

	def publishStateUpdate(self):
		currentStateResult = dict()
		for token, conf in six.iteritems(self.configByToken):
			name = conf.get('name')
			state = self.state.get(name)
			currentStateResult[name] = buildStateResult(state.get(K_FAILS))
		self.statusCallback(currentStateResult)

	def updateInterval(self, conf):
		self.checkExpiredSingle(conf)
		name = conf.get('name')
		state = self.state.get(name)
		interval = conf.get(K_INTERVAL, 1)
		nextOpenInterval = state.get('nextOpenInterval')
		intervalLength = timedelta(minutes=interval).total_seconds()
		now = time.time()
		if now > nextOpenInterval and now < nextOpenInterval + intervalLength:
			# interval has started and has now succeeded
			state['nextOpenInterval'] = nextOpenInterval + intervalLength
			print("keepAlive for '%s' succeeded"%name)
			runRecovered(conf, name, state)
			self.publishStateUpdate()
		else:
			print('token "%s" ignored, %s'%(conf.get(K_TOKEN), 'openInterval not started' if nextOpenInterval > now else 'ERROR: openInterval already passed!'))
		state['lastPing'] = now
		# it's safe to call save every time because save internally throttles IO operations
		self.persistenceCallback(self.state)

	def worker(self):
		"""
		checks if any timers have expired and errors need to be triggered
		"""
		print("keepAlive worker started")
		while True:
			event = self.queue.get()
			try:
				if K_TOKEN in event:
					token = event.get(K_TOKEN)
					conf = self.configByToken.get(token, None)
					if conf is not None:
						self.updateInterval(conf)
				elif 'timer' in event:
					print("keepAliveTimer")
					self.checkExpired()
			except:
				print("error in worker\n%s"%traceback.format_exc())
			self.queue.task_done()
