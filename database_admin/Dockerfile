FROM python:3.14-slim

RUN pip install --no-cache-dir sqlite-web==0.6.4

COPY locnet_sqlite_web.py /opt/locnet/locnet_sqlite_web.py
COPY templates /opt/locnet/templates

ENTRYPOINT ["python", "/opt/locnet/locnet_sqlite_web.py"]
