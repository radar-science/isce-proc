## Installation

### 1. Software installation

#### a. Install ISCE-2 and MintPy

[Here](https://github.com/yunjunz/conda_envs) is an example instruction to install `isce2` (release or development version) and `mintpy` (development version) using `conda`. For machines with GPU available, we recommend using the "option 3" there to install isce2 from source to leverage the GPU processing.

#### b. Install `isce-proc`

Download source code:

```bash
cd ~/tools
git clone https://github.com/radar-science/isce-proc.git
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

### 2. Account setup

Register the following accounts to download data from various sources.

#### a. ASF DAAC

Register for NASA's Alaska Satellite Facility Distributed Active Archive Center (ASF DAAC) to download SAR data.

#### b. Copernicus Data Space

Register for the Copernicus Data Space Ecosystem (CDSE) at https://dataspace.copernicus.eu/ to download Sentinel-1 orbit data.

#### c. Copernicus Climate Data Store

Register for the Copernicus Climate Data Store (CDS) at https://cds.climate.copernicus.eu/user/register to download ERA5 weather re-analysis data.
