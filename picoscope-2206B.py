# This script opens a 2206B driver device, sets up both channels and a trigger then collects a block of data.
# This data is then plotted as mV against time in us.

import ctypes
import numpy as np
from picosdk.ps2000a import ps2000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok
import csv
from datetime import datetime
from itertools import zip_longest
import os.path
from math import log
import time

# Specify sampling frequency
SAMPLING_FREQUENCY = 500e3 # Hz
if SAMPLING_FREQUENCY >= 125e6:
    timebase = round(log(500e6/SAMPLING_FREQUENCY,2))
    print('Sampling frequency: {:,}'.format(1/(2**timebase/5)*1e8) + ' Hz')
else:
    timebase=round(62.5e6/SAMPLING_FREQUENCY+2)
    print('Sampling frequency: {:,}'.format(62.5e6/(timebase-2)) + ' Hz')

# Specify acquisition time
ACQUISITION_TIME = 1 # s
samplingInterval = 1/SAMPLING_FREQUENCY
totalSamples = round(ACQUISITION_TIME/samplingInterval)
print('Number of total samples (for each channel): {:,}'.format(totalSamples))
# Buffer memory size: 32 M


# Create chandle and status ready for use.
# The c_int16 constructor accepts an optional integer initializer. Default: 0.
chandle = ctypes.c_int16()
status = {}

# Open 2000 series PicoScope
print('Setting up PiscoScope 2206B unit...')
# Returns handle to chandle for use in future API functions
# First argument: number that uniquely identifies the scope (address of chandle)
# Second argument:  first scope found (None)
status["openunit"] = ps.ps2000aOpenUnit(ctypes.byref(chandle), None)
# If any error, the following line will raise one.
assert_pico_ok(status["openunit"])

# Set up channel A
# handle = chandle
# channel = PS2000A_CHANNEL_A = 0
# enabled = 1
# coupling type = PS2000A_DC = 1
# range = PS2000A_2V = 7
# analogue offset = -2 V = -2
chARange = 7
status["setChA"] = ps.ps2000aSetChannel(chandle, 0, 1, 1, chARange, 0)
assert_pico_ok(status["setChA"])
# Set up channel B
# handle = chandle
# channel = PS2000A_CHANNEL_B = 1
# enabled = 1
# coupling type = PS2000A_DC = 1
# range = PS2000A_2V = 7
# analogue offset = 0 V
chBRange = 7
status["setChB"] = ps.ps2000aSetChannel(chandle, 1, 1, 1, chBRange, 0)
assert_pico_ok(status["setChB"])

# Set up single trigger
# handle = chandle
# enabled = 1
# source = PS2000A_CHANNEL_A = 0
# threshold = 1024 ADC counts
# direction = PS2000A_RISING = 2
# delay = 0 sample periods
# auto Trigger = 1000 ms (if no trigger events occurs)
status["trigger"] = ps.ps2000aSetSimpleTrigger(chandle, 1, 0, 1024, 2, 0, 1000)
assert_pico_ok(status["trigger"])
# Set number of pre and post trigger samples to be collected
preTriggerSamples = round(totalSamples/2)
postTriggerSamples = totalSamples-preTriggerSamples
# Get timebase information
# handle = chandle
# timebase: obtained by samplingFrequency (sample interval formula: (timebase-2)*16 ns [for timebase>=3])
# noSamples = totalSamples
# pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalNs)
# oersample: not used, just initialized
# pointer to totalSamples = ctypes.byref(returnedMaxSamples)
# segment index = 0 (index of the memory segment to use, only 1 segment by default)
timeIntervalns = ctypes.c_float()
returnedMaxSamples = ctypes.c_int32()
oversample = ctypes.c_int16(0)
status["getTimebase2"] = ps.ps2000aGetTimebase2(chandle,
                                                timebase,
                                                totalSamples,
                                                ctypes.byref(timeIntervalns),
                                                oversample,
                                                ctypes.byref(returnedMaxSamples),
                                                0)
assert_pico_ok(status["getTimebase2"])
print('Done.')

# Block sampling mode
# The scope stores data in internal buffer memory and then transfer it to the PC via USB.
# The data is lost when a new run is started in the same segment.
# For PicoScope 2206B the buffer memory is 32 MS, maximum sampling rate 500 MS/s.
print('Running block capture...')
# Run block capture
# handle = chandle
# number of pre-trigger samples = preTriggerSamples
# number of post-trigger samples = PostTriggerSamples
# timebase (already defined when using ps2000aGetTimebase2)
# oversample: not used
# time indisposed ms = None (not needed, it's the time the scope will spend collecting samples)
# segment index = 0 (the only one defined by default, this index is zero-based)
# lpReady = None (using ps2000aIsReady rather than ps2000aBlockReady; callback functions that the driver will call when the data has been collected).
# pParameter = None (void pointer passed to ps2000aBlockReady() to return arbitrary data to the application)
status["runBlock"] = ps.ps2000aRunBlock(chandle,
                                        preTriggerSamples,
                                        postTriggerSamples,
                                        timebase,
                                        oversample,
                                        None,
                                        0,
                                        None,
                                        None)
