## SAR / InSAR Processing Workflow

This repository contains some code and notes to facilitate the SAR and InSAR processing using [ISCE2](https://github.com/isce-framework/isce2) and [MintPy](https://github.com/insarlab/MintPy).

This is research code provided to you "as is" with NO WARRANTIES OF CORRECTNESS. Use at your own risk.

### 1. [Installation](./docs/installation.md)

### 2. ISCE2 stack processing with `run_isce_stack.py`

This script implements the process outlined in the readme files of ISCE-2 [topsStack](https://github.com/isce-framework/isce2/blob/main/contrib/stack/topsStack/README.md) and [stripmapStack](https://github.com/isce-framework/isce2/blob/main/contrib/stack/stripmapStack/README.md), so that one could run the entire stack processing in one line. Inside the script, it:

1. Downloads the DEM;
2. Call `stackSentinel.py` or `stackStripMap.py` to (download the orbit files for S1), generate the configuration and run files;
3. Submit the run files one by one using `run.py` (with multiple processes if asked for).

The processing parameters are controlled via a configuration file, similar to MintPy's `smallbaselineApp.cfg`, for easy reproduction and modification. Run `run_isce_stack.py -h` for the detailed usage and example. 

Below is what I run to get a typical small baseline InSAR processing:

1. run `ssara_federated_query.py` from SSARA to download S1 data from ASF into the "SLC" folder.
   - Use parallel downloading via `--parallel` option
2. run `run_isce_stack.py` to generate the stack of interferograms.
   - create a configuration file using the template example from `run_isce_stack.py -h`, e.g. `AtacamaSenAT120.txt`
   - run `run_isce_isce.py AtacamaSenAT120.txt` to download DEM and orbit data, and prepare run files
   - run `run_isce_isce.py AtacamaSenAT120.txt --start 1` to execute the run files
3. run `smallbaselineApp.py` from MintPy to generate the time-series.

#### Notes:

+ Tested for Sentinel-1 and ALOS/ALOS2 stripmap, NOT tested for other sensors/modes yet.
+ It's recommended to use the same bounding box for both `SSARA` and `topsStack` to avoid potential discrepancies between the downloaded S1 data and the needed S1 data.
