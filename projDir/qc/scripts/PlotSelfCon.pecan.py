#!/usr/bin/env python

#===========================================================================
#
# Produce plots for self consistency analysis
#
#===========================================================================

from __future__ import print_function

import os
import sys
import subprocess
from optparse import OptionParser
import numpy as np
from numpy import convolve
import matplotlib.pyplot as plt
from matplotlib import dates
import math
import datetime

def main():

#   globals

    global options
    global debug

# parse the command line

    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option('--debug',
                      dest='debug', default=False,
                      action="store_true",
                      help='Set debugging on')
    parser.add_option('--verbose',
                      dest='verbose', default=False,
                      action="store_true",
                      help='Set verbose debugging on')
    parser.add_option('--sc_file',
                      dest='scFilePath',
                      default='../data/pecan/self_con.spol_cal.txt',
                      help='Self consistency results file path')
    parser.add_option('--cp_file',
                      dest='cpFilePath',
                      default='../data/pecan/spol_pecan_CP_analysis_20150528_000553.txt',
                      help='CP results file path')
    parser.add_option('--title',
                      dest='title',
                      default='SELF CONSISTENCY FOR Z CHECK',
                      help='Title for plot')
    parser.add_option('--width',
                      dest='figWidthMm',
                      default=400,
                      help='Width of figure in mm')
    parser.add_option('--height',
                      dest='figHeightMm',
                      default=175,
                      help='Height of figure in mm')
    parser.add_option('--lenMean',
                      dest='lenMean',
                      default=1,
                      help='Len of moving mean filter')
    parser.add_option('--minElev',
                      dest='minElev',
                      default=1.25,
                      help='Minimum elevation angle (deg)')
    
    (options, args) = parser.parse_args()
    
    if (options.verbose == True):
        options.debug = True

    if (options.debug == True):
        print("Running %prog", file=sys.stderr)
        print("  scFilePath: ", options.scFilePath, file=sys.stderr)
        print("  cpFilePath: ", options.cpFilePath, file=sys.stderr)
        print("  lenMean: ", options.lenMean, file=sys.stderr)
        print("  minElev: ", options.minElev, file=sys.stderr)

    # read in column headers for self_con results

    iret, scHdrs, scData = readColumnHeaders(options.scFilePath)
    if (iret != 0):
        sys.exit(-1)

    # read in data for self_con results

    scData, scTimes = readInputData(options.scFilePath, scHdrs, scData)

    # read in column headers for CP results

    iret, cpHdrs, cpData = readColumnHeaders(options.cpFilePath)
    if (iret != 0):
        sys.exit(-1)

    # read in data for CP results

    cpData, cpTimes = readInputData(options.cpFilePath, cpHdrs, cpData)

    # render the plot
    
    doPlot(scData, scTimes, cpData, cpTimes)

    sys.exit(0)
    
########################################################################
# Read columm headers for the data
# this is in the first line

def readColumnHeaders(filePath):

    colHeaders = []
    colData = {}

    fp = open(filePath, 'r')
    line = fp.readline()
    fp.close()
    
    commentIndex = line.find("#")
    if (commentIndex == 0):
        # header
        colHeaders = line.lstrip("# ").rstrip("\n").split()
        if (options.debug == True):
            print("colHeaders: ", colHeaders, file=sys.stderr)
    else:
        print("ERROR - readColumnHeaders", file=sys.stderr)
        print("  First line does not start with #", file=sys.stderr)
        return -1, colHeaders, colData
    
    for index, var in enumerate(colHeaders, start=0):
        colData[var] = []
        
    return 0, colHeaders, colData

########################################################################
# Read in the data

def readInputData(filePath, colHeaders, colData):

    # open file

    fp = open(filePath, 'r')
    lines = fp.readlines()

    # read in a line at a time, set colData
    for line in lines:
        
        commentIndex = line.find("#")
        if (commentIndex >= 0):
            continue
            
        # data
        
        data = line.strip().split()

        for index, var in enumerate(colHeaders, start=0):
            if (var == 'count' or var == 'obsNum' or \
                var == 'year' or var == 'month' or var == 'day' or \
                var == 'hour' or var == 'min' or var == 'sec' or \
                var == 'startGate' or var == 'endGate' or \
                var == 'npairsClut' or var == 'npairsWx' or \
                var == 'unix_time'):
                colData[var].append(int(data[index]))
            elif (var == 'fileName' or var == 'rayTime'):
                colData[var].append(data[index])
            else:
                colData[var].append(float(data[index]))

    fp.close()

    # load observation times array

    year = colData['year']
    month = colData['month']
    day = colData['day']
    hour = colData['hour']
    minute = colData['min']
    sec = colData['sec']

    obsTimes = []
    for ii, var in enumerate(year, start=0):
        thisTime = datetime.datetime(year[ii], month[ii], day[ii],
                                     hour[ii], minute[ii], sec[ii])
        obsTimes.append(thisTime)

    return colData, obsTimes

