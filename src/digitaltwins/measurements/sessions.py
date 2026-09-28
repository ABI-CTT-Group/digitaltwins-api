"""CRUD for ``public.upload_session`` rows (the upload control plane)."""
from typing import Any, Dict, List, Optional

from psycopg2.extras import Json, RealDictCursor

_UPDATABLE = {
    "status", "failure_stage", "failure_message", "fhir_mode", "fhir_descriptions", "dataset_uuid",
}


def create_session(
    conn,
    category: str,
    name: str,
    description: Optional[str],
    source_kind: str,
    commit_mode: str,
    fhir_mode: str = "none",
    fhir_descriptions: Optional[Dict[str, Any]] = None,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO upload_session "
            "(category, name, description, source_kind, commit_mode, fhir_mode, fhir_descriptions) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING upload_id",
            (category, name, description, source_kind, commit_mode, fhir_mode,
             Json(fhir_descriptions) if fhir_descriptions is not None else None),
        )
        upload_id = cur.fetchone()[0]
    conn.commit()
    return str(upload_id)


def get_session(conn, upload_id: str) -> Optional[Dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM upload_session WHERE upload_id = %s", (str(upload_id),))
        row = cur.fetchone()
    conn.commit()
    return dict(row) if row else None


def list_sessions(conn, statuses: List[str]) -> List[Dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM upload_session WHERE status = ANY(%s) ORDER BY created_at DESC",
            (list(statuses),),
        )
        rows = cur.fetchall()
    conn.commit()
    return [dict(r) for r in rows]


def update_session(conn, upload_id: str, **fields) -> None:
    unknown = set(fields) - _UPDATABLE
    if unknown:
        raise ValueError(f"Not updatable: {sorted(unknown)}")
    if "fhir_descriptions" in fields and fields["fhir_descriptions"] is not None:
        fields["fhir_descriptions"] = Json(fields["fhir_descriptions"])
    assignments = ", ".join(f"{column} = %s" for column in fields)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE upload_session SET {assignments}, updated_at = now() WHERE upload_id = %s",
            (*fields.values(), str(upload_id)),
        )
    conn.commit()


def delete_session(conn, upload_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM upload_session WHERE upload_id = %s", (str(upload_id),))
    conn.commit()
