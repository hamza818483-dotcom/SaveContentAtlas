FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg curl unzip && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY main ./main
CMD ["python", "-u", "-m", "main"]
