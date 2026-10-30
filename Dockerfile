# UNTESTED: Docker was not available on the development machine. Build and fix before relying on it.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/app/src
WORKDIR /app

COPY requirements.txt requirements-dbt.txt ./
RUN pip install -r requirements.txt \
 && python -m venv /opt/dbt-venv && /opt/dbt-venv/bin/pip install -r requirements-dbt.txt

COPY src ./src
COPY sql ./sql
COPY dbt ./dbt
COPY app ./app
COPY scripts ./scripts

ENV CADW_DBT_BIN=/opt/dbt-venv/bin/dbt DBT_PROFILES_DIR=/app/dbt
# Run as an unprivileged user.
RUN useradd --create-home cadw && mkdir -p /app/data && chown -R cadw /app
USER cadw

EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0"]