########################################################################
# Moving average filter

def movingAverage(values, window):

    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'same')
    return sma

########################################################################
# Plot

def doPlot(scData, scTimes, cpData, cpTimes):

    widthIn = float(options.figWidthMm) / 25.4
    htIn = float(options.figHeightMm) / 25.4

    fig1 = plt.figure(1, (widthIn, htIn))
    ax1 = fig1.add_subplot(1,1,1,xmargin=0.0)
    ax1.plot(scTimes, np.zeros(len(scTimes)), linewidth=1, color = 'gray')
    
    fileName = options.scFilePath
    hfmt = dates.DateFormatter('%y/%m/%d')

    lenMeanFilter = int(options.lenMean)
    
    # transmit power

    cptimes = np.array(cpTimes).astype(datetime.datetime)
    timeStart1us = datetime.datetime(2015, 6, 8, 0, 0, 0)
    pwrCorrFlag = cptimes < timeStart1us
    pwrCorr = np.zeros(len(cptimes))
    pwrCorr[cptimes < timeStart1us] = -1.76

    TxPwrH = np.array(cpData["TxPwrH"]).astype(np.double)
    TxPwrH = movingAverage(TxPwrH, lenMeanFilter)
    TxPwrH = TxPwrH + pwrCorr - 87.5
    validTxPwrH = np.isfinite(TxPwrH)

    TxPwrV = np.array(cpData["TxPwrV"]).astype(np.double)
    TxPwrV = movingAverage(TxPwrV, lenMeanFilter)
    TxPwrV = TxPwrV + pwrCorr - 87.5
    validTxPwrV = np.isfinite(TxPwrV)

    ax1.plot(cptimes[validTxPwrH], TxPwrH[validTxPwrH], \
             label = 'TxPwrH - 87.5', linewidth=1, color='blue')

    ax1.plot(cptimes[validTxPwrV], TxPwrV[validTxPwrV], \
             label = 'TxPwrV - 87.5', linewidth=1, color='cyan')

    # self-consistency dbz bias

    sctimes = np.array(scTimes).astype(datetime.datetime)
    
    elevDeg = np.array(scData["elevationDeg"]).astype(np.double)

    biasArray = scData["dbzBias"]
    dbzBias = np.array(biasArray).astype(np.double)
    dbzBias = movingAverage(dbzBias, lenMeanFilter)
    validBias = np.isfinite(dbzBias) & (elevDeg > float(options.minElev))

    biasTimes = sctimes[validBias]
    validDbzBias = dbzBias[validBias]

    ax1.plot(biasTimes, validDbzBias, \
             "o", linewidth=1, label = 'DBZ bias (dB)', color = 'orange')
    
    # daily mean dbz bias
    
    #(dailyMeanTime, dailyMeanBias) = computeDailyStats(scTimes, biasArray)
    (dailyMeanTime, dailyMeanBias) = computeDailyStats(biasTimes, validDbzBias)

    ax1.plot(dailyMeanTime, dailyMeanBias, \
             linewidth=2, label = 'Daily mean bias (dB)', color = 'black')
    ax1.plot(dailyMeanTime, dailyMeanBias, \
             "^", label = 'Daily mean bias (dB)', color = 'black', markersize=12)

    for ii, dailyBias in enumerate(dailyMeanBias):
        tstr = "{0:.2f}".format(dailyBias)
        ax1.annotate(tstr,
                     xy=(dailyMeanTime[ii], dailyBias),
                     xytext=(dailyMeanTime[ii] + datetime.timedelta(0.25),
                             dailyBias + 0.02),
                     # arrowprops=dict(facecolor='gray', shrink=0.01),
                     fontsize=15)
        
    # Scott's results

    scottTimes = [ datetime.datetime(2015, 0o5, 29, 12, 00, 00), \
                   datetime.datetime(2015, 0o6, 12, 12, 00, 00), \
                   datetime.datetime(2015, 0o6, 15, 12, 00, 00), \
                   datetime.datetime(2015, 0o6, 26, 12, 00, 00), \
                   datetime.datetime(2015, 0o7, 0o2, 12, 00, 00) ]

    scottBias = [ -1.39, -1.26, 2.78, 1.40, 0.75 ]

    #ax1.plot(scottTimes, scottBias, \
    #         linewidth=2, label = 'Scott bias (dB)', color = 'red')
    #ax1.plot(scottTimes, scottBias, \
    #         "^", label = 'Scott bias (dB)', color = 'red', markersize=12)

    # mean bias for early and late parts of project
    
    startTime = datetime.datetime(2015, 0o5, 28, 0, 0, 0)
    endTime = datetime.datetime(2015, 0o6, 0o5, 0, 0, 0)
    meanBiasEarly = computePeriodStats(biasTimes, validDbzBias, startTime, endTime)
    print("Mean bias early, May 28 - June 5: ", meanBiasEarly, file=sys.stderr)

    startTime = datetime.datetime(2015, 0o6, 14, 0, 0, 0)
    endTime = datetime.datetime(2015, 0o7, 17, 0, 0, 0)
    meanBiasLate = computePeriodStats(biasTimes, validDbzBias, startTime, endTime)
    print("Mean bias late, June 14 - July 17: ", meanBiasLate, file=sys.stderr)

    meanTimes =  [ datetime.datetime(2015, 0o5, 28, 00, 00, 00), \
                   datetime.datetime(2015, 0o6, 0o5, 00, 00, 00), \
                   datetime.datetime(2015, 0o6, 14, 00, 00, 00), \
                   datetime.datetime(2015, 0o7, 17, 00, 00, 00) ]

    meanBias = [ meanBiasEarly, meanBiasEarly, meanBiasLate, meanBiasLate]

    ax1.plot(meanTimes, meanBias, \
             linewidth=2, label = 'Mean bias = (dB)', color = 'green')
    ax1.plot(meanTimes, meanBias, \
             "^", label = 'Mean bias (dB)', color = 'green', markersize=12)

    # legends, azes etc

    legend1 = ax1.legend(loc='upper right', ncol=7)
    for label in legend1.get_texts():
        label.set_fontsize('x-small')
    ax1.set_xlabel("Date")
    ax1.set_ylabel("DBZ BIAS / Xmit Pwr (dB)")
    ax1.grid(True)
    ax1.set_ylim([-3, 3])
    
    hfmt = dates.DateFormatter('%y/%m/%d')
    ax1.xaxis.set_major_locator(dates.DayLocator())
    ax1.xaxis.set_major_formatter(hfmt)
    
    for tick in ax1.xaxis.get_major_ticks():
        tick.label.set_fontsize(8) 

    titleStr = options.title
    titleStr = titleStr + " - min elev " + str(options.minElev) + " deg"
    fig1.suptitle(titleStr)
    fig1.autofmt_xdate()
    plt.tight_layout()
    fig1.subplots_adjust(bottom=0.10, left=0.06, right=0.97, top=0.94)
    plt.show()

