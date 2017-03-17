FROM python:3.5

RUN mkdir -p /app

COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT ["python", "Main.py"]