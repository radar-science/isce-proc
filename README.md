## SAR / InSAR Processing with ISCE2

This repository contains some code and notes to facilitate the SAR and InSAR processing using [ISCE2](https://github.com/isce-framework/isce2).

### 1. Installation

#### a. Install ISCE-2 and MintPy

[Here](https://github.com/yunjunz/conda_envs) is an example instruction to install both isce2 and mintpy in the same environment using conda. If you have GPU, we recommend using isce2 installation "option 2" there to leverage the GPU processing.

#### b. Install `isce-proc`

Download source code:

```bash
cd ~/tools
git clone https://github.com/radarscilab/isce-proc.git
```

Setup path by adding the following to your config file, such as `.bashrc` or `.bash_profile` for `bash` users:

```bash
##-------------- isce-proc ----------------------------##
export ISCE_PROC_HOME=~/tools/isce-proc
export PYTHONPATH=${PYTHONPATH}:${ISCE_PROC_HOME}/src
export PATH=${PATH}:${ISCE_PROC_HOME}/src/isce_proc
```

#### c. Test the installation

```bash
run_isce_stack.py -h
```

### 2. Stack processing with `run_isce_stack.py`

This script implements the process outlined in the readme files of ISCE-2 [topsStack](https://github.com/isce-framework/isce2/blob/main/contrib/stack/topsStack/README.md) and [stripmapStack](https://github.com/isce-framework/isce2/blob/main/contrib/stack/stripmapStack/README.md), so that one could run the entire stack processing in one line. Inside the script, it 1) downloads the DEM; 2) call `stackSentinel.py` or `stackStripMap.py` to (download the orbit files for S1), generate the configuration and run files; 3) submit the run files one by one using `run.py` (with multiple processes if asked for).

The processing parameters are controlled via a configuration file, in a similar style to MintPy's `smallbaselineApp.cfg`, for easy re-production and modification. Run `run_isce_stack.py -h` for the detailed usage and example. Below is what I run to get a typical small baseline InSAR processing:

1. run `ssara_federated_query.py` from SSARA to download S1 data from ASF into the "SLC" folder.
   - Use parallel downloading via `--parallel` option
2. run `run_isce_stack.py` to generate the stack of interferograms.
   - create a configuration file using the template example from `run_isce_stack.py -h`, e.g. `AtacamaSenAT120.txt`
   - run `run_isce_isce.py AtacamaSenAT120.txt` to download DEM and orbit data, and prepare run files
   - run `run_isce_isce.py AtacamaSenAT120.txt --run` to execute the run files
3. run `smallbaselineApp.py` from MintPy to generate the time-series.

Notes:

+ Tested for Sentinel-1, ALOS and ALOS2 stripmap, NOT tested for other sensors/modes yet.
+ It's recommended to use the exact same bounding box for both SSARA and topsStack to avoid potential descrepency between the downloaded S1 data and the needed S1 data.
