# digital-twin-platform

![Python 3](https://img.shields.io/badge/Python->=3.8-blue)


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
