from pathlib import Path
from irods.session import iRODSSession
from irods.exception import DataObjectDoesNotExist

from ..utils.config_loader import ConfigLoader

class Querier(object):
    """
    Class for interacting with iRODS server
    """
    def __init__(self, config_file):
        """
        Constructor
        """

        self._configs = ConfigLoader.load_from_ini(config_file)

        self._configs = self._configs["irods"]
        self._host = self._configs.get("irods_host")
        self._port = self._configs.get("irods_port")
        self._user = self._configs.get("irods_user")
        self._password = self._configs.get("irods_password")
        self._zone = self._configs.get("irods_zone")
        self._project_root = self._configs.get("irods_project_root")

    def load_file(self, path):
        with iRODSSession(host=self._host,
                          port=self._port,
                          user=self._user,
                          password=self._password,
                          zone=self._zone) as session:
            path = Path(self._project_root) / path

            try:
                obj = session.data_objects.get(str(path))
            except DataObjectDoesNotExist:
                raise FileNotFoundError(f"The CWL file was not found in iRODS: {path}")

            with obj.open('r') as file_obj:
                contents = file_obj.read()

        return contents


