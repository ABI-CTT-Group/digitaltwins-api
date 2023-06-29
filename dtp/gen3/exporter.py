from gen3.submission import Gen3Submission
import json

class Exporter(object):
    def __init__(self, auth):
        self._auth = auth
        self._exporter = Gen3Submission(self._auth)

    def export_node(self, program, project, node_type, fileformat, filename=None):
        output = self._exporter.export_node(program, project, node_type, fileformat, filename)
        return output

    def export_record(self, program, project, uuid, fileformat, filename=None):
        output = self._exporter.export_record(program, project, uuid, fileformat, filename)
        return output

    def save(self, data, fileformat, path):
        # Export data as either 'json' or 'tsv'
        if fileformat == "json":
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
        elif fileformat == "tsv":
            raise NotImplementedError("File format not supported")
        else:
            raise NotImplementedError("File format not supported")



