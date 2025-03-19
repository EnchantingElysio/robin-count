FROM python:3.13-alpine

WORKDIR /app

COPY requirements.txt .

COPY dev.requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-u", "main.py"]
