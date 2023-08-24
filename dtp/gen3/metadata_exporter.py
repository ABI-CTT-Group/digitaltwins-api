from gen3.submission import Gen3Submission
import json


class MetadataExporter(object):
    """
    Class for exporting Gen3 metadata
    """
    def __init__(self, auth):
        """
        Constructor

        :param auth: Gen3 authentication object created by the Auth class
        :type auth: object
        """
        self._auth = auth
        self._exporter = Gen3Submission(self._auth)

    def export_node(self, program, project, node_type, fileformat, filename=None):
        """
        Exporting all records in a single Gen3 node

        :param program: Program name
        :type program: str
        :param project: Project
        :type project: str
        :param node_type: Node name
        :type node_type: str
        :param fileformat: Exported file format (json or tsv)
        :type fileformat: str
        :param filename: Exported filename
        :type filename: str
        :return: List of records (metadata) in dictionary format
        :rtype: list
        """
        output = self._exporter.export_node(program, project, node_type, fileformat, filename)
        data = json.loads(output).get("data")
        return data

    def export_record(self, program, project, uuid, fileformat, filename=None):
        """
        Exporting the metadata in a single record

        :param program: Program name
        :type program: str
        :param project: Project
        :type project: str
        :param uuid: Record UUID
        :type uuid: str
        :param fileformat: Exported file format (json or tsv)
        :type fileformat: str
        :param filename: Exported filename
        :type filename: str
        :return: Metadata in a single record
        :rtype: dict
        """
        output = self._exporter.export_record(program, project, uuid, fileformat, filename)
        data = json.loads(output)[0]
        return data

    def save(self, data, fileformat, path):
        """
        Saving the metadata (dict) in json format

        :param data: metadata
        :type data: dict
        :param fileformat: file format (currently only json)
        :type fileformat: str
        :param path: Path the save file
        :type path: str
        :return:
        :rtype:
        """
        # Export data as either 'json' or 'tsv'
        if fileformat == "json":
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
        elif fileformat == "tsv":
            raise NotImplementedError("File format not supported")
        else:
            raise NotImplementedError("File format not supported")



