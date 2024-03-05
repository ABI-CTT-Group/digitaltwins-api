from setuptools import setup, find_packages

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf8") ## UnicodeDecodeError when decoding the REAME file

setup(
    name="digitaltwins",
    version="0.3.13",
    description='A Python tool for interacting with the 12 Labours DigitalTWINS (Digital Translational Workflows for '
                'Integrating Systems) Platform',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/ABI-CTT-Group/digitaltwins-api',
    author="Thiranja Prasad Babarenda Gamage, Chinchien Lin, Linkun Gao, Jiali Xu, David Nickerson",
    email="psam012@aucklanduni.ac.nz, clin864@aucklanduni.ac.nz",
    license="Apache-2.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['./resources/**']},
    install_requires=[
        "gen3~=4.21.0",
        "python-irodsclient>=1.1.8",
        "pandas",
        "xlrd",
        "PyYAML",
        "openpyxl",
        "jsonschema",
        "dictionaryutils"
    ]
)
