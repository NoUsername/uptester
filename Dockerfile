FROM    debian:jessie

RUN apt-get update && apt-get install -y python3 \
    virtualenv \
    libyaml-dev \
    python3-pip

RUN mkdir -p /opt/uptester
COPY *.py *.txt /opt/uptester/

RUN virtualenv --python=python3 /root/.uptester && \
    . /root/.uptester/bin/activate && \
    cd /opt/uptester && \
    pip3 install -r requirements.txt

RUN printf "#!/bin/sh\ncd /opt/uptester\n. /root/.uptester/bin/activate\npython3 -u uptester.py" > /opt/uptester.sh && \
	chmod ugo+x /opt/uptester.sh

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD { test -f /opt/uptester/checks.yml || echo "no checks.yml provided!" && exit 1 } && \
	/opt/uptester.sh
