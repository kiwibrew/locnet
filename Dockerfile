FROM node:24-trixie AS spa-build

WORKDIR /usr/src/app/spa

COPY spa/package.json spa/package-lock.json spa/.npmrc ./
RUN npm ci

COPY spa/ ./
RUN npm run build

FROM python:3.12-trixie

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=spa-build /usr/src/app/spa/dist ./spa/dist

EXPOSE 8000

CMD [ "fastapi", "run", "main.py" ]
