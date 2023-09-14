# 12 LABOURS DigitalTWINS API
A Python tool for interacting with the 12 Labours DigitalTWINS (Digital Translational Workflows for Integrating Systems) Platform

![Python 3](https://img.shields.io/badge/Python->=3.8-blue)
[![Contributors][contributors-shield]][contributors-url]
[![Stargazers][stars-shield]][stars-url]
[![GitHub issues-closed](https://img.shields.io/github/issues-closed/ABI-CTT-Group/digitaltwins-api.svg)](https://GitHub.com/ABI-CTT-Group/digitaltwins-api/issues?q=is%3Aissue+is%3Aclosed)
[![Issues][issues-shield]][issues-url]
[![apache License][license-shield]][license-url]
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)
<!--* [![DOI](https://zenodo.org/badge/XXXX.svg)](https://zenodo.org/badge/latestdoi/XXXXX) -->
[![PyPI version fury.io](https://badge.fury.io/py/digitaltwins-api.svg)](https://pypi.python.org/pypi/digitaltwins-api/)

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
<!--* * [The problem](#the-problem) -->
<!--* * [Our solution - XXXXXX](#our-solution---XXXXX) -->
<!--* * [Impact and vision](#impact-and-vision) -->
<!--* * [Future developments](#future-developments) -->
* [Setting up the DigitalTWINS platform API](#setting-up-the-digitaltwins-platform-API)
* [Using the DigitalTWINS Platform API](#using-the-digitalwins-platform-api)
* [Reporting issues](#reporting-issues)
* [Contributing](#contributing)
<!--* * [Cite us](#cite-us) -->
<!--* * [FAIR practices](#fair-practices) -->
* [License](#license)
<!--* * * [Team](#team) -->
<!--* * * [Acknowledgements](#acknowledgements) -->

## Introduction
The development of novel medical diagnosis and treatment approaches requires understanding how diseases that operate at the molecular scale influence physiological function at the scale of cells, tissues, organs, and organ systems. The Auckland Bioengineering Institute (ABI) led **Physiome Project aims to establish an integrative “systems medicine” framework based on personalised computational modelling** to link information encoded in the genome to organism-wide physiological function and dysfunction in disease. The **[12 LABOURS project](https://www.auckland.ac.nz/en/abi/our-research/research-groups-themes/12-Labours.html) aims to extend and apply the developments of the Physiome Project to clinical and home-based healthcare applications**.

As part of the 12 LABOURS project, we are **building a DigitalTWINS Platform to provide common infrastructure**:
* A **data catalogue** that describes what data is available, what it can be used for, and how to request it.
* A **harmonised data repository** that provides access control to primary and derived data (waveforms, medical images, electronic health records, measurements from remote monitoring devices such as wearables and implantables etc), tools, and workflows that are stored with a standardised dataset description.
* **Describe computational physiology workfkows in a standardised language** (including workflows for knowledge discovery, clinical translation, or eductation, etc), and **run and monitor their progress**.
* **Securely access electronic health records from health systems** (WIP).
* **Securely link data from remote monitoring devices** such as wearables and implantables into computational physiology workflows.
* A **web-portal** to enable different researchers, including researchers, clinicians, patients, industry, and the public to interact with the platform.
* **Guidelines for data management**.
* **Guidelines for clinical translation of computational physiology workflows** and digital twins via commercialisation
* **Unified ethics application templates** that aim to maxmise data reuseablity and linking to enable our vision for creating integrated and personalised digital twins.

Please see the [User Documentation for the DigitalTWINS Platform](https://docs.google.com/document/d/10dQ0Cyq0NQ1JlxPYCVtGCIY2umZrYzhAltsyRd9QhgY/edit) for more information in the current capabilities of the platform.

These efforts are aimed at **supporting an ecosystem** to:
* **Make research outcomes FAIR** (Findable, Accessible, Interoperable, and Reuseable).
* Enable **reproducible science**.
* **Meet data sovereignty requirements**.
* **Support clinical translation via commercialisation** by enabling researchers to conduct clinical trials more effcienty to demonstrate the efficacy of their computational physiology workflows. 
* Provide a **foundation for integrating research developements** across different research groups for assembling more comprehensive computational physiology/digital twin workflows.

This code respository provides a python API tool to enable users to programatically connect to and interact with the DigitalTWINS Platform.

**If you find the DigitalTWINS Platform useful, please add a GitHub Star to support developments!**

## Setting up the DigitalTWINS Platform API

### Pre-requisites 
- [Git](https://git-scm.com/)
- Python 3.9+. Tested on:
   - 3.9
- Operating system. Tested on:
  - Ubuntu 18.04

### Creating a python environment
It is recommended to use a virtual environment instead of your system environment. In this step, we will create a virtual environment in a new folder named **venv**, and activate the virtual environment.
   
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

### User installation
Here is the [link](https://pypi.org/project/digitaltwins/) to the project on PyPI.
```
pip install digitaltwins
```
You also need to install the digitaltwins package, which is a Python tool for interacting with the 12 Labours DigitalTWINS (Digital Translational Workflows for Integrating Systems) Platform.
```
pip install sparc-me
```

### Developer installation

#### Downloading source code
Clone the source code repository from github, e.g.:

```commandline
git clone https://github.com/ABI-CTT-Group/digitaltwins-api.git
```

#### Installing dependencies

1. Setting up a virtual environment (optional but recommended). 
     
2. Installing dependencies via pip
```
pip install -r requirements.txt
```
    
## Using the DigitalTWINS Platform API

### Running tutorials

Guided Jupyter Notebook tutorials have been developed describing how to use the DigitalTWINS Platform API in different scenarios:

<table>
<thead>
  <tr>
    <th> Tutorial</th>
    <th> Description</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td><a href="https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_1_getting_started.ipynb">
    1
    </a></td>
    <td> Getting started with the DigitalTWINS Platform (including getting access to the API).</td>
  </tr>
  <tr>
    <td><a href="https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_2_create_datasets_and_description.ipynb">
    2
    </a></td>
    <td> Creating and describing datasets in a standardised format (SPARC Dataset Structure).</td>
  </tr>
  <tr>
    <td><a href="https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_3_submit_datasets.ipynb">
    3
    </a></td>
    <td> Submitting datasets to the platform.</td>
  </tr>
  <tr>
    <td><a href="https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_7_delete_datasets.ipynb">
    4
    </a></td>
    <td> Deleting existing datasets in the platform.</td>
  </tr> 
  <tr>
    <td><a href="https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_5_query_existing_datasets.ipynb">
    5
    </a></td>
    <td> Accessing metadata for existing datasets in the platform.</td>
  </tr>
  <tr>
    <td><a href="https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_6_download_existing_datasets.ipynb">
    6
    </a></td>
    <td> Downloading existing datasets in the platform.</td>
  </tr>   
  <tr>
    <td><a href="https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_4_update_existing_datasets.ipynb">
    7
    </td>
    <td> Updating existing datasets in the platform (version controlling datasets).</td>
  </tr>
</tbody>
</table>
<p align="center">
</p>
<br/>

## Reporting issues 
To report an issue or suggest a new feature, please use the [issues page](https://github.com/ABI-CTT-Group/digitaltwins-api/issues). Issue templates are provided to allow users to report bugs, and documentation or feature requests. Please check existing issues before submitting a new one.

## Contributing
Fork this repository and submit a pull request to contribute. Before doing so, please read our [Code of Conduct](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/master/CODE_OF_CONDUCT.md) and [Contributing Guidelines](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/master/CONTRIBUTING.md). Pull request templates are provided to help guide developers in describing their contribution, mentioning the issues related to the pull request and describing their testing environment. 

## License
The DigitalTWINS Platform API is fully open source and distributed under the very permissive Apache License 2.0. See [LICENSE](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/LICENSE) for more information.
