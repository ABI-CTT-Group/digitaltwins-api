"""Upload a SPARC measurement dataset to the DigitalTWINS platform through the REST API.

The upload is chunked and resumable, so it suits large datasets. The script
waits until the dataset is stored (platform Postgres + MinIO) and, if FHIR
annotation was requested, until it has been pushed to FHIR.

    python upload_measurement_dataset.py path/to/my_dataset --fhir auto
    python upload_measurement_dataset.py path/to/my_dataset.zip --name "My dataset"
    python upload_measurement_dataset.py path/to/my_dataset --descriptions annotation.json

If the upload is interrupted, run the command the script prints (the same
arguments plus ``--resume <upload_id>``); only the missing parts are sent.

Sign-in: the Keycloak account needs the realm role ``admin`` or ``researcher``.
The username comes from ``--username`` or ``DIGITALTWINS_USERNAME``; the
password from ``DIGITALTWINS_PASSWORD`` or a prompt. It is never accepted on
the command line, so it does not end up in shell history.

Requires the ``digitaltwins`` package (``pip install -e .`` in digitaltwins-api).
"""
import argparse
import getpass
import json
import os
import shlex
import sys
from pathlib import Path

from digitaltwins import UploadClient
from digitaltwins.client import UploadError

DEFAULT_URL = "http://localhost/digitaltwins-api"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="dataset folder or .zip")
    parser.add_argument("--url", default=os.getenv("DIGITALTWINS_API_URL", DEFAULT_URL),
                        help=f"digitaltwins-api base URL (default: $DIGITALTWINS_API_URL or {DEFAULT_URL})")
    parser.add_argument("--username", default=os.getenv("DIGITALTWINS_USERNAME"),
                        help="Keycloak username (default: $DIGITALTWINS_USERNAME, else prompt)")
    parser.add_argument("--name", help="dataset name (default: folder / zip name)")
    parser.add_argument("--description")
    parser.add_argument("--category", default="measurements")
    fhir = parser.add_mutually_exclusive_group()
    fhir.add_argument("--fhir", choices=["none", "auto"], default="none",
                      help="auto: annotate every sample automatically and push to FHIR")
    fhir.add_argument("--descriptions", type=Path, metavar="FILE",
                      help="FHIR annotation JSON (subjects/samples by folder name; UUIDs are assigned) "
                           "to push instead of the automatic one")
    parser.add_argument("--resume", metavar="UPLOAD_ID", help="continue an interrupted upload of the same path")
    parser.add_argument("--no-wait-fhir", action="store_true",
                        help="return once the dataset is stored, without waiting for the FHIR push")
    return parser.parse_args(argv)


def _login(args) -> UploadClient:
    username = args.username or input("Username: ").strip()
    password = os.getenv("DIGITALTWINS_PASSWORD") or getpass.getpass(f"Password for {username}: ")
    return UploadClient.login(args.url, username, password)


def main(argv=None, client=None) -> int:
    args = parse_args(argv)
    path = Path(args.path)
    if not path.exists():
        print(f"No such path: {path}", file=sys.stderr)
        return 2
    descriptions = json.loads(args.descriptions.read_text()) if args.descriptions else None

    client = client or _login(args)
    try:
        if args.resume:
            print(f"Resuming upload {args.resume} of {path} …")
            session = client.resume(args.resume, path, wait_for_fhir=not args.no_wait_fhir)
        else:
            files = [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else [path]
            size_mb = sum(p.stat().st_size for p in files) / 1024 ** 2
            print(f"Uploading {path} ({len(files)} file(s), {size_mb:.1f} MB) …")
            session = client.upload_dataset(
                path, category=args.category, name=args.name, description=args.description,
                fhir=None if args.fhir == "none" else args.fhir, fhir_descriptions=descriptions,
                wait_for_fhir=not args.no_wait_fhir,
            )
    except UploadError as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        return 1
    except (OSError, KeyboardInterrupt) as e:  # network errors are OSErrors; Ctrl-C mid-transfer
        return _interrupted(e, client, argv)

    fhir_requested = args.fhir != "none" or descriptions is not None
    print(f"Dataset UUID: {session['dataset_uuid']}")
    print(f"FHIR: {session.get('fhir_status', 'pending') if fhir_requested else 'not requested'}")
    return 0


def _interrupted(error, client, argv) -> int:
    print(f"Upload interrupted: {error}", file=sys.stderr)
    if client.last_upload_id:
        rerun = shlex.join(argv if argv is not None else sys.argv[1:])
        print(f"Resume with: python {Path(__file__).name} {rerun} --resume {client.last_upload_id}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
