import os

from dtp.utils.config_loader import ConfigLoader

from irods.session import iRODSSession


class IRODSAPI(object):
    """
    Class for interacting with iRODS server
    """
    def __init__(self, config_file=None):
        """
        Constructor

        :param config_file: iRODS configuration file
        :type config_file: str
        """
        self._configs = ConfigLoader.load_from_json(config_file)

        self._host = self._configs.get("irods_host")
        self._port = self._configs.get("irods_port")
        self._user = self._configs.get("irods_user")
        self._password = self._configs.get("irods_password")
        self._zone = self._configs.get("irods_zone")
        self._project_root = self._configs.get("irods_project_root")

    def download_data(self, data, save_dir=None):
        """
        Downloading data from iRODS

        :param data: iRODS collection/Dataset name in the iRODS zone
        :type data: str
        :param save_dir: path to the save directory
        :type save_dir: str
        :return:
        :rtype:
        """
        with iRODSSession(host=self._host,
                              port=self._port,
                              user=self._user,
                              password=self._password,
                              zone=self._zone) as session:
            dataset_path = self._project_root + '/' + data
            self._download_collection(session, dataset_path, save_dir=save_dir)

    def _download_collection(self, session, collection_path, save_dir):
        """
        Downloading an iRODS collection

        :param session: iRODS connection session
        :type session: object
        :param collection_path: collection path in the iRODS system
        :type collection_path: str
        :param save_dir: local path to the save directory
        :type save_dir: str
        :return:
        :rtype:
        """
        dataset = session.collections.get(collection_path)
        save_dir = os.path.join(save_dir, dataset.name)
        os.makedirs(save_dir, exist_ok=True)

        for dobj in (dataset.data_objects):
            session.data_objects.get(dobj.path, os.path.join(save_dir,dobj.name))

        if dataset.subcollections:
           for subcollection in dataset.subcollections:
               self._download_collection(session, subcollection.path, save_dir)
        else:
            return
