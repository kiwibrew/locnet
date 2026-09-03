FROM node:24-trixie AS spa-build

WORKDIR /usr/src/app/spa

COPY spa/package.json spa/package-lock.json spa/.npmrc ./
RUN npm ci

COPY spa/ ./
RUN npm run build

FROM python:3.14-slim AS python-base

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=spa-build /usr/src/app/spa/dist ./spa/dist

RUN chmod 0444 /usr/src/app/app/data/app.db \
    && chmod +x /usr/src/app/docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=3s --start-period=10s --retries=12 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

ENTRYPOINT ["/usr/src/app/docker-entrypoint.sh"]

FROM python-base AS test

COPY requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt

CMD ["pytest"]

FROM python-base AS production

CMD ["fastapi", "run", "app/main.py"]
