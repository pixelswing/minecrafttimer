FROM python:3.13-alpine
WORKDIR /app
COPY server.py /app/server.py
RUN addgroup -S timer && adduser -S -G timer timer && mkdir /data && chown timer:timer /data
USER timer
EXPOSE 8787
CMD ["python3", "/app/server.py"]
