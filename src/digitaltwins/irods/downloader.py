import os
import os.path
from pathlib import Path

from irods.session import iRODSSession

from dotenv import load_dotenv
load_dotenv()


class Downloader(object):
    def __init__(self):
        self._host = os.getenv("IRODS_HOST")
        self._port = os.getenv("IRODS_PORT")
        self._user = os.getenv("IRODS_USER")
        self._password = os.getenv("IRODS_PASSWORD")
        self._zone = os.getenv("IRODS_ZONE")
        self._project_root = os.getenv("IRODS_PROJECT_ROOT")

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
