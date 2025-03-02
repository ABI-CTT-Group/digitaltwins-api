from pathlib import Path

from ..utils.config_loader import ConfigLoader

from digitaltwins import Querier

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
        # get assay params
        querier = Querier(self._config_file)
        assay = querier.get_assay(assay_id, get_params=True)

        response, workflow_monitor_url = self._airflow_workflow.run(assay)

        return response, workflow_monitor_url
