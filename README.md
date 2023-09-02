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

## Table of contents
* [Introduction](#introduction)
<!--* * [The problem](#the-problem) -->
<!--* * [Our solution - XXXXXX](#our-solution---XXXXX) -->
<!--* * [Impact and vision](#impact-and-vision) -->
<!--* * [Future developments](#future-developments) -->
* [Setting up the digital twin platform API](#setting-up-the-digital-twin-platform-API)
<!--* * [Using XXXX](#using-XXXX) -->
* [Reporting issues](#reporting-issues)
* [Contributing](#contributing)
<!--* * [Cite us](#cite-us) -->
<!--* * [FAIR practices](#fair-practices) -->
* [License](#license)
<!--* * * [Team](#team) -->
<!--* * * [Acknowledgements](#acknowledgements) -->

## Introduction
The development of novel medical diagnosis and treatment approaches requires understanding how diseases that operate at the molecular scale influence physiological function at the scale of cells, tissues, organs, and organ systems. The Auckland Bioengineering Institute (ABI) led Physiome Project aims to establish an integrative “systems medicine” framework based on personalised computational modelling to link information that is encoded in the genome to organism-wide physiological function and dysfunction in disease. The 12 Labours project aims to extend and apply the developments of the Physiome Project to clinical and home-based healthcare applications.

**If you find sparc-flow useful, please add a GitHub Star to support developments!**

## Setting up the digital twin platform API

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
    
## Reporting issues 
To report an issue or suggest a new feature, please use the [issues page](https://github.com/ABI-CTT-Group/digital-twin-platform/issues). Issue templates are provided to allow users to report bugs, and documentation or feature requests. Please check existing issues before submitting a new one.

## Contributing
Fork this repository and submit a pull request to contribute. Before doing so, please read our [Code of Conduct](https://github.com/ABI-CTT-Group/digital-twin-platform/blob/master/CODE_OF_CONDUCT.md) and [Contributing Guidelines](https://github.com/ABI-CTT-Group/digital-twin-platform/blob/master/CONTRIBUTING.md). Pull request templates are provided to help guide developers in describing their contribution, mentioning the issues related to the pull request and describing their testing environment. 

## License
sparc-flow is fully open source and distributed under the very permissive Apache License 2.0. See [LICENSE](https://github.com/ABI-CTT-Group/digital-twin-platform/blob/main/LICENSE) for more information.
