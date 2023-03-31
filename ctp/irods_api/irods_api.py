from dotenv import load_dotenv
from pathlib import Path
import os

from irods.session import iRODSSession

env_file = Path('../../.env')
load_dotenv(dotenv_path=env_file)


class IRODSAPI(object):
    def __init__(self):
        self._url = os.getenv('IRODS_URL')
        self._host = os.getenv("IRODS_HOST")
        self._port = os.getenv("IRODS_PORT")
        self._user = os.getenv("IRODS_USER")
        self._password = os.getenv("IRODS_PASSWORD")
        self._zone = os.getenv("IRODS_ZONE")
        self._project_root = os.getenv("IRODS_COLLECTION_ROOT")

    def download_dataset(self, dataset, save_dir=None):
        with iRODSSession(host=self._host,
                              port=self._port,
                              user=self._user,
                              password=self._password,
                              zone=self._zone) as session:
            dataset_path = self._project_root + '/' + dataset
            self._download_collection(session, dataset_path, save_dir=save_dir)

    def _download_collection(self, session, collection_path, save_dir):
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
