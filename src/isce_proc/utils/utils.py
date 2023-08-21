#!/usr/bin/env python3
# Author: Zhang Yunjun, Apr 2023
# Recommend usage:
#   from isce_proc.utils import utils


import datetime as dt
import glob
import os
import subprocess
import time
import shutil

import numpy as np

from isce_proc.utils import config


PARALLEL_STEPS = ['topo', 'geo2rdr', 'resamp']

RESET_CMD_TOPS_STACK = """
rm -r ESD/ coarse_interferograms/ interferograms/ geom_reference/ merged/interferograms/*/fine* merged/interferograms/*/filt_fine.int
"""
RESET_CMD_STRIPMAP_STACK = """
rm -r baselines/ configs/ coregSLC/ geom_reference/ Igrams/ merged/ offsets/ refineSecondaryTiming/ run_* SLC/ referenceShelve/
cd download;  rm -rf 20* AL*;  mv ARCHIVED_FILES/* .;  cd ..
"""


############################## Random Utilities ##############################
def reset_proc_dir(processor='topsStack'):
    """Reset processing directory before re-run."""

    cmd_str = '------ Copy and paste the following the command to reset the process direction ----\n'
    if processor == 'topsStack':
        cmd_str += RESET_CMD_TOPS_STACK
    elif processor == 'stripmapStack':
        cmd_str += RESET_CMD_STRIPMAP_STACK

    print(cmd_str)
    return


def copy_reference_shelve(iDict, out_dir='referenceShelve'):
    """Copy shelve files into root directory [for stripmapStack].

    """
    proj_dir = os.path.abspath(os.getcwd())

    # check folders
    shelve_dir = os.path.join(proj_dir, out_dir)
    if os.path.isdir(shelve_dir) :
        print('referenceShelve folder already exists: {}'.format(shelve_dir))
        return
    else:
        print('create directory: {}'.format(shelve_dir))
        os.makedirs(shelve_dir)

    # check files
    shelve_files = ['data.bak','data.dat','data.dir']
    if all(os.path.isfile(os.path.join(shelve_dir, i)) for i in shelve_files):
        print('all shelve files already exists')
        return
    else:
        date_list = sorted([os.path.basename(i) for i in glob.glob('SLC/*')])
        m_date = iDict.get('referenceDate', date_list[0])
        slc_dir = os.path.join(proj_dir, 'SLC/{}'.format(m_date))
        for shelve_file in shelve_files:
            shelve_file = os.path.join(slc_dir, shelve_file)
            shutil.copy2(shelve_file, shelve_dir)
            print('copy {} to {}'.format(shelve_file, shelve_dir))
    return


def check_template_auto_value(tempDict, autoDict=config.AUTO_DICT):
    """Check template content against default config.

    Including:
    + translate auto values
    + fill missing options
    + translate special values for typoes
    + translate wildcards inputs
    """

    # 1. translate auto value: remove them, then fill them in step 2
    for key in list(tempDict.keys()):
        if tempDict[key] == 'auto':
            tempDict.pop(key)

    # 2. fill missing options
    for key in autoDict.keys():
        if key not in tempDict.keys():
            tempDict[key] = autoDict[key]

    # 3. translate special values: yes/no/true/false/none
    specialValues = {
        'yes'  : True,
        'true' : True,
        'no'   : False,
        'false': False,
        'none' : None,
    }
    for key, value in tempDict.items():
        value = str(value).lower()
        if value in specialValues.keys():
            tempDict[key] = specialValues[value]

    # 4. translate wildward inputs
    for key in ['isce.demFile']:
        if tempDict[key] and '*' in tempDict[key]:
            values = glob.glob(tempDict[key])
            if len(values) > 0:
                tempDict[key] = values[0]

    return tempDict


