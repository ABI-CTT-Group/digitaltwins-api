import os
import pymongo
import shutil

import workflow_manager as wm


def delete_duplicate(project_name, root):
    myclient = pymongo.MongoClient('localhost', 27017)
    if project_name in myclient.list_database_names():
        print('DROP %s database' % project_name)
        myclient.drop_database(project_name)
    if os.path.exists(root):
        print('DELETE %s directory' % root)
        shutil.rmtree(root)


def setup_workflow(project_name, root):
    os.makedirs(root, exist_ok=True)

    project = wm.create_project(project_name, root_dir=root)
    project.import_script('scripts/pretend_import.py')
    project.import_script('scripts/pretend_segment.py')
    return project


if __name__ == '__main__':
    project_name = 'example_project'
    root = './logs/example_project'

    delete_duplicate(project_name, root)

    project = setup_workflow(project_name, root)

    script = project.script('pretend_import')
    args = {"dataset": "dataset-12L_1-version-1",
            "data_type": "primary",
            "subject": "sub-1.3.6.1.4.1.14519.5.2.1.186051521067863971269584893740842397538",
            "sample": "sam-1.3.6.1.4.1.14519.5.2.1.175414966301645518238419021688341658582"}
    script.run(args)

    wm.project.start_process_monitor(project_name, minutes_alive=3, sleep_time=3, total_cores=2)
