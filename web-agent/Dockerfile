FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    iputils-ping \
    procps \
 && ln -snf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime \
 && echo "America/Sao_Paulo" > /etc/timezone \
 && dpkg-reconfigure -f noninteractive tzdata \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web_monitor.py .

ARG LOG_DURING_BUILD
ENV LOG_DURING_BUILD=true

CMD ["python", "web_monitor.py"]
