#!/usr/bin/env python3
# Author: Zhang Yunjun, Mar 2019


import argparse
import datetime as dt
import glob
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from mintpy.objects import sensor
from mintpy.utils import readfile


KEY_PREFIX = 'isce.'
PARALLEL_STEPS = ['topo', 'geo2rdr', 'resamp']

#####################################################################################
EXAMPLE = """example:
  # warming up the environment
  # run "screen -S SenAT120 -L" to start a screen session
  # run "load_insar" to source ISCE and MintPy
  # run "load_tops/stripmap_stack" to load ISCE stack processor

  run_isce_stack.py AtacamaSenAT120.txt         # prepare           run_files
  run_isce_stack.py AtacamaSenAT120.txt --run   # prepare / execute run_files

  # continue processing from certain step [only when DEM and run_files/configs already exist]
  run_isce_stack.py AtacamaSenAT120.txt --start 2 --end 7

  # clean up directory before re-processing
  run_isce_stack.py AtacamaSenAT120.txt --reset
"""

TEMPLATE = """template:
##------------------------------- ISCE tops/stripmapStack ------------------------------##
isce.processor          = stripmapStack              #[stripmapStack, topsStack], auto for topsStack
isce.workflow           = interferogram              #[slc / correlation / interferogram / offset], auto for interferogram
isce.demSNWE            = 31.1, 32.8, 130.1, 131.9   #[S, N, W, E] in degree, auto for none (expaned from boundingBox; otherwise error)
isce.demFile            = ./DEM/gsi10m.dem.wgs84     #DEM file name, auto for none (generate on the fly)
isce.demSource          = srtm1                      #[srtm1, srtm3, nasadem, gsi_dehm], auto for srtm1
isce.demFillValue       = 0                          #[0 / 1 / -32768], value used to fill missing DEMs, auto for -32768
isce.boundingBox        = none                       #[S, N, W, E] in degree, auto for none
isce.referenceDate      = none                       #[20150101 / no], auto for none (1st date)
isce.azimuthLooks       = 3                          #[int], auto for 3
isce.rangeLooks         = 9                          #[int], auto for 9
isce.filtStrength       = 0.5                        #[0.0-1.0], auto for 0.5
isce.unwrapMethod       = snaphu                     #[snaphu / icu], auto for snaphu
isce.useGPU             = no                         #[yes / no], auto for no
isce.numProcess         = 4                          #[int>=1], number of processors, auto for 4

##----------for topsStack only:
isce.virtualMerge       = no                         #[yes / no], auto for no, use virtual files for the merged SLCs and geometry
isce.coregistration     = geometry                   #[geometry / NESD], auto for geometry
isce.swathNum           = 1,2                        #[1,2,3], auto for '1,2,3'
isce.numConnection      = 5                          #[int>=1], auto for 3
isce.orbitDir           = ~/bak/aux/aux_poeorb/      #Directory with all orbit files
isce.auxDir             = ~/bak/aux/aux_cal/         #Directory with all aux   files
isce.startDate          = none                       #[20140825 / no], auto for none (1st date)
isce.endDate            = none                       #[20190622 / no], auto for none (last date)
isce.numProcess4topo    = auto                       #auto for numProcess/OMP_NUM_THREADS. Max limited by no. of CPUs per node on server
## ionospheric phase estimation
## copy $ISCE_STACK/topsStack/ion_param.txt to the local dir to turn ON iono
isce.numConnectionIon   = 3                          #[int>=1], auto for 3
isce.paramIonFile       = ./ion_param.txt            #Ion param file, auto for none (no iono estimation)

##----------for stripmapStack only:
## Sensors with zero doppler SLC: ALOS2
## link: https://github.com/isce-framework/isce2/blob/master/components/isceobj/StripmapProc/Factories.py#L61
isce.zeroDopper         = no                         #[yes / no], use zero doppler geometry for processing, auto for no
isce.focus              = no                         #[yes / no], do focus, auto for yes (for RAW data)
isce.ALOS.fbd2fbs       = yes                        #[yes / no], auto for yes, convert FBD to FBS for ALOS-1
isce.ALOS2.polarization = HH                         #[HH / VV], auto for HH
isce.maxTempBaseline    = 1800                       # auto for 1800 days
isce.maxPerpBaseline    = 1800                       # auto for 1800 meters
isce.applyWaterMask     = yes                        # auto for yes
"""


