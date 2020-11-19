FROM python:3

WORKDIR /usr/src/app

RUN pip install discord

COPY . .

CMD [ "python", "./dorian.py" ]