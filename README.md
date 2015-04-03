# uptester

## requirements

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

## configuration

See the `example-checks.yml` file for documentation about the config structure.

## http endpoints

	# ping (check if running)
    http://localhost:7676/
    http://localhost:7676/ping

    # check how often ping endpoint was called
    http://localhost:7676/pingStatus

    # status of all configured checks
	http://localhost:7676/status    

## graphite reporting

uptester supports reporting the up-info to graphite. By default this is disabled, to enable this just put the following into your `checks.yml`

	# the host and port fields are optional, defaults are 127.0.0.1 and 2003
	__graphite:
	  - enabled: True
	  - host: myGraphiteHost
	  - port: 1234

Graphite can be used to easily calculate uptime-percentages from the checks ran by uptester. Uptester reports a value of `0` to graphite if the service is unavailable or `100` if it is available. Generating a rolling average in graphite gives you a nice uptime-percentage for any desired timeframe.

Example:

![Graphite example graph](https://i.imgur.com/wSEwZK3.png)
