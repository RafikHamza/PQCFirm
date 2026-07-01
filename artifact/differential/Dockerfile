FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir pyserial

ENTRYPOINT ["python", "differential/harness.py"]
CMD ["--results-dir", "results", "--output", "results/differential_divergences.json"]