AUTO_DICT = {
    'isce.processor'      : 'topsStack',
    'isce.workflow'       : 'interferogram',
    'isce.demSNWE'        : None,
    'isce.demFile'        : None,
    'isce.demSource'      : 'srtm1',
    'isce.demFillValue'   : '-32768',
    'isce.boundingBox'    : None,
    'isce.referenceDate'  : None,
    'isce.azimuthLooks'   : '3',
    'isce.rangeLooks'     : '9',
    'isce.filterStrength' : '0.5',
    'isce.unwrapMethod'   : 'snaphu',
    'isce.useGPU'         : False,
    'isce.numProcess'     : 4,

    #for topsStack only
    'isce.virtualMerge'       : False,
    'isce.coregistration'     : 'geometry',
    'isce.swathNum'           : '1,2,3',
    'isce.numConnection'      : '3',
    'isce.orbitDir'           : '~/bak/aux/aux_poeorb/',
    'isce.auxDir'             : '~/bak/aux/aux_cal/',
    'isce.startDate'          : None,
    'isce.endDate'            : None,
    'isce.numProcess4topo'    : None,
    'isce.numConnection.Ion'  : '3',
    'isce.paramIonFile'       : None,

    #for stripmapStack only
    'isce.zeroDoppler'        : False,
    'isce.focus'              : True,
    'isce.ALOS.fbd2fbs'       : True,
    'isce.ALOS2.polarization' : 'HH',
    'isce.maxTempBaseline'    : '1800',
    'isce.maxPerpBaseline'    : '1800',
    'isce.applyWaterMask'     : True,
}


#####################################################################################

def create_parser():
    parser = argparse.ArgumentParser(description='Driver script of ISCE-2 (tops/stripmap) stack processor.',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog=TEMPLATE+'\n'+EXAMPLE)

    parser.add_argument('templateFile', type=str, help='template file')
    parser.add_argument('--run', dest='runStack', action='store_true', help='run/execute the run files')
    parser.add_argument('--reset', action='store_true', help='clean the directory before re-run.')

    step = parser.add_argument_group('Steps to run','This enables --run option automatically')
    parser.add_argument('--start', dest='startStep', type=int, help='Start processing at named run number.')
    parser.add_argument('--end', dest='endStep', type=int, help='End processing at named run number.')

    return parser


def cmd_line_parse(iargs=None):
    parser = create_parser()
    inps = parser.parse_args(args=iargs)

    if not inps.reset and not inps.templateFile:
        raise SystemExit('ERROR: at least one of the following arguments are required: -t/--template, --reset')

    if inps.templateFile:
        inps.templateFile = os.path.abspath(inps.templateFile)

    # --start/end
    if inps.startStep or inps.endStep:
        inps.runStack = True

    #if any(not os.path.isdir(i) for i in ['configs', 'run_files']):
    #    msg = 'ERROR: NO configs or run_files folder found in the current directory!'
    #    raise SystemExit(msg)
    return inps


#####################################################################################

