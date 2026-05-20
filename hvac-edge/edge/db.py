import duckdb


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS readings (
    time       TIMESTAMPTZ NOT NULL,
    point_id   VARCHAR(32) NOT NULL,
    value      DOUBLE NOT NULL,
    quality    VARCHAR(16) DEFAULT 'good',
    PRIMARY KEY (time, point_id)
);

CREATE TABLE IF NOT EXISTS inspections (
    id         BIGINT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at   TIMESTAMPTZ,
    plan_id    VARCHAR(64) NOT NULL,
    status     VARCHAR(16) DEFAULT 'running',
    result     JSON
);

CREATE TABLE IF NOT EXISTS work_orders (
    id            BIGINT PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL,
    equipment_id  VARCHAR(32) NOT NULL,
    severity      VARCHAR(16) NOT NULL,
    title         VARCHAR(256) NOT NULL,
    description   TEXT,
    status        VARCHAR(16) DEFAULT 'open',
    synced_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id         BIGINT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    topic      VARCHAR(128) NOT NULL,
    payload    JSON NOT NULL,
    qos        TINYINT DEFAULT 1,
    retries    INT DEFAULT 0,
    synced     BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS sync_meta (
    table_name   VARCHAR(64) PRIMARY KEY,
    last_sent_at TIMESTAMPTZ NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS seq_inspection_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_work_order_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_sync_queue_id START 1;
"""


def init_db(path: str = "edge_data.duckdb") -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(path)
    conn.execute(SCHEMA_SQL)
    return conn
