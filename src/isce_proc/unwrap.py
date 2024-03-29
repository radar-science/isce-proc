#!/usr/bin/env python3
# Author: Zhang Yunjun, Apr 2023


import argparse
import os
import sys
import time

import numpy as np
from mintpy.utils import readfile, writefile, isce_utils


######################################################################################
EXAMPLE = """example:
  unwrap.py -i filt_fine.int -c filt_fine.cor -o filt_fine.unw

  # commands to run phase unwrapping with a custom mask
  prep_isce.py -d ./merged/interferograms -f filt_fine.int -m ./reference/IW1.xml -b ./baselines/ -g ./merged/geom_reference/
  generate_mask.py ../../geom_reference/los.rdr inc -m 1 --base ../../geom_reference/waterMask.rdr -o waterMask.h5
  generate_mask.py filt_fine.cor -m 0.4 --vroipoly --base waterMask.h5 -o maskUnw.h5 
  # may use "generate_mask.py maskUnw.h5 -m 0.5 --mp 400 -o mask1.h5" to remove small isolated clusters.
  unwrap.py -i filt_fine.int -c filt_fine.cor -o filt_fine.unw --mask maskUnw.h5
"""

def create_parser():
    parser = argparse.ArgumentParser(description='Phase unwrap the interferogram',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog=EXAMPLE)

    parser.add_argument('-i','--int', dest='int_file', type=str, required=True,
                        help='Path of the input interferogram file.')
    parser.add_argument('-c','--cor', dest='cor_file', type=str, required=False,
                        help='Path of the input coherence (phase sigma) file.')
    parser.add_argument('-o','-u','--unw', dest='unw_file', type=str, required=True,
                        help='Path of the output unwrapped interferogram file.')
    parser.add_argument('-m','--method', dest='unwrap_method', type=str,
                        choices={'icu', 'snaphu'}, default='snaphu',
                        help='Phase unwrapping algorithm (default: %(default)s).')
    parser.add_argument('--mask', dest='mask_file', type=str,
                        help='Path of an mask file to mask interferogram before PU,'
                             ' by setting the amplitude value to zero.')
    parser.add_argument('--min-cor','--min-coherence', dest='min_coherence', type=float, default=0,
                        help='Set a minimum coherence value to mask out low coherent pixels (default: %(default)s).')

    snaphu = parser.add_argument_group('SNAPHU', 'SNAPHU Configurations')
    snaphu.add_argument('--max-defo', dest='max_defo', type=float, default=2.0,
                        help='Maximum phase discontinuity likely in cycles. (default: %(default)s)')
    snaphu.add_argument('--max-comp', dest='max_comp', type=int, default=20,
                        help='Maximum number of connected component per tile. (default: %(default)s)')
    snaphu.add_argument('--init-only', dest='init_only', action='store_true',
                        help='Initialize-only mode. (default: %(default)s)')
    snaphu.add_argument('--init-method', dest='init_method', type=str,
                        choices={'MST', 'MCF'}, default='MST',
                        help='Algorithm used for initialization of wrapped phase values. (default: %(default)s)')
    snaphu.add_argument('--cost-mode', dest='cost_mode', type=str,
                        choices={'TOPO', 'DEFO', 'SMOOTH', 'NOSTATCOSTS'}, default='DEFO',
                        help='Statistical-cost mode. (default: %(default)s)')

    return parser


def cmd_line_parse(iargs=None):
    parser = create_parser()
    inps = parser.parse_args(args=iargs)

    for fname in [inps.int_file, inps.cor_file, inps.mask_file]:
        if fname and not os.path.isfile(fname):
            raise FileNotFoundError(f'No file found in: {fname}')

    return inps


######################################################################################
def mask_int_file(int_file, msk_file, cor_file=None, min_coherence=0):
    """Mask int_file based on mask_file."""
    # read
    data = readfile.read(int_file, datasetName='complex')[0]
    mask = readfile.read(msk_file)[0]

    # mask out pixels by setting to zero
    flag = mask == 0
    data[flag] = 0
    print(f'masking out pixels using file: {msk_file} ({np.sum(flag)} pixels)')

    # mask out pixels with nan value, as it's not supported by snaphu
    data[np.isnan(data)] = 0

    # mask based on coherence threshold
    if min_coherence > 0 and cor_file:
        cor = readfile.read(cor_file)[0]
        flag = cor < min_coherence
        data[flag] = 0
        print(f'masking out pixels with values < {min_coherence} in file: {cor_file} ({np.sum(flag)} pixels)')

    # write
    fbase, fext = os.path.splitext(int_file)
    out_file = f'{fbase}_msk{fext}'
    print(f'write masked interferograms to file: {out_file}')

    atr = readfile.read_attribute(int_file)
    writefile.write(data, out_file=out_file, metadata=atr, ref_file=int_file)
    writefile.write_isce_xml(atr, out_file)

    return out_file


######################################################################################
def main(iargs=None):
    inps = cmd_line_parse(iargs)

    # --mask option
    if inps.mask_file:
        inps.int_file = mask_int_file(
            int_file=inps.int_file,
            msk_file=inps.mask_file,
            cor_file=inps.cor_file,
            min_coherence=inps.min_coherence,
        )

    if inps.unwrap_method == 'icu':
        isce_utils.unwrap_icu(
            int_file=inps.int_file,
            unw_file=inps.unw_file,
        )

    elif inps.unwrap_method == 'snaphu':
        isce_utils.unwrap_snaphu(
            int_file=inps.int_file,
            cor_file=inps.cor_file,
            unw_file=inps.unw_file,
            max_defo=inps.max_defo,
            max_comp=inps.max_comp,
            init_only=inps.init_only,
            init_method=inps.init_method,
            cost_mode=inps.cost_mode,
        )


######################################################################################
if __name__ == '__main__':
    main(sys.argv[1:])
