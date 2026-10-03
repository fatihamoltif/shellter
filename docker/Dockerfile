FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --default-timeout=1000 -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