def run_sh_file(sh_file, text_cmd=None, num_proc=1):
    """Run shell file."""

    print('running {}'.format(os.path.basename(sh_file)))
    print('At time: {}'.format(dt.datetime.now()))
    start_time = time.time()

    stack_dir = os.environ['ISCE_STACK']
    scp_name = os.path.join(stack_dir, 'topsStack', 'run.py')

    # check num_proc against number of lines
    def get_file_line_number(fname):
        with open(sh_file, 'r') as f:
            for i, l in enumerate(f):
                pass
        return i + 1

    num_line = get_file_line_number(sh_file)
    num_proc = min(int(num_proc), num_line)

    # compose command line
    cmd = '{} -i {} -p {}'.format(scp_name, sh_file, num_proc)
    if text_cmd:
        cmd = text_cmd + '; ' + cmd
    print(cmd)

    # execute
    status = subprocess.Popen(cmd, shell=True).wait()
    if status != 0:
        raise RuntimeError("Error in {}".format(sh_file))
    print('finished running {} with status {}'.format(sh_file, status))

    # Timing
    h, m = divmod(divmod(time.time()-start_time, 60)[0], 60)
    print('Time used: {:03.0f} hours {:02.0f} mins\n'.format(h, m))

    return status


def run_stack(iDict, run_file_dir='run_files'):
    """Run stack processing by executing files within the run_files folder."""

    # check: run_files and configs directories
    for dir_name in ['configs', 'run_files']:
        if not os.path.isdir(dir_name):
            raise NotADirectoryError('NO {} folder found in the current directory!'.format(dir_name))

    # path setup for the stack processor
    isce_stack_dir = os.path.expandvars('${ISCE_STACK}')
    print(f'load ISCE-2 {iDict["processor"]} from {isce_stack_dir}/{iDict["processor"]}')
    os.system('export PATH=${PATH}:${ISCE_STACK}/' + f'{iDict["processor"]}')

    # go to run_files directory
    dir_orig = os.path.abspath(os.getcwd())
    run_file_dir = os.path.join(dir_orig, run_file_dir)
    os.chdir(run_file_dir)
    print('go to directory: {}'.format(run_file_dir))

    # remove un-necessary *.job files
    job_files = glob.glob(os.path.join(run_file_dir, 'run_*_*.job'))
    for job_file in job_files:
        os.remove(job_file)
        print('remove file: {}'.format(job_file))

    # grab all run files
    run_files = glob.glob(os.path.join(run_file_dir, 'run_[0-9][0-9]_*'))
    run_files = sorted([i for i in run_files if '.' not in os.path.basename(i)])  # clean up

    # start/end step
    # note that python list starts from zero
    num_step = len(run_files)
    for key, val in zip(['startStep', 'endStep'], [1, num_step]):
        if not iDict[key]:
            iDict[key] = val
        else:
            iDict[key] = int(iDict[key])
    step0 = iDict['startStep'] - 1
    step1 = iDict['endStep'] - 1
    print('number of steps: {}'.format(num_step))
    print('steps to run: {}'.format(run_files[step0:step1+1]))

    # submit job step by step
    for step_ind in range(step0, step1+1):
        run_file = run_files[step_ind]

        # adjust num_proc for steps with OMP_NUM_THREADS enabled.
        num_proc = int(iDict['numProcess'])
        num_thread = int(os.environ.get('OMP_NUM_THREADS',1))
        if any(i in run_file for i in PARALLEL_STEPS):
            num_proc = np.ceil(num_proc / num_thread).astype(int)

        print('\n\n'+'#'*50)
        run_sh_file(run_file,
                    text_cmd=iDict['text_cmd'],
                    num_proc=num_proc)

    # go back to original directory
    os.chdir(dir_orig)
    print('go to directory: {}'.format(dir_orig))
    return


