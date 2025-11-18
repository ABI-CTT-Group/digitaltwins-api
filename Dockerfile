FROM python:3.11-slim

WORKDIR /digitaltwins-api

# install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# copy files
COPY pyproject.toml .
#COPY requirements-docker.txt requirements-prod.txt
COPY requirements-prod.txt .
#COPY src/digitaltwins src/digitaltwins
COPY src ./src
COPY app ./app

# install pythion dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements-prod.txt
RUN pip install --no-cache-dir -e .

# Expose API port
EXPOSE 8000

# Run the app
#WORKDIR /digitaltwins-api
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# building image
# sudo docker build -t digitaltwins-api .
# running container
# sudo docker run --rm -d -p 8010:8000 digitaltwins-api

# print docker image folder strcutre
# sudo docker run --rm digitaltwins-api ls -l /digitaltwins-api
# sudo docker run --rm digitaltwins-api ls -lR /digitaltwins-api



