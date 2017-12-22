FROM ubuntu:16.04

RUN set -e -x ;\
    mkdir /code /venv ;\
    useradd -rm service ;\
    apt-get update ;\
    apt-get install -yf python-virtualenv build-essential libpq-dev libsasl2-dev python-dev libldap2-dev libssl-dev ;\
    apt-get clean ;\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ADD pip-requirements.txt /venv/pip-requirements.txt
RUN set -e -x ;\
    virtualenv /venv/venv ;\
    /venv/venv/bin/pip install -r /venv/pip-requirements.txt

ADD . /code
RUN set -e -x ;\
    chown -R service:service /code ;\
    chown -R service:service /venv

USER service
WORKDIR /code
RUN set -e -x ;\
    cp config.py.dist-docker config.py

EXPOSE 5000
ENTRYPOINT ["/venv/venv/bin/python", "run-debug.py"]
