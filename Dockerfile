FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=monitor.py
ENV TG_TOKEN=""
ENV TG_CHAT_ID=""

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
