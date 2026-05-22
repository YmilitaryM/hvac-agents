# HVAC Platform -- Grafana Dashboards

Pre-built Grafana dashboard templates for monitoring the HVAC microservices platform.

## Dashboards

| File | Dashboard | UID | Description |
|------|-----------|-----|-------------|
| `dashboards/overview.json` | HVAC - Service Overview | `hvac-overview` | System-wide health: request rates, latency percentiles, error rates, DB pools, circuit breaker status across all services |
| `dashboards/energy-service.json` | HVAC - Energy Service | `hvac-energy-service` | Energy service deep-dive: endpoint-level traffic, latency, errors, and energy_db pool |
| `dashboards/health-service.json` | HVAC - Health Service | `hvac-health-service` | Health service deep-dive: endpoint-level traffic, latency, errors, and health_db pool |
| `dashboards/gateway.json` | HVAC - Gateway & Routing | `hvac-gateway` | Gateway-specific: traffic per proxied backend, latency, 502/504 counts, circuit breaker states |

## Prerequisites

- **Grafana** 10.x or later (schema version 38)
- **Prometheus** data source scraping the HVAC services at their `/metrics` endpoints
- Each HVAC service must expose the standard `hvac_*` metrics (see below)

## How to Import

### Via Grafana UI

1. In Grafana, go to **Dashboards > New > Import** (or click the **+** icon and choose **Import dashboard**).
2. Click **Upload JSON file** and select the desired dashboard from `monitoring/grafana/dashboards/`.
3. In the **Prometheus** data source dropdown, select your Prometheus data source.
4. Click **Import**.

### Via Grafana Provisioning (recommended for automation)

Add a provisioning config to your Grafana instance:

```yaml
# /etc/grafana/provisioning/dashboards/hvac.yaml
apiVersion: 1
providers:
  - name: 'HVAC'
    orgId: 1
    folder: 'HVAC Platform'
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/dashboards/hvac
```

Then copy the dashboard JSON files into `/etc/grafana/dashboards/hvac/`.

### Via REST API

```bash
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d '{
    "dashboard": '"$(cat dashboards/overview.json)"',
    "overwrite": true,
    "inputs": [{"name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus", "value": "Prometheus"}]
  }'
```

## Prometheus Data Source

All dashboards expect a Prometheus data source. The data source is referenced via the Grafana variable `${DS_PROMETHEUS}` -- this is resolved at import time when you choose which Prometheus instance to use.

### Required Metrics

The following metrics must be available in Prometheus:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `hvac_http_requests_total` | Counter | `service`, `method`, `endpoint`, `status` | Total HTTP requests per service |
| `hvac_http_request_duration_seconds` | Histogram | `service`, `method`, `endpoint` | Request latency histogram |
| `hvac_db_pool_size` | Gauge | `service` | Maximum DB connection pool size |
| `hvac_db_pool_active` | Gauge | `service` | Currently active DB connections |
| `hvac_circuit_breaker_state` | Gauge | `service`, `target` | Circuit breaker state (0=closed, 1=open, 2=half-open) |

### Prometheus Scrape Config Example

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'hvac-services'
    scrape_interval: 15s
    static_configs:
      - targets:
          - 'gateway:8000'
          - 'asset_service:8001'
          - 'energy_service:8002'
          - 'health_service:8003'
          - 'agent_service:8004'
          - 'env_service:8005'
          - 'sim_service:8006'
          - 'acquisition_service:8007'
          - 'edgemanager_service:8008'
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - '9090:9090'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:10.4.0
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/dashboards/hvac
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    ports:
      - '3000:3000'
    networks:
      - monitoring
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
```

### Provisioning Config for Docker Compose

Create `monitoring/grafana/provisioning/datasources/prometheus.yaml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

Create `monitoring/grafana/provisioning/dashboards/hvac.yaml`:

```yaml
apiVersion: 1
providers:
  - name: 'HVAC'
    orgId: 1
    folder: 'HVAC Platform'
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/dashboards/hvac
```

## Alert Thresholds

Each dashboard includes pre-configured color thresholds:

| Panel | Green | Yellow | Red |
|-------|-------|--------|-----|
| P95 Latency | < 300ms | 300ms -- 500ms | > 500ms |
| P99 Latency | < 500ms | 500ms -- 1s | > 1s |
| 4xx Error Rate | < 1 req/s | 1 -- 5 req/s | > 5 req/s |
| 5xx Error Rate | 0 req/s | -- | > 0.1 req/s |
| DB Pool Utilization | < 50% | 50 -- 75% | > 90% |
| Error Ratio | < 1% | 1 -- 5% | > 5% |
| Circuit Breaker | Closed (0) | Half-Open (2) | Open (1) |

Adjust thresholds to match your SLOs and capacity planning requirements.

## Customization

- **Time range**: Default is 24 hours. Change the `time.from` value in each JSON file (e.g., `"now-7d"` for a week).
- **Refresh interval**: Default is 30 seconds. Change the `refresh` value (e.g., `"1m"`).
- **Service filtering**: The overview dashboard includes a `$service` template variable populated from `label_values(hvac_http_requests_total, service)`. Service-specific dashboards are pre-filtered.
- **Adding new services**: New services will automatically appear in the `$service` variable once they start emitting metrics.
