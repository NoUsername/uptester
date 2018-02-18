FROM python:3.6-alpine3.7

RUN mkdir -p /opt/uptester

WORKDIR /opt/uptester

COPY *.py *.txt ./

RUN pip install -r requirements.txt

RUN printf '#!/bin/sh\ntest -f /opt/uptester/checks.yml || ( printf "no checks.yml provided!\\n" && exit 1 )\ncd /opt/uptester\npython -u uptester.py' > /opt/uptester.sh && \
	chmod ugo+x /opt/uptester.sh

CMD /opt/uptester.sh

EXPOSE 7676
