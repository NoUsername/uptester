#!/bin/env python
import flask
import yaml
import requests
import subprocess
import threading
import traceback
import json

def readChecks():
	result = dict()
	with open("checks.yml", "r") as f:
		result = yaml.load(f)
	for k, v in result.iteritems():
		if not isinstance(v, dict):
			raise Exception("value of '%s' is not a dictionary"%k)
		if not v.has_key('interval'):
			raise Exception("'%s' is missing an interval value")
		if not v.has_key('url'):
			raise Exception("'%s' is missing an url value")
		if not v.has_key('onFail'):
			raise Exception("'%s' is missing an onFail command")
	return result

def runCmd(cmd):
	subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

def runFailCommand(check):
	fails = check.get('fails', 0) + 1
	check['fails'] = fails
	minFails = check.get('minFails', 1)
	if fails < minFails:
		print("%s more fails before triggering"%(minFails - fails))
		return
	onFailCmd = check.get('onFail')
	onNegativeCmd = check.get('onNegative', None)
	if fails == minFails:
		print("running onFail command:\n%s"%(onFailCmd))
		# run command in background
		runCmd(onFailCmd)
	elif onNegativeCmd is not None:
		runCmd(onNegativeCmd)

def runCheck(check, name=''):
	minFails = check.get('minFails', 1)
	try:
		res = requests.get(check.get('url'))
		expectStatus = [200]
		if check.has_key('expectStatus'):
			expectStatus = check.get('expectStatus')
		if not res.status_code in expectStatus:
			runFailCommand(check)
			return False
		if check.has_key('expectText'):
			if res.text.find(check.get('expectText')) == -1:
				runFailCommand(check)
				return False
		fails = check.get('fails', 0)
		if fails > minFails and check.has_key('onRecover'):
			print("'%s' recovered"%name)
			runCmd(check.get('onRecover'))
		check['fails'] = 0
		return True
	except:
		print("exception during check")
		traceback.print_exc()
		runFailCommand(check)
	return False

def startChecker(statusCallback):
	checks = readChecks()
	__timer(checks, 0, statusCallback)

def __timer(checks, count, statusCallback):
	# call __timer() again in 60 seconds
	threading.Timer(60, __timer, [checks, count + 1, statusCallback]).start()
	print("timer callback")
	status = dict()
	for k, v in checks.iteritems():
		if count % v.get('interval') == 0:
			print("running check '%s'"%k)
			ok = runCheck(v, k)
			status[k] = dict(success=ok, fails=v.get('fails'))
			print("check %s"%('OK' if ok else 'FAILED'))
	statusCallback(status)

# web part
app = flask.Flask(__name__)

def __textResponse(data):
	return (data, 200, {'Content-Type': 'text/plain; charset=utf-8'})

def __jsonResponse(data):
	return (data, 200, {'Content-Type': 'application/json'})

COUNTER='counter'
STATUS='status'

@app.route("/")
@app.route("/ping")
def ping():
	cfg = flask.current_app.config
	cfg[COUNTER] = cfg[COUNTER] + 1
	return __textResponse("OK")

# show ping count
@app.route("/pingStatus")
def pong():
	cfg = flask.current_app.config
	return __textResponse("ping called %s times"%cfg[COUNTER])

# show status from statusChecker
@app.route("/status")
def status():
	cfg = flask.current_app.config
	return __jsonResponse(json.dumps(cfg[STATUS]))

if __name__=='__main__':
	print("starting checker")
	def statusCallback(data):
		app.config[STATUS] = data
	startChecker(statusCallback)
	app.config[COUNTER] = 0
	print("starting web")
	app.run(host="0.0.0.0", port=7676)