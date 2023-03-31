from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission


class Gen3Submitter(object):
    """
    Submitting metadata to gen3
    """

    def __init__(self, endpoint, credentials):
        self._endpoint = endpoint
        self._credentials = credentials

        self._auth = Gen3Auth(endpoint, refresh_file="credentials.json")
        self._submission = Gen3Submission(endpoint, self._auth)

    def submit_record(self, program, project, file):
        self._submission.submit_record(program, project, file)


