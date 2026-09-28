"""Numbered SQL migrations for the platform ``public`` schema.

``services/postgres/digitaltwins_schema.sql`` is the baseline and only runs on an
empty volume; everything after it ships here as ``migrations/NNNN_<name>.sql``.
Each file runs in its own transaction and is recorded in ``schema_migrations``.
Runs are serialised with a Postgres advisory lock, so concurrent API workers
starting together apply each migration exactly once.

Usage: ``python -m digitaltwins.postgres.migrate`` (reads POSTGRES_* env vars),
or ``apply_migrations(conn)`` from the API's startup hook.
"""
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_FILENAME = re.compile(r"^(\d{4})_[\w-]+\.sql$")
# Arbitrary constant identifying this runner's advisory lock.
_LOCK_KEY = 0x6474_6D69  # "dtmi"


def discover(migrations_dir=MIGRATIONS_DIR):
    """Return ``[(version, path), ...]`` sorted by version."""
    found = {}
    for path in Path(migrations_dir).iterdir():
        match = _FILENAME.match(path.name)
        if not match:
            continue
        version = match.group(1)
        if version in found:
            raise ValueError(f"Duplicate migration version {version}: {found[version].name}, {path.name}")
        found[version] = path
    return sorted(found.items())


def apply_migrations(conn, migrations_dir=MIGRATIONS_DIR):
    """Apply pending migrations on ``conn``; return the versions applied.

    A failing migration is rolled back and re-raised; later migrations are not
    attempted.
    """
    migrations = discover(migrations_dir)
    applied_now = []
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        conn.commit()
        try:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS public.schema_migrations ("
                " version varchar(4) PRIMARY KEY,"
                " name text NOT NULL,"
                " applied_at timestamptz NOT NULL DEFAULT now())"
            )
            cur.execute("SELECT version FROM public.schema_migrations")
            done = {row[0] for row in cur.fetchall()}
            conn.commit()

            for version, path in migrations:
                if version in done:
                    continue
                try:
                    cur.execute(path.read_text())
                    cur.execute(
                        "INSERT INTO public.schema_migrations (version, name) VALUES (%s, %s)",
                        (version, path.name),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    logger.error("Migration %s failed; rolled back", path.name)
                    raise
                logger.info("Applied migration %s", path.name)
                applied_now.append(version)
        finally:
            cur.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))
            conn.commit()
    return applied_now


def run():
    """Connect with the POSTGRES_* env vars and apply pending migrations."""
    from digitaltwins.core.connection import Connection

    conn, _ = Connection().connect()
    try:
        applied = apply_migrations(conn)
    finally:
        conn.close()
    logger.info("Applied %d migration(s): %s", len(applied), ", ".join(applied) or "none pending")
    return applied


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()