assert_pico_ok(status["runBlock"])

# Check for data collection to finish using ps2000aIsReady
ready = ctypes.c_int16(0)
check = ctypes.c_int16(0)
while ready.value == check.value:
    status["isReady"] = ps.ps2000aIsReady(chandle, ctypes.byref(ready))

# Create buffers ready for assigning pointers for data collection
bufferAMax = (ctypes.c_int16 * totalSamples)()
bufferAMin = (ctypes.c_int16 * totalSamples)() # used for downsampling which isn't in the scope of this example
bufferBMax = (ctypes.c_int16 * totalSamples)()
bufferBMin = (ctypes.c_int16 * totalSamples)() # used for downsampling which isn't in the scope of this example

# Set data buffer location for data collection from channel A
# handle = chandle
# source = PS2000A_CHANNEL_A = 0
# pointer to buffer max = ctypes.byref(bufferDPort0Max)
# pointer to buffer min = ctypes.byref(bufferDPort0Min)
# buffer length = totalSamples
# segment index = 0
# ratio mode = PS2000A_RATIO_MODE_NONE = 0
status["setDataBuffersA"] = ps.ps2000aSetDataBuffers(chandle,
                                                     0,
                                                     ctypes.byref(bufferAMax),
                                                     ctypes.byref(bufferAMin),
                                                     totalSamples,
                                                     0,
                                                     0)
assert_pico_ok(status["setDataBuffersA"])

# Set data buffer location for data collection from channel B
# handle = chandle
# source = PS2000A_CHANNEL_B = 1
# pointer to buffer max = ctypes.byref(bufferBMax)
# pointer to buffer min = ctypes.byref(bufferBMin)
# buffer length = totalSamples
# segment index = 0
# ratio mode = PS2000A_RATIO_MODE_NONE = 0
status["setDataBuffersB"] = ps.ps2000aSetDataBuffers(chandle,
                                                     1,
                                                     ctypes.byref(bufferBMax),
                                                     ctypes.byref(bufferBMin),
                                                     totalSamples,
                                                     0,
                                                     0)
assert_pico_ok(status["setDataBuffersB"])

# Create overflow location
overflow = ctypes.c_int16()
# Create converted type totalSamples
cTotalSamples = ctypes.c_int32(totalSamples)

# Retrived data from scope to buffers assigned above
# handle = chandle
# start index = 0 (zero-based index, sample intervals from the start of the buffer)
# pointer to number of samples = ctypes.byref(cTotalSamples)
# downsample ratio = 0
# downsample ratio mode = PS2000A_RATIO_MODE_NONE (downsampling disabled)
# pointer to overflow = ctypes.byref(overflow))
status["getValues"] = ps.ps2000aGetValues(chandle, 0, ctypes.byref(cTotalSamples), 0, 0, 0, ctypes.byref(overflow))
assert_pico_ok(status["getValues"])


# find maximum ADC count value
# handle = chandle
# pointer to value = ctypes.byref(maxADC)
maxADC = ctypes.c_int16()
status["maximumValue"] = ps.ps2000aMaximumValue(chandle, ctypes.byref(maxADC))
assert_pico_ok(status["maximumValue"])

# convert ADC counts data to mV
adc2mVChAMax =  adc2mV(bufferAMax, chARange, maxADC)
adc2mVChBMax =  adc2mV(bufferBMax, chBRange, maxADC)

# Create time data
timeAxis = np.linspace(0, (cTotalSamples.value) * (timeIntervalns.value-1), cTotalSamples.value)
print('Done.')

# plot data from channel A and B
plt.plot(timeAxis, adc2mVChAMax[:])
plt.plot(timeAxis, adc2mVChBMax[:])
plt.xlabel('Time (ns)')
plt.ylabel('Voltage (mV)')
plt.show()

# Stop the scope
print('Closing the scope...')
# handle = chandle
status["stop"] = ps.ps2000aStop(chandle)
assert_pico_ok(status["stop"])
# Close unitDisconnect the scope
# handle = chandle
status["close"] = ps.ps2000aCloseUnit(chandle)
assert_pico_ok(status["close"])
print('Done.')
print(status)

# Save raw samples to .csv file (with timestamp)
startTime = time.time()
print('Saving raw samples to .csv file...')
timestamp = datetime.now().strftime("%Y%m%d_%I%M%S_%p")

samplesFileNameChA = timestamp + "_ChA.csv"
completeFileNameChA = os.path.join('../raw-samples',samplesFileNameChA)
with open(completeFileNameChA,'w') as file:
    writer = csv.writer(file)
    writer.writerows(zip(adc2mVChAMax,timeAxis))
    
samplesFileNameChB = timestamp + "_ChB.csv"
completeFileNameChB = os.path.join('../raw-samples',samplesFileNameChB)
with open(completeFileNameChB,'w') as file:
    writer = csv.writer(file)
    writer.writerows(zip(adc2mVChBMax,timeAxis))
elapsedTime = time.time() - startTime

print('Done. Elapsed time for .csv files generation: {:.1f}'.format(elapsedTime) + ' s.')