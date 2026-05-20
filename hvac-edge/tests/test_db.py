# hvac-edge/tests/test_db.py
import tempfile, os
from edge.db import init_db


def test_init_db_creates_tables():
    db_path = os.path.join(tempfile.mkdtemp(), "test.duckdb")
    conn = init_db(db_path)

    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    table_names = [t[0] for t in tables]

    assert "readings" in table_names
    assert "inspections" in table_names
    assert "work_orders" in table_names
    assert "sync_queue" in table_names
    assert "sync_meta" in table_names
    conn.close()


def test_insert_and_query_reading():
    db_path = os.path.join(tempfile.mkdtemp(), "test2.duckdb")
    conn = init_db(db_path)

    conn.execute(
        "INSERT INTO readings (time, point_id, value, quality) VALUES ('2026-05-20T10:00:00Z', 'p1', 23.5, 'good')"
    )
    result = conn.execute("SELECT value FROM readings WHERE point_id = 'p1'").fetchone()
    assert result[0] == 23.5
    conn.close()
