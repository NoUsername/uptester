#!/bin/env python

import subprocess

# key for number of detected fails
K_FAILS = 'fails'
# key for bool if "onFail" was triggered
K_ALERTED = 'alerted'
# key for interval in minutes
K_INTERVAL = 'interval'
# key for incoming ping token
K_TOKEN = 'token'
# key for api result success state
K_SUCCESS = 'success'
# special key in the checks.yml config file which configures graphite
K_GRAPHITE = '__graphite'

def runCmd(cmd):
	subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

def runFailCommand(check, state):
	fails = state.get(K_FAILS) + 1
	state[K_FAILS] = fails
	minFails = check.get('minFails', 1)
	alerted = state.get(K_ALERTED, False)
	if fails < minFails:
		print('%s more fails before triggering'%(minFails - fails))
		return
	onFailCmd = check.get('onFail')
	onNegativeCmd = check.get('onNegative', None)
	if not alerted and fails >= minFails:
		print('running onFail command:\n%s'%(onFailCmd))
		# run command in background
		runCmd(onFailCmd)
		state[K_ALERTED] = True
	elif onNegativeCmd is not None:
		runCmd(onNegativeCmd)

def runRecovered(check, name, state):
	minFails = check.get('minFails', 1)
	fails = state.get(K_FAILS, 0)
	if fails >= minFails and 'onRecover' in check:
		print('"%s" recovered'%name)
		runCmd(check.get('onRecover'))
	state[K_FAILS] = 0
	state[K_ALERTED] = False

def buildStateResult(fails):
	"""
	builds the result object which is returned by the json api for each check
	"""
	return {K_SUCCESS: fails == 0, K_FAILS : fails}