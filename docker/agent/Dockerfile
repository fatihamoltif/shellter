# Image du Worker Agent réel (SDK Docker) — intégration SSH réelle.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /agent

RUN pip install --no-cache-dir flask==3.0.3 docker==7.1.0 requests==2.32.3

COPY docker/agent/agent_real.py /agent/agent_real.py
COPY docker/ssh /agent/ssh

EXPOSE 5000
CMD ["python", "agent_real.py"]
