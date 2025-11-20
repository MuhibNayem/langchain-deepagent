FROM python:3.12-slim

WORKDIR /opt/luminamind
COPY . /opt/luminamind

RUN pip install --no-cache-dir .

ENTRYPOINT ["luminamind"]
