# uptester

`uptester` is a small Python program which can do very similar things (functionally, without the fancy UI) as the popular services [pingdom](https://www.pingdom.com/) and [DeadMan'sSnitch](https://deadmanssnitch.com/).

So there are two parts:
* "ping" (HTTP request) external services periodically to check if they are up.
* wait for incoming "pings" (HTTP request) from external sources in periodic intervals.

For both you can configure the interval (minute granularity) in which these things should happen.
* For outgoing pings this means that every X minutes a request will be sent to that url and the result checked.
* For incoming pings this means that at least every X minutes an incoming request is expected. If it does not happen for that time it is considered an error.

Incoming requests are identified by a user-definable token (see example config) and can happen via HTTP POST (form param or json) or HTTP GET as part of the URL.
It does not matter if the incoming request happens more often than the configured interval, but if it happens rarely than that an error is triggered.

uptester is a very small utility which gets powerful by allowing you to hook custom commands into all exposed events. This means you can trigger any shell-command in any of the following events:
* `onFail` A check fails (was good before, failed for the first time).
* `onNegative` A check fails again (not triggered the first time where `onFail` triggers).
* `onRecover` A check that has been failing before returned back to normal.

Examples of what you can do via these hooks and custom commands:

* Trigger a [Pushbullet](https://www.pushbullet.com/) notification via curl (or any other HTTP enabled service).
* Send an email via the mail command.
* Trigger LEDs on some hardware device like RaspberryPi via some script.
* ...

## Requirements

If you want to run via docker you only need docker (skip to Docker sub-heading).

* python (tested with 2.7, should work with 3 as well)
* virtualenv and virtualenvwrapper (not required but makes it easier to run)

Get it up and running with virtualenv:

	sudo apt-get install virtualenvwrapper
	# create and activate virtualenv
	mkvirtualenv --no-site-packages uptester
	workon uptester
	pip install -r requirements.txt

	# get your config (here we simply use the example (won't do that much))
	cp example-checks.yml checks.yml

	# to actually run it:
	python uptester.py

Additional notes:

	# subsequent runs should be done like this:
	workon uptester
	python uptester.py

	# if you want to start it from a shellscript (e.g. init script) you probably need this to activate the virtualenv
	/home/yourUser/.virtualenvs/uptester/bin/python uptester.py

### Running via docker:

Place your configuration (see next part) in /etc/uptester.yml and run via:

	sudo docker build .
	# get hash, e.g. 1f50ffd73437
	# make sure you have a config file and a state.yml file (state.yml can be an empty file if you are starting out)
	sudo docker run -v /etc/uptester.yml:/opt/uptester/checks.yml -v /var/uptester-state.yml:/opt/uptester/state.yml -p 7676:7676 1f50ffd73437 /opt/uptester.sh

## Configuration

See the `example-checks.yml` file for documentation about the config structure.

## HTTP endpoints

	# ping (check if running)
    http://localhost:7676/
    http://localhost:7676/ping

    # check how often ping endpoint was called
    http://localhost:7676/pingStatus

    # status of all configured checks
	http://localhost:7676/status    

	# INCOMING:
	http://localhost:7676/alive/myToken
	# HTTP POST:
	http://localhost:7676/alive data `token=myToken`
	http://localhost:7676/alive data `{"token":"myToken"}`

# State

The internal state of uptester is kept across restarts of the program via the `state.yml` file. If you want to reset the state simply delete this file.
NOTE: The file is not written immediately after each change (to reduce disk IO) so you might loose the last few seconds of events in the worst case if you stop the uptester process.

## Graphite reporting

uptester supports reporting the up-info to graphite. By default this is disabled, to enable this just put the following into your `checks.yml`

	# the host and port fields are optional, defaults are 127.0.0.1 and 2003
	__graphite:
	  - enabled: True
	  - host: myGraphiteHost
	  - port: 1234

Graphite can be used to easily calculate uptime-percentages from the checks ran by uptester. Uptester reports a value of `0` to graphite if the service is unavailable or `100` if it is available. Generating a rolling average in graphite gives you a nice uptime-percentage for any desired timeframe.

Example:

![Graphite example graph](https://i.imgur.com/wSEwZK3.png)
