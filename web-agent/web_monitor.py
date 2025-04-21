import os
import time
import subprocess
import requests
import psycopg2
import logging
from datetime import datetime

if os.getenv("LOG_DURING_BUILD") == "true":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
else:
    logging.disable(logging.CRITICAL)

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST"),
    "database": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD")
}

TARGETS = ["google.com", "youtube.com", "rnp.br"]

def check_ping(target):
    try:
        result = subprocess.run(
            ['ping', '-c', '4', target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        output = result.stdout
        if 'rtt min/avg/max/mdev' in output:
            stats = output.split('rtt min/avg/max/mdev = ')[1].split('/')
            latency = float(stats[1])
            packet_loss = float(output.split('% packet loss')[0].split()[-1])
            logging.info(f"Ping para {target} OK")
            return latency, packet_loss
        return None, 100.0
        
    except Exception as e:
        logging.error(f"Erro no ping para {target}: {e}", exc_info=True)
        return None, 100.0

def check_http(target):
    try:
        start = time.time()
        response = requests.get(f"https://{target}", timeout=20)
        elapsed = (time.time() - start) * 1000
        logging.info(f"Requisição HTTP para {target} OK")
        return elapsed, response.status_code
    except Exception as e:
        logging.error(f"Erro HTTP para {target}: {e}", exc_info=True)
        return None, None

def store_metrics(metrics):
    if not metrics:
        return
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        data_to_insert = [
            (
                metric["timestamp"],
                metric["target"],
                metric["metric_type"],
                metric["latency"],
                metric["packet_loss"],
                metric["response_time"],
                metric["status_code"]
            )
            for metric in metrics
        ]
        
        cursor.executemany("""
            INSERT INTO web_monitoring.metrics 
            (timestamp, target, metric_type, latency, packet_loss, response_time, status_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, data_to_insert)
        
        conn.commit()
        logging.info("Dados Armazenados com sucesso!")
    except Exception as e:
        logging.error(f"Erro no banco de dados: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    while True:
        logging.info("Iniciando ciclo de monitoramento...")
        all_metrics = []
        
        for target in TARGETS:
            latency, packet_loss = check_ping(target)
            if latency is not None:
                all_metrics.append({
                    "timestamp": datetime.now(),
                    "target": target,
                    "metric_type": "ping",
                    "latency": latency,
                    "packet_loss": packet_loss,
                    "response_time": None,
                    "status_code": None
                })
            
            response_time, status_code = check_http(target)
            if status_code:
                all_metrics.append({
                    "timestamp": datetime.now(),
                    "target": target,
                    "metric_type": "http",
                    "latency": None,
                    "packet_loss": None,
                    "response_time": response_time,
                    "status_code": status_code
                })
        
        store_metrics(all_metrics)
        time.sleep(5)
