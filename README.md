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

## Setting up the digital-twin-platform API

### Pre-requisites 
- [Git](https://git-scm.com/)
- Python 3.8+. Tested on:
   - 3.8
- Operating system. Tested on:
  - Ubuntu 18
   
### PyPI

Here is the [link](https://pypi.org/project/digital-twin-platform/) to the project on PyPI
```
pip install digital-twin-platform
```

### From source code

#### Downloading source code
Clone the source code repository from github, e.g.:
```
```commandline
git clone https://github.com/ABI-CTT-Group/digital-twin-platform.git
```

#### Installing dependencies

1. Setting up a virtual environment (optional but recommended). 
   In this step, we will create a virtual environment in a new folder named **venv**, 
   and activate the virtual environment.
   
   * Linux
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
   
   * Windows
   ```
   python3 -m venv venv
   venv\Scripts\activate
   ```
   
2. Installing dependencies via pip
    ```
    pip install -r requirements.txt
    ```