def fill_and_translate_template_auto_value(tempDict, autoDict=AUTO_DICT):
    """Fill the missing template option with default value and
    translate special values
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
    specialValues = {'yes'  : True,
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
            else:
                tempDict[key] = None

    return tempDict


def read_inps2dict(inps):
    print('read options from template file: '+os.path.basename(inps.templateFile))
    template = readfile.read_template(inps.templateFile)
    template = fill_and_translate_template_auto_value(template)

    # merge template and inps into iDict
    iDict = vars(inps)
    key_list = [i.split(KEY_PREFIX)[1] for i in template.keys() if i.startswith(KEY_PREFIX)]
    for key in key_list:
        iDict[key] = template[KEY_PREFIX + key]
    # add extra info:
    iDict['sensor'], iDict['projectName'] = sensor.project_name2sensor_name(iDict['templateFile'])

    # check
    if iDict['processor'] not in ['topsStack', 'stripmapStack']:
        msg = 'un-recognized ISCE-2 stack processor: {}'.format(iDict['processor'])
        msg += 'supported processors: [topsStack, stripmapStack]'
        raise ValueError(msg)

    # expand all paths to abspath
    for key in iDict.keys():
        if key.endswith(('File', 'Dir')) and iDict[key]:
            iDict[key] = os.path.expanduser(iDict[key])
            iDict[key] = os.path.expandvars(iDict[key])
            iDict[key] = os.path.abspath(iDict[key])

    # --text_cmd
    if iDict['processor'] == 'topsStack':
        iDict['text_cmd'] = 'export PATH=${PATH}:${ISCE_STACK}/topsStack'
    else:
        iDict['text_cmd'] = 'export PATH=${PATH}:${ISCE_STACK}/stripmapStack'

    return iDict


#####################################################################################
def copy_referenceShelve(iDict, out_dir='referenceShelve'):
    """Copy shelve files into root directory"""
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


def reset_process_directory(processor='topsStack'):
    """Reset processing directory in order to re-run.
    """

    if processor == 'topsStack':
        cmd_str = """------ Copy and paste the following the command to reset the process direction ----

"""

    elif processor == 'stripmapStack':
        cmd_str="""------ Copy and paste the following the command to reset the process direction ----