############################## Stack Preparation #############################
def prep_dem(iDict):
    """Prepare DEM for stack processing"""

    # DEM dir
    dir_orig = os.path.abspath(os.getcwd())
    if iDict['demFile']:
        dem_dir = os.path.abspath(os.path.dirname(iDict['demFile']))
    else:
        dem_dir = os.path.join(dir_orig, 'DEM')
    os.makedirs(dem_dir, exist_ok=True)

    if iDict['demFile'] and os.path.isfile(iDict['demFile']):
        print('input DEM file exists: {}, skip re-generation.'.format(iDict['demFile']))
        return iDict

    else:
        dem_files = glob.glob(os.path.join(dem_dir, '*.dem.wgs84'))
        if len(dem_files) > 0 and os.path.isfile(dem_files[0]):
            print('use existing DEM file: {}'.format(dem_files[0]))
            iDict['demFile'] = dem_files[0]
            return iDict

        else:
            print('genenrating new DEM ...')

    # auto demSNWE from bbox
    if not iDict['demSNWE']:
        if iDict['boundingBox']:
            bbox = [float(i) for i in iDict['boundingBox'].split(',')]
            buff = float(iDict.get('demBuffer', 3))
            dem_bbox = [bbox[0]-buff, bbox[1]+buff,
                        bbox[2]-buff, bbox[3]+buff]
        else:
            raise ValueError('required demSNWE not found!')
    else:
        dem_bbox = [float(i) for i in iDict['demSNWE'].split(',')]

    # download/stitch DEM
    os.chdir(dem_dir)
    print('go to directory', dem_dir)

    # compose command line for DEM generation with dem(_gsi).py
    if iDict['demSource'] == 'gsi_dehm':
        # DEHM from GSI Japan via mintpy/dem_gsi.py
        cmd = 'dem_gsi.py --bbox {}'.format(' '.join(str(i) for i in dem_bbox))
        dem_file = os.path.join(dem_dir, 'gsi10m.dem.wgs84')

    else:
        # SRTM from USGS via isce/dem.py
        dem_bbox = [int(x) for x in [
            np.floor(dem_bbox[0]), np.ceil(dem_bbox[1]),
            np.floor(dem_bbox[2]), np.ceil(dem_bbox[3]),
        ]]
        # call dem.py
        cmd = 'dem.py --action stitch --bbox {}'.format(' '.join(str(i) for i in dem_bbox))
        cmd += ' --report --source {}'.format(iDict['demSource'].split('srtm')[1])
        cmd += ' --correct --filling --filling_value {}'.format(iDict['demFillValue'])
        if iDict['demUrl']:
            cmd += f' -u {iDict["demUrl"]}'
        dem_file = os.path.join(dem_dir, 'demLat*.dem.wgs84')

    # run the command line
    print(cmd)
    status = subprocess.Popen(cmd, shell=True).wait()
    if status != 0:
        raise RuntimeError("Error in DEM generation.")

    # clean up
    dem_file_geoid = dem_file.replace('.wgs84','')
    for fext in ['', '.xml', '.vrt']:
        if os.path.isfile(dem_file_geoid+fext):
            os.remove(dem_file_geoid+fext)
            print('remove file:', dem_file_geoid+fext)

    # get DEM filename
    dem_files = glob.glob(dem_file)
    if len(dem_files) > 0:
        iDict['demFile'] = dem_files[0]
    else:
        raise FileNotFoundError('DEM file not found in {}'.format(dem_file))

    # go back to the original directory
    os.chdir(dir_orig)
    print('go to directory', dir_orig)
    return iDict


def prep_ALOS(iDict):
    """Prepare ALOS raw data for processing [for stripmapStack].

    + call prepRawALOS.py to:
        - uncompress the downloaded tar/zip files
        - organize into date forlders
        - generate the unpack script
    + call the unpack script to:
        - generate SLC
        - prepare the ISCE format
    """

    # compose prep script
    scp = os.path.expandvars('$ISCE_STACK/stripmapStack/prepRawALOS.py')
    cmd = f'{scp} -i ./download -o ./SLC -t "" '
    # convert ALOS PALSAR FBD mode to FBS mode
    if iDict.get('ALOS.fbd2fbs', True):
        cmd += ' --dual2single '

    # run prep script --> unpack script
    print(cmd)
    os.system(cmd)

    # run unpack script
    run_sh_file(
        'run_unPackALOS',
        text_cmd=iDict['text_cmd'],
        num_proc=int(iDict['numProcess']),
    )

    return


