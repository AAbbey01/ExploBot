FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

COPY explo-bot-revival-6f275d2323e4.json /app/explo-bot-revival-6f275d2323e4.json


CMD ["python", "app.py"]
