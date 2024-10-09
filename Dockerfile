FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

COPY explo-bot-3e5798a0c8ca.json /app/explo-bot-3e5798a0c8ca.json

ENV GOOGLE_APPLICATION_CREDENTIALS="/app/explo-bot-3e5798a0c8ca.json"

CMD ["python", "app.py"]
