FROM python:3.12-trixie

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update
RUN apt-get install -y nodejs npm
 
COPY . .

WORKDIR /usr/src/app/spa
RUN npm install
RUN npm run build

WORKDIR /usr/src/app

EXPOSE 8000

CMD [ "fastapi", "run", "main.py" ]

