#!/usr/bin/env python3
# Author: Zhang Yunjun, Apr 2023
# Recommend usage:
#   from isce_proc.utils import config


EXAMPLE_TEMPLATE = """template:
##------------------------------- ISCE tops/stripmapStack ------------------------------##
isce.processor          = stripmapStack              #[stripmapStack, topsStack], auto for topsStack
isce.workflow           = interferogram              #[slc / correlation / interferogram / offset], auto for interferogram
isce.demSNWE            = 31.1, 32.8, 130.1, 131.9   #[S, N, W, E] in degree, auto for none (expaned from boundingBox; otherwise error)
isce.demFile            = ./DEM/gsi10m.dem.wgs84     #DEM file name, auto for none (generate on the fly)
isce.demSource          = srtm1                      #[srtm1, srtm3, nasadem, gsi_dehm], auto for srtm1
isce.demFillValue       = 0                          #[0 / 1 / -32768], value used to fill missing DEMs, auto for -32768
isce.demUrl             = none                       #[none, https://e4ftl01.cr.usgs.gov/DP133/SRTM/SRTMGL1.003/2000.02.11], auto for none
isce.demBuffer          = 3                          #[int], buffer btw. SNWE and download DEM tiles, auto for 3
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
    'isce.demUrl'         : None,
    'isce.demBuffer'      : 3,
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
