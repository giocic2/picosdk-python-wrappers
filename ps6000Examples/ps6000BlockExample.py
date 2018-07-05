#
# Copyright (C) 2018 Pico Technology Ltd. See LICENSE file for terms.
#
# PS6000 BLOCK MODE EXAMPLE
# This example opens a 6000 driver device, sets up two channels and a trigger then collects a block of data.
# This data is then plotted as mV against time in ns.

import ctypes
import numpy as np
from picosdk.ps6000 import ps6000 as ps
import matplotlib.pyplot as plt
from picosdk.functions import *

# Create chandle and status ready for use
chandle = ctypes.c_int16()
status = {}

# Open 6000 series PicoScope
# Returns handle to chandle for use in future API functions
status["openunit"] = ps.ps6000OpenUnit(ctypes.byref(chandle), None)

# Set up channel A
# handle = chandle
# channel = PS6000_CHANNEL_A = 0
# enabled = 1
# coupling type = PS6000_DC = 1
# range = PS6000_2V = 7
# analogue offset = 0 V
# bandwidth limiter = PS6000_BW_FULL = 0
chARange = 7
status["setChA"] = ps.ps6000SetChannel(chandle, 0, 1, 1, chARange, 0, 0)

# Set up channel B
# handle = chandle
# channel = PS6000_CHANNEL_B = 1
# enabled = 1
# coupling type = PS6000_DC = 1
# range = PS6000_2V = 7
# analogue offset = 0 V
# bandwidth limiter = PS6000_BW_FULL = 0
chBRange = 7
status["setChB"] = ps.ps6000SetChannel(chandle, 1, 1, 1, chBRange, 0, 0)

# Set up single trigger
# handle = chandle
# enabled = 1
# source = PS6000_CHANNEL_A = 0
# threshold = 64 ADC counts
# direction = PS6000_RISING = 2
# delay = 0 s
# auto Trigger = 1000 ms
status["trigger"] = ps.ps6000SetSimpleTrigger(chandle, 1, 0, 64, 2, 0, 1000)

# Set number of pre and post trigger samples to be collected
preTriggerSamples = 2500
postTriggerSamples = 2500
maxSamples = preTriggerSamples + postTriggerSamples

# Get timebase information
# handle = chandle
# timebase = 8 = timebase
# noSamples = maxSamples
# pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
# oversample = 1
# pointer to maxSamples = ctypes.byref(returnedMaxSamples)
# segment index = 0
timebase = 8
timeIntervalns = ctypes.c_float()
returnedMaxSamples = ctypes.c_int32()
status["getTimebase2"] = ps.ps6000GetTimebase2(chandle, timebase, maxSamples, ctypes.byref(timeIntervalns), 1, ctypes.byref(returnedMaxSamples), 0)

# Run block capture
# handle = chandle
# number of pre-trigger samples = preTriggerSamples
# number of post-trigger samples = PostTriggerSamples
# timebase = 8 = 80 ns (see Programmer's guide for mre information on timebases)
# oversample = 0
# time indisposed ms = None (not needed in the example)
# segment index = 0
# lpReady = None (using ps6000IsReady rather than ps6000BlockReady)
# pParameter = None
status["runBlock"] = ps.ps6000RunBlock(chandle, preTriggerSamples, postTriggerSamples, timebase, 0, None, 0, None, None)

# Check for data collection to finish using ps6000IsReady
ready = ctypes.c_int16(0)
check = ctypes.c_int16(0)
while ready.value == check.value:
    status["isReady"] = ps.ps6000IsReady(chandle, ctypes.byref(ready))

# Create buffers ready for assigning pointers for data collection
bufferAMax = (ctypes.c_int16 * maxSamples)()
bufferAMin = (ctypes.c_int16 * maxSamples)()
bufferBMax = (ctypes.c_int16 * maxSamples)()
bufferBMin = (ctypes.c_int16 * maxSamples)()

# Set data buffer location for data collection from channel A
# handle = chandle
# source = PS6000_CHANNEL_A = 0
# pointer to buffer max = ctypes.byref(bufferAMax)
# pointer to buffer min = ctypes.byref(bufferAMin)
# buffer length = maxSamples
# ratio mode = PS6000_RATIO_MODE_NONE = 0
status["setDataBuffersA"] = ps.ps6000SetDataBuffers(chandle, 0, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), maxSamples, 0)

# Set data buffer location for data collection from channel B
# handle = chandle
# source = PS6000_CHANNEL_B = 1
# pointer to buffer max = ctypes.byref(bufferBMax)
# pointer to buffer min = ctypes.byref(bufferBMin)
# buffer length = maxSamples
# ratio mode = PS6000_RATIO_MODE_NONE = 0
status["setDataBuffersB"] = ps.ps6000SetDataBuffers(chandle, 1, ctypes.byref(bufferBMax), ctypes.byref(bufferBMin), maxSamples, 0)

# create overflow loaction
overflow = ctypes.c_int16()
# create converted type maxSamples
cmaxSamples = ctypes.c_int32(maxSamples)

# Retried data from scope to buffers assigned above
# handle = chandle
# start index = 0
# pointer to number of samples = ctypes.byref(cmaxSamples)
# downsample ratio = 1
# downsample ratio mode = PS6000_RATIO_MODE_NONE
# pointer to overflow = ctypes.byref(overflow))
status["getValues"] = ps.ps6000GetValues(chandle, 0, ctypes.byref(cmaxSamples), 1, 0, 0, ctypes.byref(overflow))

# find maximum ADC count value
# handle = chandle
# pointer to value = ctypes.byref(maxADC)
maxADC = ctypes.c_int16(32512)

# convert ADC counts data to mV
adc2mVChAMax =  adc2mV(bufferAMax, chARange, maxADC)
adc2mVChBMax =  adc2mV(bufferBMax, chBRange, maxADC)

# Create time data
time = np.linspace(0, (cmaxSamples.value) * timeIntervalns.value, cmaxSamples.value)

# plot data from channel A and B
plt.plot(time, adc2mVChAMax[:])
plt.plot(time, adc2mVChBMax[:])
plt.xlabel('Time (ns)')
plt.ylabel('Voltage (mV)')
plt.show()

# display status returns
print(status)

# Close unitDisconnect the scope
# handle = chandle
ps.ps6000CloseUnit(chandle)