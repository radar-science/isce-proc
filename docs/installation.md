## Installation

#### a. Install ISCE-2 and MintPy

[Here](https://github.com/yunjunz/conda_envs) is an example instruction to install `isce2` (release or development version) and `mintpy` (development version) using `conda`. For machines with GPU available, we recommend using the "option 3" there to install isce2 from source to leverage the GPU processing.

#### b. Install `isce-proc`

Download source code:

```bash
cd ~/tools
git clone git@github.com:radar-science/isce-proc.git
```

Add the following to your source file, such as `.bashrc` or `.bash_profile` for _bash_ users:

```bash
##-------------- isce-proc ----------------------------##
export ISCE_PROC_HOME=~/tools/isce-proc
export PYTHONPATH=${PYTHONPATH}:${ISCE_PROC_HOME}/src
export PATH=${PATH}:${ISCE_PROC_HOME}/src/isce_proc
```

#### c. Test the installation

```bash
topsApp.py -h
smallbaselineApp.py -h
run_isce_stack.py -h
```
