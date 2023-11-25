FROM python:3.11.6

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apt-get update && apt-get install -y python3-opencv
RUN pip install --no-cache-dir -r requirements.txt

CMD python MeterReader.py