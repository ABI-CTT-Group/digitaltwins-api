# Tutorial 1: Getting started with the 12 LABOURS DigitalTWINS platform

## Introduction
This tutorial shows how to get access to and interact with the 12 LABOURS DigitalTWINS Platform and its web portal.

## Definitions
- API - Application Programming Interface used to access the features or data of an application or service.
- CTT - ABI Clinical Translational Technologies Research Group

## Learning outcomes
In this tutorial, you will learn how to:
- install the platform's API.
- connect to the platform.
- access the platform's web portal.

## Installing the platform's API
We will connect to the DigitalTWINS platform programmatically using its Python API, which is called `digitaltwins`. It is designed to be used with the `sparc-me` Python tool, which is used for managing datasets.

### Pre-requisites 
- Python 3.9+. Tested on:
   - 3.9
- Operating system. Tested on:
  - Ubuntu 20.04
  - Windows 10
  - Mac 13.3, 13.5

### 1. **Setting up a virtual environment (optional but recommended)**

It is recommended to use a virtual environment instead of your system environment. Your integrated development environment (IDE) software e.g. (PyCharm, VisualStudio Code etc) provides the ability to create a Python virtual environment for new projects. The code below shows how to create a new Python virtual environment directly from the Linux or Mac terminal or from the Windows PowerShell (will be stored in a new folder named **venv** in the current working directory), and how to activate the virtual environment.

Linux and MacOS
```
python3 -m venv venv
source venv/bin/activate
```

Windows
```
python3 -m venv venv
venv\Scripts\activate
```
### 2. **Installing digitaltwins and sparc-me from PyPI**
```
pip install digitaltwins
pip install sparc-me
```

## Accessing your local eResearch storage drive
For security reasons, the CTT team have placed project specific documentation for connecting to your instance of the 12 LABOURS DigitalTWINS platform on your project-specific eResearch drive. Please see the [Workshop FAQ Section of the 12 LABOURS DigitalTWINS platform user documentation] to find the instructions for mounting your eResearch drive.

## Connecting to the platform

### 1. Open a terminal on your computer

- Windows users: Open Windows PowerShell.
- Linux or Mac users: Open a terminal.

### 2. Enter the following command to connect to your virtual machine (VM).

- Replace UPI with your University of Auckland UPI.
- Replace VM_ADDRESS with the VM address the virtual machine that has been assigned to your project (e.g. X@aucland.ac.nz). You can find the VM address for your VM in the `README.txt` file located in the root directory of your eResearch storage drive.

`ssh -L 3000:localhost:3000 -L 8000:localhost:8000 -L 80:localhost:80 -L 443:localhost:443 -L 1247:localhost:1247 UPI@VM_ADDRESS`

When prompted, enter your University of Auckland password and 2-factor authentication code separated by a colon ie `UOA_PASSWORD:TWO_FACTOR_AUTHENTICATION_CODE`. For security reasons, the password or text cursor may not show as you type in your password.

If successful, a command prompt will appear. Please leave this terminal running in the background.

### 3. Locating your platform API configuration file

A configuration file is required to programmatically interact with your instance of the platform. The path to this file needs to be specified when connecting to the platform using the `digitaltwins` Python API in Tutorials 2 and 5. The location of your project-specific configuration file can be found in your eResearch storage drive. **Please do not copy, move, or share the configuration file**.

##### Windows
`X:\DigitalTWINS\resources\latest\configs\configs.ini`
- please replace `X:` with the drive letter that you mounted your eResearch drive. 

##### Linux or MacOs
`/MOUNT_POINT/DigitalTWINS/resources/latest/configs/configs.ini`
- please replace `/MOUNT_POINT` with the location where you mounted your eResearch drive. 

### Troubleshooting
Sometimes you need to connect to VPN even if you are on campus (UoA IT ticket has been submitted and CeR are following up).

## Accessing the platform's web portal
Once you have connected to the platform, open https://localhost:3000 in a web browser to access the web portal for the 12 LABOURS DigitalTWINS platform. The data catalogue can be found from the `View data browswer` link on the `DATA & MODELS` page.

Please wait a moment for the datasets to load. If the datasets still do not load, then please reload the website.

## Accessing API Documentation
API documentation lists all the classes and methods available. This can be a useful reference when trying to understand input arguments of the classes and methods when using the `digitaltwins` and `sparc-me` Python tools.
- sparc-me API documentation TODO Add link
- digitaltwins API documentation TODO Add link

## Feedback
Once you have completed this tutorial, please complete [this survey](https://docs.google.com/forms/d/e/1FAIpQLSe-EsVz6ahz2FXFy906AZh68i50jRYnt3hQe-loc-1DaFWoFQ/viewform?usp=sf_link), which will allow us to improve this and future tutorials.

## Next steps
The [next tutorial](https://github.com/ABI-CTT-Group/digitaltwins-api/blob/main/tutorials/tutorial_2_exploring_and_downloading_platform_datasets.ipynb) will show how to explore and download datasets from the 12 LABOURS DigitalTWINS platform.