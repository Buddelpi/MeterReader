FROM python:3.11.6-slim-bookworm

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apt-get update && apt-get install -y python3-opencv
RUN apt-get install -y git-all
RUN pip install --no-cache-dir -r requirements.txt

CMD git clone https://github.com/Buddelpi/MeterReader.git . 2> /dev/null || (git -C . pull); python MeterReader.py