FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 matchday
COPY --chown=matchday:matchday . .
RUN mkdir -p /app/data && chown matchday:matchday /app/data
USER matchday
ENV HOST=0.0.0.0 PORT=5000 ATS_DB=/app/data/ats.sqlite3
EXPOSE 5000
CMD ["python", "server.py"]
