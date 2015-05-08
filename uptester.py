#!/bin/env python
from threading import Timer
from persistence import Persistence
from keep_alive_ping import KeepAlivePing
from commons import *
import flask
import yaml
import requests
import traceback
import json
import copy
import six

reporter = None

stateStore = Persistence()
keepAlivePing = None

def readConfig():
	checks = dict()
	pings = dict()
	config = dict()
	with open('checks.yml', 'r') as f:
		config = yaml.load(f)
	meta = dict()
	for k, v in six.iteritems(config):
		if not isinstance(v, dict):
			raise Exception('value of "%s" is not a dictionary'%k)
		if k.startswith('__'):
			meta[k] = v
		else:
			if 'url' not in v and 'token' not in v:
				raise Exception('"%s" is missing an url or token value')
			if 'onFail' not in v:
				raise Exception('"%s" is missing an onFail command')
			if 'url' in v:
				checks[k] = v
			else:
				pings[k] = v

	if K_GRAPHITE in meta:
		graphConf = meta[K_GRAPHITE]
		if graphConf['enabled']:
			global reporter
			from graphite_reporter import GraphiteReporter
			reporter = GraphiteReporter(graphConf.get('host', '127.0.0.1'), graphConf.get('port', 2003))

	return (checks, pings)

def runCheck(check, name, state):
	try:
		res = requests.get(check.get('url'))
		expectStatus = [200]
		if 'expectStatus' in check:
			expectStatus = check.get('expectStatus')
		if not res.status_code in expectStatus:
			runFailCommand(check, state)
			return False
		if 'expectText' in check:
			if res.text.find(check.get('expectText')) == -1:
				runFailCommand(check, state)
				return False
		runRecovered(check, name, state)
		return True
	except:
		print('exception during check')
		traceback.print_exc()
		runFailCommand(check, state)
	return False

def startChecker(checks, statusCallback):
	states = stateStore.getInitialChecksState()
	for k in checks:
		if k not in states:
			states[k] = {K_FAILS: 0, K_ALERTED: False}
	__timer(checks, states, 0, statusCallback)

def __timer(checks, states, count, statusCallback):
	# call __timer() again in 60 seconds
	Timer(60, __timer, [checks, states, count + 1, statusCallback]).start()
	print('timer callback')
	statusResult = dict()
	for k, v in six.iteritems(checks):
		state = states.get(k)
		if count % v.get(K_INTERVAL, 1) == 0:
			print('running check "%s"'%k)
			ok = runCheck(v, k, state)
			print('check %s'%('OK' if ok else 'FAILED'))
		fails = state.get(K_FAILS)
		statusResult[k] = buildStateResult(fails)
	stateStore.persistChecks(states)
	statusCallback(statusResult)

# web part
app = flask.Flask(__name__)

def __textResponse(data):
	return (data, 200, {'Content-Type': 'text/plain; charset=utf-8'})

def __jsonResponse(data):
	return (data, 200, {'Content-Type': 'application/json'})

COUNTER='counter'
STATUS='status'

@app.route('/')
@app.route('/ping')
def ping():
	cfg = flask.current_app.config
	cfg[COUNTER] = cfg[COUNTER] + 1
	return __textResponse('OK')

# show ping count
@app.route('/pingStatus')
def pong():
	cfg = flask.current_app.config
	return __textResponse('ping called %s times'%cfg[COUNTER])

# show status from statusChecker
@app.route('/status')
def status():
	cfg = flask.current_app.config
	return __jsonResponse(json.dumps(cfg[STATUS]))

@app.route('/alive', defaults=dict(token=None), methods=['POST'])
@app.route('/alive/<token>', methods=['GET', 'POST'])
def pingIn(token):
	if token is None:
		token = flask.request.form.get('token', None)
	if token is None:
		try:
			jsonData = json.loads(flask.request.data)
			token = jsonData.get('token', None)
		except:
			pass

	if token is not None:
		keepAlivePing.onToken(token)
		return __textResponse("OK\ntoken %s"%token)
	return __textResponse("ERROR\nno token provided")


if __name__=='__main__':
	app.config[STATUS] = dict()
	def statusCallback(data):
		data = copy.deepcopy(data)
		app.config[STATUS].update(data)
		if reporter is not None:
			reporter.report(data)

	checkerStartDelay = 1
	print('checker starts in %s sec' % checkerStartDelay)
	(checks, pings) = readConfig()
	Timer(checkerStartDelay, startChecker, [checks, statusCallback]).start()
	keepAlivePing = KeepAlivePing(pings, stateStore.getInitialPingsState(), stateStore.persistPings, statusCallback)
	app.config[COUNTER] = 0
	print('starting web')
	app.run(host='0.0.0.0', port=7676)