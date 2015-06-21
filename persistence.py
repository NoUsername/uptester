#!/bin/env python
"""
Reads the status of the checks from a file and
writes it back to the file asynchronously.

Used to keep state across restarts of uptester.
"""
from threading import Thread, Timer
from datetime import timedelta
from six.moves.queue import Queue
import yaml
import traceback
import copy
import time


STATE_FILE = 'state.yml'
MIN_SAVE_INTERVAL_SEC = 10

def worker(workQueue, initialState):
	print("Persistence worker queue started")
	state = copy.deepcopy(initialState)
	lastSaved = 0
	dirty = False
	while True:
		data = workQueue.get()
		if 'checks' in data:
			state['checks'] = data.get('checks')
			dirty = True
		if 'pings' in data:
			state['pings'] = data.get('pings')
			dirty = True
		now = time.time()
		td = timedelta(seconds=now - lastSaved)
		if dirty:
			if td.total_seconds() > MIN_SAVE_INTERVAL_SEC:
				print("saving state")
				try:
					f = open(STATE_FILE, 'w')
					f.write(yaml.dump(state, default_flow_style=False))
					f.close()
					lastSaved = now
					dirty = False
				except:
					print("error writing state:\n%s"%traceback.format_exc())
			else:
				# saving postponed (too many saves in short time)
				pass
		workQueue.task_done()

def readState():
	try:
		with open(STATE_FILE, 'r') as f:
			state = yaml.load(f)
			state['checks'] = state.get('checks', dict())
			state['pings'] = state.get('pings', dict())
			return state
	except:
		print("could not read state file")
		return dict(checks=dict(), pings=dict())

def triggerSaveTimer(queue):
	Timer(MIN_SAVE_INTERVAL_SEC, triggerSaveTimer, [queue]).start()
	queue.put(dict(saveTrigger=None))


class Persistence:
	workQueue = Queue()
	initialState = readState()
	workerThread = Thread(target=worker, args=[workQueue, initialState])
	workerThread.daemon = True
	workerThread.start()
	triggerSaveTimer(workQueue)

	def getInitialChecksState(self):
		return Persistence.initialState.get('checks')

	def getInitialPingsState(self):
		return Persistence.initialState.get('pings')

	def persistChecks(self, data):
		"""saves the data asynchronously"""
		Persistence.workQueue.put(dict(checks=data))

	def persistPings(self, data):
		"""saves the data asynchronously"""
		Persistence.workQueue.put(dict(pings=data))


