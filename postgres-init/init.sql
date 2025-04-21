CREATE SCHEMA IF NOT EXISTS web_monitoring;
CREATE SCHEMA IF NOT EXISTS traffic_monitoring;

CREATE TABLE IF NOT EXISTS web_monitoring.metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    target VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    latency FLOAT,
    packet_loss FLOAT,
    response_time FLOAT,
    status_code INT
);

CREATE TABLE IF NOT EXISTS traffic_monitoring.metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    client_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    availability NUMERIC,
    bandwidth_usage NUMERIC,
    quality_score TEXT
);

GRANT USAGE ON SCHEMA web_monitoring TO monitor;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA web_monitoring TO monitor;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA web_monitoring TO monitor;

GRANT USAGE ON SCHEMA traffic_monitoring TO monitor;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA traffic_monitoring TO monitor;
