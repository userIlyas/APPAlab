FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
ARG SERVICE_PACKAGE
ARG APPA_TAINT_INSTALL=0
COPY services/common ./services/common
COPY services/${SERVICE_PACKAGE} ./services/${SERVICE_PACKAGE}
COPY configs ./configs
COPY vendor ./vendor
RUN if [ "${APPA_TAINT_INSTALL}" = "1" ]; then \
      pip install --no-cache-dir vendor/appa_agent_python-*.whl; \
    fi

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

ARG APP_MODULE
ENV APP_MODULE=${APP_MODULE}
CMD ["sh", "-c", "uvicorn ${APP_MODULE}:app --host 0.0.0.0 --port ${PORT:-8000}"]

