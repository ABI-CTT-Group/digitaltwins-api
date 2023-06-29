from gen3.submission import Gen3Submission


class Queryer(object):
    def __init__(self, auth):
        self._auth = auth
        self._queryer = Gen3Submission(self._auth)

    def graphql_query(self, query_string, variables=None):
        response = self._queryer.query(query_string, variables).get("data")

        return response

    def get_programs(self):
        response = self._queryer.get_programs()

        programs = list()
        for resp in response.get("links"):
            program = resp.split('/')[-1]
            programs.append(program)

        return programs

    def get_projects(self, program):
        response = self._queryer.get_projects(program)

        projects = list()
        for resp in response.get("links"):
            project = resp.split('/')[-1]
            projects.append(project)

        return projects

    def get_node_records(self, node, program, project):
        response = self._queryer.export_node(program, project, node, "json")
        data = response.get("data")
        return data