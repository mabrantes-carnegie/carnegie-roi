FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and parameterized query templates only.
COPY app/ ./app/
COPY data/queries/ ./data/queries/

EXPOSE 8080

CMD ["shiny", "run", "app/app.py", "--host", "0.0.0.0", "--port", "8080"]
