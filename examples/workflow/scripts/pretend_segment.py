import argparse
import os
import time

import workflow_manager as wm

script_id = 'pretend_segment'
run_program = 'python3'
run_script = 'pretend_segment.py'
files = ['pretend_segment.py']
depends_on = ['pretend_import']
cores = 2
time_limit = 4


def run(process):
    source_workspace = process.parent.get_workspace('pretend_import')
    dest_workspace = process.get_workspace('pretend_segment', True)

    print("Source workspace: " + str(source_workspace.path()))
    print("Destination workspace: " + str(dest_workspace.path()))

    sample = os.listdir(source_workspace)[0]
    segment(sample, dest_workspace)

    process.completed()


def segment(sample, dest):
    filename = "mask.txt"
    dest = os.path.join(dest, filename)
    fp = open(dest, 'w')
    fp.write(len(sample))
    fp.close()
    time.sleep(3)
    

if __name__ == "__main__":
    run(wm.get_project_process())
