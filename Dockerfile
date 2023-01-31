FROM python:3.9
WORKDIR /app

RUN apt-get update
RUN apt install zip

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "server.py"]