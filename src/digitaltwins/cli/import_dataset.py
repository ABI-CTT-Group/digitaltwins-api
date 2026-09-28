"""Import a measurement dataset from inside the digitaltwins-api container.

    python -m digitaltwins.cli.import_dataset <folder|zip> [--name N] [--fhir auto] [--move]

Signs in with Keycloak (browser device flow, or ``--password``), checks the
upload role, then runs the same pipeline as ``/datasets/uploads`` in-process:
SPARC validation → commit (Postgres + MinIO) → optional FHIR push. The
``scripts/import-dataset.*`` wrappers copy a dataset from the host into the
container and call this.

Exit codes: 0 ok, 1 commit / FHIR failed, 2 invalid dataset, 3 not authorised.
"""
import argparse
import shutil
import sys
from pathlib import Path

from ..core.connection import Connection
from ..measurements import jobs, pipeline, sessions
from ..measurements.staging import dataset_dir, staging_root
from ..measurements.validation import extract_uploaded_archive, resolve_project_root, validate_sparc_structure
from .keycloak_login import login


def _parse(argv):
    parser = argparse.ArgumentParser(prog="python -m digitaltwins.cli.import_dataset", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="dataset folder or .zip")
    parser.add_argument("--name", help="dataset name (default: folder / zip name)")
    parser.add_argument("--description")
    parser.add_argument("--fhir", choices=["none", "auto"], default="none", help="auto-annotate and push FHIR")
    parser.add_argument("--category", default="measurements")
    parser.add_argument("--move", action="store_true", help="move (not copy) the folder into staging")
    parser.add_argument("--password", action="store_true", help="password login instead of the device flow")
    parser.add_argument("--username")
    return parser.parse_args(argv)


def _fail(code: int, message: str) -> int:
    print(f"  ✗ {message}", file=sys.stderr)
    return code


def main(argv=None) -> int:
    args = _parse(argv)
    try:
        username = login(use_password=args.password, username=args.username)
    except PermissionError as e:
        return _fail(3, str(e))

    path = Path(args.path)
    if not path.exists():
        return _fail(2, f"No such path: {path}")

    extracted = None
    try:
        if path.is_file():
            try:
                extracted = extract_uploaded_archive(staging_root() / "import", path)
            except Exception as e:
                return _fail(2, f"Cannot extract {path.name}: {e}")
            source = extracted
        else:
            source = path
        ok, message = validate_sparc_structure(source)
        if not ok:
            return _fail(2, message)
        root = resolve_project_root(source)

        conn, _ = Connection().connect()
        try:
            upload_id = sessions.create_session(
                conn, category=args.category, name=args.name or (path.stem if path.is_file() else path.name),
                description=args.description, source_kind="zip" if path.is_file() else "folder",
                commit_mode="on_finalize", fhir_mode=args.fhir,
            )
            target = dataset_dir(upload_id)
            target.parent.mkdir(parents=True, exist_ok=True)
            print(f"  Importing as {username}…")
            if extracted is not None or args.move:
                shutil.move(str(root), str(target))
            else:
                shutil.copytree(root, target)
            sessions.update_session(conn, upload_id, status="processing")
            jobs.run_commit_and_push(upload_id)

            session = sessions.get_session(conn, upload_id)
            if session["status"] != "completed":
                return _fail(1, f"Commit failed: {session['failure_message']}")
            dataset = pipeline.get_dataset_row(conn, session["dataset_uuid"])
        finally:
            conn.close()
    finally:
        if extracted is not None:
            shutil.rmtree(extracted, ignore_errors=True)

    print(f"  ✓ Imported dataset {session['dataset_uuid']} (FHIR: {dataset['fhir_status']})")
    if dataset["fhir_status"] == "failed":
        return _fail(1, f"FHIR push failed; retry with POST /datasets/{session['dataset_uuid']}/fhir/push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
