import os

from dotenv import load_dotenv
load_dotenv()

from ..utils.config_loader import is_truthy

from ..airflow.workflow import Workflow as AirflowWorkflow


class Workflow(object):
    def __init__(self):
        self._airflow_enabled = is_truthy(os.getenv("AIRFLOW_ENABLED"))

        if self._airflow_enabled:
            self._airflow_workflow = AirflowWorkflow()


    def run(self, assay_id):
        """


        :param assay_id: assay id on Seek
        :type assay_id: int
        :return:
        :rtype:
        """

        response, workflow_monitor_url = self._airflow_workflow.run(assay_id)

        return response, workflow_monitor_url
