#!/usr/bin/env python3
# Author: Zhang Yunjun, Mar 2019


import argparse
import os
import sys

from mintpy.objects import sensor
from mintpy.utils import readfile

from isce_proc.utils import utils, config


#####################################################################################
EXAMPLE = """example:
  # warming up the environment
  # run "screen -S SenAT120 -L" to start a screen session
  # run "load_insar" to source ISCE and MintPy

  run_isce_stack.py AtacamaSenAT120.txt         # prepare           run_files
  run_isce_stack.py AtacamaSenAT120.txt --run   # prepare / execute run_files

  # continue processing from certain step [only when DEM and run_files/configs already exist]
  run_isce_stack.py AtacamaSenAT120.txt --start 2 --end 7

  # clean up directory before re-processing
  run_isce_stack.py AtacamaSenAT120.txt --reset
"""

def create_parser():
    parser = argparse.ArgumentParser(description='Driver script of ISCE-2 (tops/stripmap) stack processor.',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog=config.EXAMPLE_TEMPLATE+'\n'+EXAMPLE)

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

    return inps


def read_inps2dict(inps):
    print('read options from template file: '+os.path.basename(inps.templateFile))
    template = readfile.read_template(inps.templateFile)
    template = utils.check_template_auto_value(template)

    # merge template and inps into iDict
    key_prefix = 'isce.'
    iDict = vars(inps)
    key_list = [i.split(key_prefix)[1] for i in template.keys() if i.startswith(key_prefix)]
    for key in key_list:
        iDict[key] = template[key_prefix + key]
    # add extra info:
    iDict['sensor'], iDict['projectName'] = sensor.project_name2sensor_name(iDict['templateFile'])

    # check: processor
    if iDict['processor'] not in ['topsStack', 'stripmapStack']:
        msg = 'un-recognized ISCE-2 stack processor: {}'.format(iDict['processor'])
        msg += 'supported processors: [topsStack, stripmapStack]'
        raise ValueError(msg)

    # default: --text_cmd option
    if iDict['processor'] == 'topsStack':
        iDict['text_cmd'] = 'export PATH=${PATH}:${ISCE_STACK}/topsStack'
    else:
        iDict['text_cmd'] = 'export PATH=${PATH}:${ISCE_STACK}/stripmapStack'

    # default: expand all paths to abspath
    for key in iDict.keys():
        if key.endswith(('File', 'Dir')) and iDict[key]:
            iDict[key] = os.path.expanduser(iDict[key])
            iDict[key] = os.path.expandvars(iDict[key])
            iDict[key] = os.path.abspath(iDict[key])

    return iDict


#####################################################################################
def main(iargs=None):
    inps = cmd_line_parse(iargs)
    iDict = read_inps2dict(inps)

    # --reset option
    if inps.reset:
        utils.reset_proc_dir(iDict['processor'])
        return

    # --start option
    if inps.startStep:
        status = utils.run_stack(iDict)
        return status

    # prepare DEM
    iDict = utils.prep_dem(iDict)

    # prepare RAW/SLC data (for stripmapStack only)
    if iDict['processor'] == 'stripmapStack':

        if iDict['sensor'] == 'Alos':
            run_file = utils.prep_ALOS(iDict)

        elif iDict['sensor'] == 'Alos2':
            run_file = utils.prep_ALOS2(iDict)

        else:
            raise ValueError('unsupported sensor: {}'.format(iDict['sensor']))

    # prepare stack processing
    utils.prep_stack(iDict)

    # run stack processing
    if inps.runStack:
        utils.run_stack(iDict)

    return


#####################################################################################
if __name__ == '__main__':
    main(sys.argv[1:])
