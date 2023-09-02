# 12 LABOURS DigitalTWINS API
A Python tool for interacting with the 12 Labours DigitalTWINS (Digital Translational Workflows for Integrating Systems) Platform

![Python 3](https://img.shields.io/badge/Python->=3.8-blue)
[![Contributors][contributors-shield]][contributors-url]
[![Stargazers][stars-shield]][stars-url]
[![GitHub issues-closed](https://img.shields.io/github/issues-closed/ABI-CTT-Group/digital-twin-platform.svg)](https://GitHub.com/ABI-CTT-Group/digital-twin-platform/issues?q=is%3Aissue+is%3Aclosed)
[![Issues][issues-shield]][issues-url]
[![apache License][license-shield]][license-url]
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)
<!--* [![DOI](https://zenodo.org/badge/XXXX.svg)](https://zenodo.org/badge/latestdoi/XXXXX) -->
[![PyPI version fury.io](https://badge.fury.io/py/digital-twin-platform.svg)](https://pypi.python.org/pypi/digtial-twin-platform/)

[contributors-shield]: https://img.shields.io/github/contributors/ABI-CTT-Group/digital-twin-platform.svg?style=flat-square
[contributors-url]: https://github.com/ABI-CTT-Group/digital-twin-platform/graphs/contributors
[stars-shield]: https://img.shields.io/github/stars/ABI-CTT-Group/digital-twin-platform.svg?style=flat-square
[stars-url]: https://github.com/ABI-CTT-Group/digital-twin-platform/stargazers
[issues-shield]: https://img.shields.io/github/issues/ABI-CTT-Group/digital-twin-platform.svg?style=flat-square
[issues-url]: https://github.com/ABI-CTT-Group/digital-twin-platform/issues
[license-shield]: https://img.shields.io/github/license/ABI-CTT-Group/digital-twin-platform.svg?style=flat-square
[license-url]: https://github.com/ABI-CTT-Group/digital-twin-platform/blob/master/LICENSE
[lines-of-code-shield]: https://img.shields.io/tokei/lines/github/ABI-CTT-Group/digital-twin-platform
[lines-of-code-url]: #

## Local Installation

1. Clone the repository:

```commandline
git clone https://github.com/ABI-CTT-Group/digital-twin-platform.git
```

2. Update your .bashrc file
add the path to the dtp module to your Python path environment variable. 
This can done by adding the following line to your ~/.bashrc file.
```
export PYTHONPATH=$PYTHONPATH:~/path/to/digital-twin-platform/repo/dtp
```
then, run
```commandline
source ~/.bashrc
```

3. Install Python dependencies using virtual environment
    
    3.1. Create a virtual environment
    
    ```commandline
    python3 -m venv venv/
    ```
   
    3.2. Activate the virtual environment
    
    ```commandline
    source venv/bin/activate
    ```
   
    3.3. Install the dependencies via requirements.txt
    
    ```commandline
    pip install -r requirements.txt
    ```
