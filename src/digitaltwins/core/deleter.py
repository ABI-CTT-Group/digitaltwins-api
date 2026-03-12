import os
from pathlib import Path

from gen3.auth import Gen3Auth, Gen3AuthError
from gen3.submission import Gen3Submission

from digitaltwins import Querier
from digitaltwins.irods.irods import IRODS

from requests.exceptions import HTTPError

from dotenv import load_dotenv
load_dotenv()

import urllib3
urllib3.disable_warnings()


class Deleter(object):
    def __init__(self):
        self._gen3_cred_file = os.getenv("GEN3_CRED_FILE")
        self._ssl_cert = os.getenv("GEN3_SSL_CERT")

        if self._gen3_cred_file:
            self._gen3_cred_file = str(Path(self._gen3_cred_file).resolve())
        if self._ssl_cert:
            self._ssl_cert = str(Path(self._ssl_cert).resolve())
            os.environ["REQUESTS_CA_BUNDLE"] = self._ssl_cert

        self._program = os.getenv("GEN3_PROGRAM")
        self._project = os.getenv("GEN3_PROJECT")
        self._gen3_endpoint = os.getenv("GEN3_ENDPOINT")

        self._auth = Gen3Auth(self._gen3_endpoint, refresh_file=self._gen3_cred_file)
        self._submission = Gen3Submission(self._gen3_endpoint, self._auth)

    def delete(self, dataset_id):
        self.delete_metadata(dataset_id)
        self.delete_dataset(dataset_id)

    def delete_metadata(self, dataset_id):
        querier = Querier()
        records = querier.get_dataset_records(dataset_id=dataset_id, program=self._program, project=self._project)

        try:
            self._submission.delete_records(program=self._program, project=self._project, uuids=records, batch_size=1000)
        except HTTPError as e:
            print("Connection failed.")
            raise HTTPError("HTTP connection error: Please make sure you have access to the remote server. then "
                                  "try again!")
        except Gen3AuthError as e:
            raise ValueError("Connection failed. Please try again. If the error persists, please contact the developers")
    #
    def delete_dataset(self, dataset_id):
        irods = IRODS()
        irods.delete(dataset_id)
