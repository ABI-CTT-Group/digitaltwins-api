from pathlib import Path

from digitaltwins import Workflow

if __name__ == '__main__':
    config_file = Path(r"/path/to/your/config/file")
    assay_id = 2

    workflow = Workflow(config_file)
    response, workflow_monitor_url = workflow.run(assay_id=assay_id)

    print("response.status_code:" + str(response.status_code))
    print("Monitoring workflow on: " + workflow_monitor_url)
