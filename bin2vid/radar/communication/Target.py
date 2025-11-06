"""
Created on 15.07.2022

@author: IMST GmbH
"""


class Target(object):
    idNumber = None  # target ID
    rangeBin = None  # used by detections
    dopplerBin = None  # used by detections
    tarRange = None  # result of tracking
    speed = None  # result of tracking
    aziAngle = None  # azimuth angle [deg]
    eleAngle = None  # elevation angle [deg] (only != 0 for MIMO radar cubes)
    magnitude = None  # target magnitude
    lifeTime = None  # how often target was found again (tracking)
    inferenceResult = None  # results of inference when DSP with NN is available and DspDopplerProc = 1 (tracking)
    dopplerSpectra = None  # complex or magnitude values of doppler spectra of tracks
