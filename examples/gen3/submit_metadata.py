from dtp.gen3.metadata_uploader import MetadataUploader
from pathlib import Path

if __name__ == '__main__':
    endpoint = "GEN3_URL"
    cred_file = Path(r"/path/to/gen3/credentials/file")
    program = "demo1"
    project = "12L"
    file = Path(r"/path/to/gen3/json/metadata")

    auth = Auth(endpoint, cred_file)

    submitter = MetadataUploader(auth)
    submitter.submit_record(program, project, str(file))
