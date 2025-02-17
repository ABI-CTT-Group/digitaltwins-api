from pathlib import Path

from digitaltwins import Querier

if __name__ == '__main__':
    config_file = Path(r"/path/to/configs.ini")

    querier = Querier(config_file)

    print("programs:")
    programs = querier.get_programs()
    print(programs)

    print("program 3:")
    program_id = 3
    program = querier.get_program(program_id)
    print(program)

    print("projects:")
    projects = querier.get_projects()
    print(projects)

    print("project 4:")
    project_id = 4
    project = querier.get_project(project_id)
    print(project)

    print("investigations:")
    investigations = querier.get_investigations()
    print(investigations)

    print("investigation 2:")
    investigation_id = 2
    investigation = querier.get_project(investigation_id)
    print(investigation)

    print("studies:")
    studies = querier.get_investigations()
    print(studies)

    print("study 2:")
    study_id = 2
    study = querier.get_study(study_id)
    print(study)

    print("assays:")
    assays = querier.get_assays()
    print(assays)

    print("assay 2:")
    assay_id = 2
    assay = querier.get_assay(assay_id)
    print(assay)

    print("SOPs:")
    sops = querier.get_sops()
    print(sops)

    print("SOP 1:")
    sop_id = 1
    sop = querier.get_sop(sop_id)
    print(sop)

    # Object dependencies can be collected by get_dependencies(data, target). e.g.
    # EX 1
    print("projects in program: {program_id}".format(program_id=program_id))
    program = querier.get_program(program_id=program_id)
    projects = querier.get_dependencies(program, "projects")
    print(projects)
    # EX 2
    print("investigations in projects: {project_id}".format(project_id=project_id))
    project = querier.get_project(project_id=project_id)
    investigations = querier.get_dependencies(project, "investigations")
    print(investigations)


