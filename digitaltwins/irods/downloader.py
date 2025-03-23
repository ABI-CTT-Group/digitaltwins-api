import os.path
from pathlib import Path

from irods.session import iRODSSession

from ..utils.config_loader import ConfigLoader


class Downloader(object):
    def __init__(self, config_file):
        self._config_file = Path(config_file)
        self._configs = ConfigLoader.load_from_ini(config_file)["irods"]

        self._host = self._configs.get("irods_host")
        self._port = self._configs.get("irods_port")
        self._user = self._configs.get("irods_user")
        self._password = self._configs.get("irods_password")
        self._zone = self._configs.get("irods_zone")
        self._project_root = self._configs.get("irods_project_root")

    def download(self, collection, save_dir=None):
        """
        Downloading data from iRODS

        :param collection: iRODS collection. path relative to the project root
        :type collection: str
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
            collection_path = self._project_root + '/' + collection
            self._download_collection(session, collection_path, save_dir=save_dir)

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
        collection = session.collections.get(collection_path)
        save_dir = Path(save_dir)
        save_dir = save_dir.joinpath(collection.name)
        os.makedirs(save_dir, exist_ok=True)

        for dobj in (collection.data_objects):
            session.data_objects.get(dobj.path, os.path.join(save_dir,dobj.name))

        if collection.subcollections:
           for subcollection in collection.subcollections:
               self._download_collection(session, subcollection.path, save_dir)
        else:
            return


