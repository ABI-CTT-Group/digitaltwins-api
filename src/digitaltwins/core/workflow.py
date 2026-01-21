from pathlib import Path

from ..utils.config_loader import ConfigLoader

from ..airflow.workflow import Workflow as AirflowWorkflow


class Workflow(object):
    def __init__(self, config_file):
        self._config_file = Path(config_file)
        self._configs = ConfigLoader.load_from_ini(config_file)

        if self._configs.getboolean("airflow", "enabled"):
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
