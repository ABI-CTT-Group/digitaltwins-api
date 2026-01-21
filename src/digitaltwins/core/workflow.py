import os

from dotenv import load_dotenv

from ..utils.config_loader import ConfigLoader, is_truthy

from ..airflow.workflow import Workflow as AirflowWorkflow

load_dotenv()


class Workflow(object):
    def __init__(self, config_file=None):
        if not config_file and os.getenv("CONFIG_FILE_PATH"):
            config_file = os.getenv("CONFIG_FILE_PATH")

        if config_file:
            self._configs = ConfigLoader.load_from_ini(config_file)
            self._airflow_enabled = self._configs.getboolean("airflow", "enabled")
        else:
            self._airflow_enabled = is_truthy(os.getenv("AIRFLOW_ENABLED"))

        if self._airflow_enabled:
            self._airflow_workflow = AirflowWorkflow(config_file)


    def run(self, assay_id):
        """


        :param assay_id: assay id on Seek
        :type assay_id: int
        :return:
        :rtype:
        """

        response, workflow_monitor_url = self._airflow_workflow.run(assay_id)

        return response, workflow_monitor_url
