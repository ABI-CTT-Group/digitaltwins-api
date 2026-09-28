# Importing a measurement dataset from the server terminal

This is a one-command way to import a prepared SPARC measurement dataset into the platform, with no GUI and no code. It is meant for people with shell access to the server. The command:
- validates the dataset
- stores the files in MinIO and the metadata in the platform Postgres
- optionally annotates the dataset and pushes it to FHIR

Afterwards the dataset appears in the portal as **completed**.

The dataset can be a **folder or a `.zip`**. It must be a SPARC measurements dataset: a `dataset_description.*` file plus `primary/<sub-XXX>/<sam-YYY>/<files>`. A `.zip` may wrap the dataset in a single top-level folder; that folder is unwrapped automatically. `subjects.xlsx` and `samples.xlsx` are optional. Subjects and samples missing from them are registered from the `primary/` folder names, so every sample gets a platform UUID.

> **Data safety:** your original dataset on the host is never modified. The copy made inside the container is kept only as a local cache for the FHIR build. It is removed after a successful FHIR push, or after 7 days. The canonical data lives in MinIO, Postgres and FHIR.

---

## Two steps

The dataset can live **anywhere on the host**. You just give its path.

1. **Run** the importer with the dataset (folder or `.zip`). The scripts are in this repository's `scripts/` folder:

   | OS | Double-click | …or from a terminal |
   |---|---|---|
   | **macOS** | `scripts/import-dataset.command` (asks for the path) | `./scripts/import-dataset.sh /path/to/mydataset --fhir auto` |
   | **Windows** | `scripts\import-dataset.bat` (asks for the path; or drag a folder or zip onto it) | `.\scripts\import-dataset.ps1 C:\data\mydataset --fhir auto` |
   | **Linux** | servers are usually headless, so use a terminal | `./scripts/import-dataset.sh /path/to/mydataset --fhir auto` |

   > **Windows:** double-click the **`.bat`**. Double-clicking a `.ps1` only opens it in an editor. If a script isn't executable on macOS or Linux, run `chmod +x scripts/import-dataset.*`.

   The script finds the running `digitaltwins-api` container and copies the dataset into it. It shows a live progress bar if [`pv`](https://www.ivarch.com/programs/pv.shtml) is installed (`apt install pv` / `brew install pv`); otherwise it prints the size. Then it runs the importer inside the container.

2. **Sign in** when prompted. Open the printed link in your browser and log in with your normal account. You need the realm role **admin** or **researcher**, the same as for uploading through the portal or the REST API.

---

## What it does

```
sign in (admin | researcher) → validate the SPARC structure
→ register in Postgres (dataset, subjects, samples → platform UUIDs) + upload to MinIO
→ with --fhir auto: auto-annotate from the files → push to FHIR (identifiers = platform UUIDs)
```

The importer runs the same pipeline as `POST /datasets/uploads` in the REST API. For large uploads from a remote machine, use the Python `UploadClient` instead (see the README). It can also send your own annotation (`fhir_descriptions`).

## Options

```
import-dataset.(sh|command|ps1) <FOLDER_OR_ZIP> [--name NAME] [--description TEXT] [--fhir auto|none] [--password] [--username U]
```

- `FOLDER_OR_ZIP`: host path to the dataset folder or `.zip`. The script copies it into the container.
- `--name NAME`: dataset name. The default is the folder or zip name. Names don't have to be unique, because datasets are identified by UUID.
- `--fhir auto`: annotate every sample automatically and push the result to FHIR. The default, `none`, stores the dataset only; you can annotate and push it later from the portal or with `POST /datasets/{uuid}/fhir/push`.
- `--password` / `--username U`: sign in with a username and password instead of the browser flow. Use this only if the Keycloak device flow isn't enabled.

## Exit codes

- `0`: success
- `1`: the commit or the FHIR push failed. The dataset copy is kept. If only the FHIR push failed, the dataset is stored; retry with `POST /datasets/{uuid}/fhir/push`.
- `2`: invalid dataset (not a SPARC measurements dataset, or a broken zip)
- `3`: not authorised (the account has neither the `admin` nor the `researcher` role)

## Prerequisites (one-time, ops)

- The Keycloak client used by the API (`KEYCLOAK_CLIENT_ID`) has the **device flow** enabled; otherwise use `--password`.
- Operators have the `admin` or `researcher` realm role.
- The stack is up (`docker compose up -d`). The importer runs inside the `digitaltwins-api` container.
