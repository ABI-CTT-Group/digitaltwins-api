# 12 LABOURS DigitalTWINS API
A Python tool for interacting with the 12 LABOURS DigitalTWINS (Digital Translational Workflows for Integrating Systems) platform

![Python 3](https://img.shields.io/badge/Python->=3.9-blue)
[![Contributors][contributors-shield]][contributors-url]
[![Stargazers][stars-shield]][stars-url]
[![GitHub issues-closed](https://img.shields.io/github/issues-closed/ABI-CTT-Group/digitaltwins-api.svg)](https://GitHub.com/ABI-CTT-Group/digitaltwins-api/issues?q=is%3Aissue+is%3Aclosed)
[![apache License][license-shield]][license-url]
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)
[![PyPI version fury.io](https://badge.fury.io/py/digitaltwins.svg)](https://pypi.python.org/pypi/digitaltwins)
<!--* [![Issues][issues-shield]][issues-url] -->
<!--* [![DOI](https://zenodo.org/badge/XXXX.svg)](https://zenodo.org/badge/latestdoi/XXXXX) -->

[contributors-shield]: https://img.shields.io/github/contributors/ABI-CTT-Group/digitaltwins-api.svg?style=flat-square
[contributors-url]: https://github.com/ABI-CTT-Group/digitaltwins-api/graphs/contributors
[stars-shield]: https://img.shields.io/github/stars/ABI-CTT-Group/digitaltwins-api.svg?style=flat-square
[stars-url]: https://github.com/ABI-CTT-Group/digitaltwins-api/stargazers
[issues-shield]: https://img.shields.io/github/issues/ABI-CTT-Group/digitaltwins-api.svg?style=flat-square
[issues-url]: https://github.com/ABI-CTT-Group/digitaltwins-api/issues
[license-shield]: https://img.shields.io/github/license/ABI-CTT-Group/digitaltwins-api.svg?style=flat-square
[license-url]: https://github.com/ABI-CTT-Group/digitaltwins-api/blob/master/LICENSE
[lines-of-code-shield]: https://img.shields.io/tokei/lines/github/ABI-CTT-Group/digitaltwins-api
[lines-of-code-url]: #

## Table of contents
* [Introduction](#introduction)
* [Setting up the DigitalTWINS platform API](#setting-up-the-digitaltwins-platform-API)
* [Using the DigitalTWINS Platform API](#using-the-digitalwins-platform-api)
* [Reporting issues](#reporting-issues)
* [Contributing](#contributing)
* [License](#license)
* [Team](#team)
* [Funding](#funding)
* [Acknowledgements](#acknowledgements)

<!--* * [The problem](#the-problem) -->
<!--* * [Our solution - XXXXXX](#our-solution---XXXXX) -->
<!--* * [Impact and vision](#impact-and-vision) -->
<!--* * [Future developments](#future-developments) -->
<!--* * [Cite us](#cite-us) -->
<!--* * [FAIR practices](#fair-practices) -->

## Introduction
The development of novel medical diagnosis and treatment approaches requires understanding how diseases that operate at the molecular scale influence physiological function at the scale of cells, tissues, organs, and organ systems. The Auckland Bioengineering Institute (ABI) led **Physiome Project aims to establish an integrative “systems medicine” framework based on personalised computational modelling** to link information encoded in the genome to organism-wide physiological function and dysfunction in disease. The **[12 LABOURS project](https://www.auckland.ac.nz/en/abi/our-research/research-groups-themes/12-Labours.html) aims to extend and apply the developments of the Physiome Project to clinical and home-based healthcare applications**.

As part of the 12 LABOURS project, we are **building a DigitalTWINS platform to provide common infrastructure**:
* A **data catalogue** that describes what data is available, what it can be used for, and how to request it.
* A **harmonised data repository** that provides access control to primary and derived data (waveforms, medical images, electronic health records, measurements from remote monitoring devices such as wearables and implantables etc), tools, and workflows that are stored with a standardised dataset description.
* **Describe computational physiology workflows in a standardised language** (including workflows for knowledge discovery, clinical translation, or education, etc), and **run and monitor their progress**.
* **Securely access electronic health records from health systems** (WIP).
* **Securely link data from remote monitoring devices** such as wearables and implantables into computational physiology workflows.
* A **web portal** to enable different researchers, including researchers, clinicians, patients, industry, and the public, to interact with the platform.
* **Guidelines for data management**.
* **Guidelines for clinical translation of computational physiology workflows** and digital twins via commercialisation
* **Unified ethics application templates** that aim to maximise data reusability and linking to enable our vision for creating integrated and personalised digital twins.

Please see the [User Documentation for the DigitalTWINS platform](https://docs.google.com/document/d/10dQ0Cyq0NQ1JlxPYCVtGCIY2umZrYzhAltsyRd9QhgY/edit) for more information in the current capabilities of the platform.

These efforts are aimed at **supporting an ecosystem** to:
* **Make research outcomes FAIR** (Findable, Accessible, Interoperable, and Reusable).
* Enable **reproducible science**.
* **Meet data sovereignty requirements**.
* **Support clinical translation via commercialisation** by enabling researchers to conduct clinical trials more efficiently to demonstrate the efficacy of their computational physiology workflows. 
* Provide a **foundation for integrating research developments** across different research groups for assembling more comprehensive computational physiology/digital twin workflows.

**If you find the DigitalTWINS platform useful, please add a GitHub Star to support developments!**

## Storing datasets in the DigitalTWINS platform
Data within the DigitalTWINS platform is stored in the SPARC Dataset Structure (SDS). More information about SDS datasets can be found on the [SPARC project's documentation](https://docs.sparc.science/docs/overview-of-sparc-dataset-format). The use of SDS datasets in the 12 LABOURS DigitaTWINS platform is described in the following [presentation](https://docs.google.com/file/d/1zZ3-C17lPIgtRp6bnkSwvKacaTA66GVR/edit?usp=docslist_api&filetype=mspresentation).

## Installing the DigitalTWINS platform API
This code repository provides a Python API tool to enable users to connect to and interact with the DigitalTWINS platform programmatically.

### Pre-requisites
- Python 3.9+. Tested on:
   - 3.9
- Operating system. Tested on:
  - Ubuntu 20.04
  - Windows 10
  - Mac 13.3, 13.5

### User installation
The DigitalTWINS platform Python API is called `digitaltwins`. It is designed to be used with the `sparc-me` python tool.

1. **Setting up a virtual environment (optional but recommended)**
   
   It is recommended to use a virtual environment instead of your system environment. Your integrated development environment (IDE) software e.g. (PyCharm, VisualStudio Code etc) provides the ability to create a Python virtual environment for new projects. The code below shows how to create a new Python virtual environment directly from the Linux or Mac terminal or from the Windows PowerShell (will be stored in a new folder named **venv** in the current working directory), and how to activate the virtual environment.
   
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
2. **Installing digitaltwins and sparc-me from PyPI**
   ```
   pip install digitaltwins
   pip install sparc-me
   ```

### Developer installation

1. **Downloading source code**
   
   Clone the source code repository from github, e.g.:
   
   ```commandline
   git clone https://github.com/ABI-CTT-Group/digitaltwins-api.git
   ```
   
2. **Setting up a virtual environment (optional but recommended)**
   
   See step 1 in the user installation instructions. 
   
3. **Installing dependencies via pip**
   
   ```
   pip install -r requirements.txt
   ```
   
## Using the DigitalTWINS platform

Please see the [documentation for workshop 1](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/workshop_1_describing_and_storing_data.md), which describes how to use the 12 LABOURS DigitalTWINS platform and its API.

## Reporting issues 
To report an issue or suggest a new feature, please use the [issues page](https://github.com/ABI-CTT-Group/digitaltwins-api/issues). Issue templates are provided to allow users to report bugs, and documentation or feature requests. Please check existing issues before submitting a new one.

## Contributing
Fork this repository and submit a pull request to contribute. Before doing so, please read our [Code of Conduct](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/master/CODE_OF_CONDUCT.md) and [Contributing Guidelines](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/master/CONTRIBUTING.md). Pull request templates are provided to help developers describe their contribution, mention the issues related to the pull request, and describe their testing environment. 

## License
The DigitalTWINS platform API is fully open source and distributed under the very permissive Apache License 2.0. See [LICENSE](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/LICENSE) for more information.

## Team
- Chinchien Lin (12L, CTT, BBRG)
- Linkun Gao (12L, CTT, BBRG)
- Jiali Xu (12L, CTT)
- David Yu (12L portal)
- Frances Feng (12L portal)
- Alan Wu (12L portal)
- David Nickerson (12L, SPARC DRC, CTT)
- Thiranja Prasad Babarenda Gamage (12L, CTT, BBRG)

## Funding
This software was funded by the [New Zealand Ministry of Business Innovation and Employment’s Catalyst: Strategic fund](https://www.mbie.govt.nz/science-and-technology/science-and-innovation/funding-information-and-opportunities/investment-funds/catalyst-fund/funded-projects/catalyst-strategic-auckland-bioengineering-institute-12-labours-project/). This research is also supported by the use of the Nectar Research Cloud, a collaborative Australian research platform supported by the National Collaborative Research Infrastructure Strategy-funded ARDC.

## Acknowledgements
We gratefully acknowledge the valuable contributions from:
- University of Auckland
  - Auckland Bioengineering Institute (ABI) Clinical Translational Technologies Group (CTT)
  - ABI 12 LABOURS project
  - ABI Breast Biomechanics Research Group (BBRG)
  - Infrastructure and technical support from the Centre for eResearch (including Anita Kean)
- New Zealand eScience Infrastructure (NeSI)
  - Nathalie Giraudon, Claire Rye, Jun Huh, and Nick Jones
- Gen3 team at the Centre for Translational Data Science at the University of Chicago
- Members of the SPARC Data and Resource Center (DRC).

<img src='https://raw.githubusercontent.com/ABI-CTT-Group/digitaltwins-api/main/docs/acknowledgements.jpg' width='500' alt="acknowledgements.jpg">
