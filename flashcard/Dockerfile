FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the init_db script first, then start the server
CMD python init_db.py && uvicorn app:app --host 0.0.0.0 --port 8000
