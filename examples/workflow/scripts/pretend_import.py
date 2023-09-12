import os
import shutil

import workflow_manager as wm
from digitaltwins.irods.irods import IRODS

script_id = 'pretend_import'
run_program = 'python3'
run_script = 'pretend_import.py'


def init(process):
    path = process.params.get('path')
    process.set_param('path', os.path.abspath(path))
    return process


def run(process):
    print("Args: " + str(process.params))
    dataset = process.params.get('dataset')
    data_type = process.params.get('data_type')
    subject = process.params.get('subject')
    sample = process.params.get('sample')

    workspace = process.get_workspace('pretend_import', True)
    print("Workspace: " + str(workspace.path()))

    irods = IRODS()
    data = dataset + '/' + data_type + '/' + subject + '/' + sample
    irods.download(collection_name=data, save_dir=workspace)

    process.completed()


def import_scans(source, dest):
    print("Source:" + str(source))
    print("Destination:" + str(dest))

    if os.path.isdir(source):
        files = os.listdir(source)
        paths = list()
        for file in files:
            path = os.path.join(source, file)
            if os.path.exists(path):
                paths.append(os.path.join(source, file))
            else:
                return False, 'Source file not found %s' % path

        print("list of files:" + str(paths))

        for path in paths:
            shutil.copy(path, dest)
    else:
        shutil.copy(source, dest)

    return True, ''


if __name__ == "__main__":
    run(wm.get_project_process())