rm -r baselines/ configs/ coregSLC/ geom_reference/ Igrams/ merged/ offsets/ refineSecondaryTiming/ run_* SLC/ referenceShelve/
cd download
rm -rf 20* AL*
mv ARCHIVED_FILES/* .
cd ..
    """

    print(cmd_str)
    return


#####################################################################################

def run_sh_file(sh_file, text_cmd=None, num_proc=1):
    """Run shell file"""
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


def prepare_dem(iDict):
    """Prepare DEM for stack processing"""

    # DEM dir
    dir_orig = os.path.abspath(os.getcwd())
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
            dem_bbox = [bbox[0]-3, bbox[1]+3, bbox[2]-3, bbox[3]+3]
        else:
            raise ValueError('required demSNWE not found!')
    else:
        dem_bbox = [float(i) for i in iDict['demSNWE'].split(',')]


    os.chdir(dem_dir)
    print('go to directory', dem_dir)

    # compose command line for DEM generation with dem(_gsi).py
    if iDict['demSource'] == 'gsi_dehm':
        # DEHM from GSI Japan
        cmd = 'dem_gsi.py --bbox {}'.format(' '.join(str(i) for i in dem_bbox))
        dem_file = os.path.join(dem_dir, 'gsi10m.dem.wgs84')

    else:
        # isce/dem.py takes integer input only
        dem_bbox = [np.floor(dem_bbox[0]), np.ceil(dem_bbox[1]),
                    np.floor(dem_bbox[2]), np.ceil(dem_bbox[3])]
        dem_bbox = [int(i) for i in dem_bbox]
        # call dem.py
        cmd = 'dem.py --action stitch --bbox {}'.format(' '.join(str(i) for i in dem_bbox))
        cmd += ' --report --source {}'.format(iDict['demSource'].split('srtm')[1])
        cmd += ' --correct --filling --filling_value {}'.format(iDict['demFillValue'])
        dem_file = os.path.join(dem_dir, 'demLat*.dem.wgs84')

    # run command line
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


def prepare_ALOS(iDict):
    # uncompress tar/zip files
    cmd = 'prepRawALOS.py -i ./download -o ./SLC -t "" '

    # convert ALOS PALSAR FBD mode to FBS mode
    if iDict.get('ALOS.fbd2fbs', True):
        cmd += ' --dual2single '

    print(cmd)
    os.system(cmd)

    # run unPack script
    run_sh_file('run_unPackALOS',
                text_cmd=iDict['text_cmd'],
                num_proc=int(iDict['numProcess']))
    return


def prepare_ALOS2(iDict):
    # uncompress tar/zip files
    cmd = 'prepSlcALOS2.py -i ./download -o ./SLC -t ""'

    if iDict.get('ALOS2.polarization', None):
        cmd += ' --polarization {}'.format(iDict['ALOS2.polarization'])

    print(cmd)
    os.system(cmd)

    # run unPack script
    run_sh_file('run_unPackALOS2',
                text_cmd=iDict['text_cmd'],
                num_proc=int(iDict['numProcess']))
    return


def prepare_stack(iDict):
    """Call stack*.py to generate run_files and config folders"""

    # load corresponding stack processor module
    proc = iDict['processor']
    if proc == 'topsStack':
        from topsStack import stackSentinel as prep_stack
    else:
        from stripmapStack import stackStripMap as prep_stack
    scp_name = os.path.basename(prep_stack.__file__)

    ##### compose the command line script
    ##----------required
    # common
    iargs = [
        '--slc_directory',   os.path.abspath('./SLC'),
        '--workflow',        iDict['workflow'],
        '--dem',             iDict['demFile'],
        '--azimuth_looks',   iDict['azimuthLooks'],
        '--range_looks',     iDict['rangeLooks'],
        '--filter_strength', iDict['filtStrength'],
        '--unw_method',      iDict['unwrapMethod'],
    ]

    # unique
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

    ##----------optional
    # common
    if iDict['referenceDate']:
        iargs += ['--reference_date', iDict['referenceDate']]

    if iDict['boundingBox']:
        iargs += ['--bbox', ' '.join(i for i in iDict['boundingBox'].split(','))]

    if iDict['useGPU']:
        iargs += ['--useGPU']

    # unique
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

        if iDict['paramIonFile']:
            iargs += ['--param_ion', iDict['paramIonFile'], '--num_connections_ion', iDict['numConnectionIon']]

    else:
        #if iDict['applyWaterMask']:
        #    iargs += ['--applyWaterMask']

        if iDict['sensor'] in ['Alos2']:
            iargs += ['--nofocus', '--zero']

    ##### run the command line script
    print(scp_name, ' '.join(iargs))
    prep_stack.main(iargs)

    return


def run_stack(iDict, run_file_dir='run_files'):
    """
    """

    # check dir: run_files and configs
    for dir_name in ['configs', 'run_files']:
        if not os.path.isdir(dir_name):
            raise NotADirectoryError('NO {} folder found in the current directory!'.format(dir_name))

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
    run_files  = glob.glob(os.path.join(run_file_dir, 'run_[0-9]_*'))             # stripmapStack
    run_files += glob.glob(os.path.join(run_file_dir, 'run_[0-9][0-9]_*'))        # topsStack
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



#####################################################################################
def main(iargs=None):
    inps = cmd_line_parse(iargs)
    iDict = read_inps2dict(inps)

    # --reset option
    if inps.reset:
        reset_process_directory(iDict['processor'])
        return

    # --start option
    if inps.startStep:
        status = run_stack(iDict)
        return status

    # prepare DEM
    iDict = prepare_dem(iDict)

    # prepare RAW/SLC data (for stripmapStack only)
    if iDict['processor'] == 'stripmapStack':

        if iDict['sensor'] == 'Alos':
            run_file = prepare_ALOS(iDict)

        elif iDict['sensor'] == 'Alos2':
            run_file = prepare_ALOS2(iDict)

        else:
            raise ValueError('unsupported sensor: {}'.format(iDict['sensor']))

    # prepare stack processing
    prepare_stack(iDict)

    # run stack processing
    if inps.runStack:
        run_stack(iDict)

    return


#####################################################################################
if __name__ == '__main__':
    main(sys.argv[1:])