########################################################################
# compute daily stats for a variable

def computeDailyStats(times, vals):

    dailyTimes = []
    dailyMeans = []

    nptimes = np.array(times).astype(datetime.datetime)
    npvals = np.array(vals).astype(np.double)

    validFlag = np.isfinite(npvals)
    timesValid = nptimes[validFlag]
    valsValid = npvals[validFlag]
    
    startTime = nptimes[0]
    endTime = nptimes[-1]
    
    startDate = datetime.datetime(startTime.year, startTime.month, startTime.day, 0, 0, 0)
    endDate = datetime.datetime(endTime.year, endTime.month, endTime.day, 0, 0, 0)

    oneDay = datetime.timedelta(1)
    halfDay = datetime.timedelta(0.5)
    
    thisDate = startDate
    while (thisDate < endDate + oneDay):
        
        nextDate = thisDate + oneDay
        result = []
        
        sum = 0.0
        sumDeltaTime = datetime.timedelta(0)
        count = 0.0
        for ii, val in enumerate(valsValid, start=0):
            thisTime = timesValid[ii]
            if (thisTime >= thisDate and thisTime < nextDate):
                sum = sum + val
                deltaTime = thisTime - thisDate
                sumDeltaTime = sumDeltaTime + deltaTime
                count = count + 1
                result.append(val)
        if (count > 5):
            mean = sum / count
            meanDeltaTime = datetime.timedelta(0, sumDeltaTime.total_seconds() / count)
            dailyMeans.append(mean)
            dailyTimes.append(thisDate + meanDeltaTime)
            # print >>sys.stderr, " daily time, meanStrong: ", dailyTimes[-1], meanStrong
            result.sort()
            
        thisDate = thisDate + oneDay

    return (dailyTimes, dailyMeans)


########################################################################
# compute daily means for dbz bias

def computePeriodStats(times, vals, startTime, endTime):

    nptimes = np.array(times).astype(datetime.datetime)
    npvals = np.array(vals).astype(np.double)
    
    validVals = np.isfinite(npvals)
    goodVals = npvals[validVals]
    goodTimes = nptimes[validVals]

    mean = 0.0
    sum = 0.0
    count = 0.0
    for ii, val in enumerate(goodVals, start=0):
        thisTime = goodTimes[ii]
        if (thisTime >= startTime and thisTime < endTime):
            sum = sum + val
            count = count + 1

    if (count > 1):
        mean = sum / count

    return mean
            
########################################################################
# Run a command in a shell, wait for it to complete

def runCommand(cmd):

    if (options.debug == True):
        print("running cmd:",cmd, file=sys.stderr)
    
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print("Child was terminated by signal: ", -retcode, file=sys.stderr)
        else:
            if (options.debug == True):
                print("Child returned code: ", retcode, file=sys.stderr)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)

########################################################################
# Run - entry point

if __name__ == "__main__":
   main()