def prep_ALOS2(iDict):
    """Prepare ALOS2 stripmap SLC data for processing [for stripmapStack].

    + call prepSlcALOS2.py to:
        - uncompress the downloaded tar/zip files
        - organize into date forlders
        - generate the unpack script
    + call the unpack script to:
        - prepare the ISCE format
    """

    # compose prep script
    scp = os.path.expandvars('$ISCE_STACK/stripmapStack/prepSlcALOS2.py')
    cmd = f'{scp} -i ./download -o ./SLC -t ""'
    if iDict.get('ALOS2.polarization', None):
        cmd += ' --polarization {}'.format(iDict['ALOS2.polarization'])

    # run prep script --> unpack script
    print(cmd)
    os.system(cmd)

    # run unpack script
    run_sh_file(
        'run_unPackALOS2',
        text_cmd=iDict['text_cmd'],
        num_proc=int(iDict['numProcess']),
    )

    return


def prep_stack(iDict):
    """Call stack*.py to generate run_files and config folders"""

    # 1. load corresponding stack processor module
    # 2. setup PATH for individual scripts to be executable
    proc = iDict['processor']
    if proc == 'topsStack':
        from topsStack import stackSentinel as isce_stack
        isce_stack_path = os.path.expandvars('$ISCE_STACK/topsStack')
    else:
        from stripmapStack import stackStripMap as isce_stack
        isce_stack_path = os.path.expandvars('$ISCE_STACK/topsStack')
    os.environ["PATH"] = os.environ["PATH"] + os.pathsep + isce_stack_path
    scp_name = os.path.basename(isce_stack.__file__)

    ##### compose the command line script
    ##---------- 1. required options
    # 1.1 common options
    iargs = [
        '--slc_directory',   os.path.abspath('./SLC'),
        '--workflow',        iDict['workflow'],
        '--dem',             iDict['demFile'],
        '--azimuth_looks',   iDict['azimuthLooks'],
        '--range_looks',     iDict['rangeLooks'],
        '--filter_strength', iDict['filtStrength'],
        '--unw_method',      iDict['unwrapMethod'],
    ]

    # 1.2 unique options
    if proc == 'topsStack':
        iargs += [
            '--coregistration',  iDict['coregistration'],
            '--num_connections', iDict['numConnection'],
            '--aux_directory',   iDict['auxDir'],
            '--orbit_directory', iDict['orbitDir'],
            '--virtual_merge',   str(iDict['virtualMerge']),
        ]

    else:
        iargs += [
            '--time_threshold',     iDict['maxTempBaseline'],
            '--baseline_threshold', iDict['maxPerpBaseline'],
        ]

    ##---------- 2. optional options
    # 2.1 common options
    if iDict['referenceDate']:
        iargs += ['--reference_date', iDict['referenceDate']]

    if iDict['boundingBox']:
        iargs += ['--bbox', ' '.join(i for i in iDict['boundingBox'].split(','))]

    if iDict['useGPU']:
        iargs += ['--useGPU']

    # 2.2 unique options
    if proc == 'topsStack':
        if iDict['startDate']:
            t0 = dt.datetime.strptime(iDict['startDate'], '%Y%m%d')
            iargs += ['--start_date', t0.strftime('%Y-%m-%d')]

        if iDict['endDate']:
            t1 = dt.datetime.strptime(iDict['endDate'], '%Y%m%d')
            iargs += ['--stop_date', t1.strftime('%Y-%m-%d')]

        if iDict['swathNum']:
            iargs += ['--swath_num', ' '.join(i for i in iDict['swathNum'].split(','))]

        if iDict['numProcess']:
            if iDict['numProcess4topo']:
                num_proc = iDict['numProcess4topo']
            else:
                num_thread = int(os.environ.get('OMP_NUM_THREADS',1))
                num_proc = np.floor(int(iDict['numProcess']) / num_thread).astype(int)
            iargs += ['--num_proc4topo', str(num_proc)]

        if iDict['updateMode']:
            iargs += ['--update']

        if iDict['paramIonFile']:
            iargs += ['--param_ion', iDict['paramIonFile'], '--num_connections_ion', iDict['numConnectionIon']]

    else:
        #if iDict['applyWaterMask']:
        #    iargs += ['--applyWaterMask']

        if iDict['sensor'] in ['Alos2']:
            iargs += ['--nofocus', '--zero']

    ##### run the command line script
    print(scp_name, ' '.join(iargs))
    isce_stack.main(iargs)

    return
