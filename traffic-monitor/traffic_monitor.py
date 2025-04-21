import os
import requests
import psycopg2
from datetime import datetime
import time
import logging


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

VIA_IPE_ENDPOINT = "https://viaipe.rnp.br/api/norte"
HEADERS = {"Accept": "application/json"}

def fetch_viaipe_data():
    try:
        response = requests.get(VIA_IPE_ENDPOINT, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Erro na API: {str(e)}", exc_info=True)
        return None

def calculate_metrics(data):
    if not data or not isinstance(data, list):
        logging.warning("Dados inválidos ou estrutura inesperada")
        return []

    metrics = []
    for node in data:
        try:
            if "data" not in node or "id" not in node:
                logging.warning(f"Nó inválido: campos 'data' ou 'id' faltando: {node}")
                continue

            node_data = node.get("data", {})
            interfaces = node_data.get("interfaces", [])
            smoke = node_data.get("smoke", {})
            
            if not interfaces:
                logging.warning(f"Nó {node['id']} sem interfaces válidas")
                continue

            # Agregar dados de interfaces de cada cliente 
            total_traffic_in = sum(iface.get("traffic_in", 0) for iface in interfaces)
            total_traffic_out = sum(iface.get("traffic_out", 0) for iface in interfaces)
            total_max_down = sum(iface.get("max_traffic_down", 1) for iface in interfaces)
            total_max_up = sum(iface.get("max_traffic_up", 1) for iface in interfaces)

            # calcula porcentagem de disponibilidade baseada na perda de pacotes
            loss_percent = smoke.get("loss", 0)
            availability = 100 - loss_percent

            # 2. Consumo de Banda (em porcentagem da capacidade máxima)
            bandwidth_usage_down = (total_traffic_in / total_max_down) * 100 if total_max_down > 0 else 0
            bandwidth_usage_up = (total_traffic_out / total_max_up) * 100 if total_max_up > 0 else 0
            bandwidth_usage_avg = (bandwidth_usage_down + bandwidth_usage_up) / 2
            
            # Qualidade textual baseada na perda de pacotes
            avg_loss = smoke.get("avg_loss", 0)
            if avg_loss <= 0.01:
                quality_label = "Ótima"
                quality_score = 100
            elif avg_loss <= 1:
                quality_label = "Boa"
                quality_score = 80
            elif avg_loss <= 3:
                quality_label = "Regular"
                quality_score = 50
            else:
                quality_label = "Ruim"
                quality_score = 20

            metrics.append({
                "client_id": node.get("id", "unknown"),
                "client_name": node.get("name", "unknown"),
                "availability": round(availability, 2),
                "bandwidth_usage": round(bandwidth_usage_avg, 2),
                "quality": quality_label,
                "timestamp": datetime.now()
            })
        except Exception as e:  
            logging.error(f"Erro processando nó {node.get('id')}: {str(e)}", exc_info=True)

    return metrics

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
                metric["client_id"],
                metric["client_name"],
                metric["availability"],
                metric["bandwidth_usage"],
                metric["quality"]
            )
            for metric in metrics
        ]
        
        cursor.executemany("""
            INSERT INTO traffic_monitoring.metrics 
            (timestamp, client_id, client_name, availability, bandwidth_usage, quality_score)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, data_to_insert)
        
        conn.commit()
        
    except psycopg2.OperationalError as e:
        logging.error(f"Erro de conexão com o banco: {e}", exc_info=True)
    except psycopg2.DatabaseError as e:
        logging.error(f"Erro de banco de dados: {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e:
        logging.error(f"Erro inesperado: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    while True:
        logging.info("Iniciando coleta...")
        data = fetch_viaipe_data()
        if data:
            logging.info(f"Dados brutos recebidos: {len(data)} registros")
            metrics = calculate_metrics(data)
            if metrics:
                logging.info(f"Métricas calculadas: {len(metrics)}")
                store_metrics(metrics)
                logging.info("Dados armazenados com sucesso!")
            else:
                logging.warning("Nenhuma métrica calculada.")
        else:
            logging.error("Falha ao obter dados da API.")
        
        time.sleep(15)
