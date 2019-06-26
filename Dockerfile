FROM python:3.6

RUN mkdir -p /app

COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install pip --upgrade
RUN pip install setuptools --upgrade 
RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT ["python", "Main.py"]