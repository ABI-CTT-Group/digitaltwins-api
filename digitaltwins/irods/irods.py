import os
from pathlib import Path

from irods.session import iRODSSession

class IRODS(object):
    """
    Class for interacting with iRODS server
    """
    def __init__(self, configs):
        """
        Constructor
        """

        self._configs = configs["irods"]
        self._host = self._configs.get("irods_host")
        self._port = self._configs.get("irods_port")
        self._user = self._configs.get("irods_user")
        self._password = self._configs.get("irods_password")
        self._zone = self._configs.get("irods_zone")
        self._project_root = self._configs.get("irods_project_root")

    def upload(self, local_dataset_dir):
        with iRODSSession(host=self._host,
                          port=self._port,
                          user=self._user,
                          password=self._password,
                          zone=self._zone) as session:

            local_dataset_dir = Path(local_dataset_dir)

            self._create_collections(session, local_dataset_dir)

            try:
                # Walk through the local directory and upload its contents to iRODS
                for root, dirs, files in os.walk(str(local_dataset_dir)):
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        filename = Path(local_file_path).name

                        sub = str(root).replace(str(local_dataset_dir.parent), '')
                        sub = sub.replace("\\", "/")
                        collection_path = self._project_root + sub
                        irods_file_path = collection_path + "/" + filename

                        # Upload the file to iRODS
                        session.data_objects.put(local_file_path, irods_file_path, force=True)

                        print(f"File uploaded: '{local_file_path}'")
            except Exception as e:
                print(f"Error uploading local directory: {e}")

    def _create_collections(self, session, local_dataset_dir):
        for item in local_dataset_dir.rglob("*"):
            if item.is_dir():
                sub = str(item).replace(str(local_dataset_dir.parent), '')
                sub = sub.replace("\\", "/")
                collection_path = self._project_root + sub

                if session.collections.exists(collection_path):
                    continue
                else:
                    session.collections.create(collection_path, recurse=True)

    def delete(self, collection_name):
        with iRODSSession(host=self._host,
                          port=self._port,
                          user=self._user,
                          password=self._password,
                          zone=self._zone) as session:
            collection_path = self._project_root + '/' + collection_name

            if session.collections.exists(collection_path):
                session.collections.remove(collection_path, recurse=True)
