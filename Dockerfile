FROM python:3-slim

WORKDIR /usr/src/app

RUN pip install discord

RUN mkdir data

COPY . .

CMD [ "python", "./dorian.py" ]