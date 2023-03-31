from ctp.gen3.submitter import Gen3Submitter
from pathlib import Path

if __name__ == '__main__':
    endpoint = "GEN3_URL"
    credentials = Path(r"/path/to/gen3/credentials/file")
    program = "demo1"
    project = "12L"
    file = Path(r"/path/to/gen3/json/metadata")

    submitter = Gen3Submitter(endpoint, str(credentials))
    submitter.submit_record(program, project, str(file))
