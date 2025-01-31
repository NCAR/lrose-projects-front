#!/usr/bin/env python

#===========================================================================
#
# Produce plots for ZDR bias from clutter
#
#===========================================================================

from __future__ import print_function

import os
import sys
import subprocess
from optparse import OptionParser
import numpy as np
from numpy import convolve
from numpy import linalg, array, ones
import matplotlib.pyplot as plt
from matplotlib import dates
import math
import datetime
import contextlib

def main():

#   globals

    global options
    global debug
    global startTime
    global endTime

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
    parser.add_option('--cm_file',
                      dest='cmFilePath',
                      default='../data/pecan/clut_mon.spol.qc.txt',
                      help='ClutMon results file path')
    parser.add_option('--cp_file',
                      dest='cpFilePath',
                      default='../data/pecan/spol_pecan_CP_analysis_20150524_000021.txt',
                      help='CP results file path')
    parser.add_option('--bias_file',
                      dest='biasFilePath',
                      default='../data/pecan/spol_zdr_bias_in_snow.txt',
                      help='File path for bias results')
    parser.add_option('--title',
                      dest='title',
                      default='ZDR BIAS FROM CLUTTER',
                      help='Title for plot')
    parser.add_option('--width',
                      dest='figWidthMm',
                      default=400,
                      help='Width of figure in mm')
    parser.add_option('--height',
                      dest='figHeightMm',
                      default=320,
                      help='Height of figure in mm')
    parser.add_option('--lenMean',
                      dest='lenMean',
                      default=11,
                      help='Len of moving mean filter')
    parser.add_option('--start',
                      dest='startTime',
                      default='2015 06 20 00 00 00',
                      help='Start time for plot')
    parser.add_option('--end',
                      dest='endTime',
                      default='2015 07 16 00 00 00',
                      help='End time for plot')
    
    (options, args) = parser.parse_args()
    
    if (options.verbose == True):
        options.debug = True

    year, month, day, hour, minute, sec = options.startTime.split()
    startTime = datetime.datetime(int(year), int(month), int(day),
                                  int(hour), int(minute), int(sec))

    year, month, day, hour, minute, sec = options.endTime.split()
    endTime = datetime.datetime(int(year), int(month), int(day),
                                int(hour), int(minute), int(sec))

    if (options.debug == True):
        print("Running %prog", file=sys.stderr)
        print("  cmFilePath: ", options.cmFilePath, file=sys.stderr)
        print("  cpFilePath: ", options.cpFilePath, file=sys.stderr)
        print("  biasFilePath: ", options.biasFilePath, file=sys.stderr)
        print("  startTime: ", startTime, file=sys.stderr)
        print("  endTime: ", endTime, file=sys.stderr)

    # read in column headers for clutter monitoring results

    iret, cmHdrs, cmData = readColumnHeaders(options.cmFilePath)
    if (iret != 0):
        sys.exit(-1)

    # read in data for clutter monitoring results

    cmData, cmTimes = readInputData(options.cmFilePath, cmHdrs, cmData)

    # read in column headers for bias results

    iret, biasHdrs, biasData = readColumnHeaders(options.biasFilePath)
    if (iret != 0):
        sys.exit(-1)

    # read in data for bias results

    biasData, biasTimes = readInputData(options.biasFilePath, biasHdrs, biasData)

    # read in column headers for CP results

    iret, cpHdrs, cpData = readColumnHeaders(options.cpFilePath)
    if (iret != 0):
        sys.exit(-1)

    # read in data for CP results

    cpData, cpTimes = readInputData(options.cpFilePath, cpHdrs, cpData)

    # render the plot
    
    doPlot(biasData, biasTimes, cpData, cpTimes, cmData, cmTimes)

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

    obsTimes = []
    colData = {}
    for index, var in enumerate(colHeaders, start=0):
        colData[var] = []

   # read in a line at a time, set colData
    for line in lines:
        
        commentIndex = line.find("#")
        if (commentIndex >= 0):
            continue
            
        # data
        
        data = line.strip().split()
        if (len(data) != len(colHeaders)):
            if (options.debug == True):
                print("skipping line: ", line, file=sys.stderr)
            continue;

        values = {}
        for index, var in enumerate(colHeaders, start=0):
            if (var == 'count' or var == 'obsNum' or \
                var == 'year' or var == 'month' or var == 'day' or \
                var == 'hour' or var == 'min' or var == 'sec' or \
                var == 'nDbzStrong' or var == 'nDbmhcStrong' or \
                var == 'nDbmvcStrong' or var == 'nDbmhxStrong' or \
                var == 'nDbmvxStrong' or var == 'nZdrStrong' or \
                var == 'nXpolrStrong' or \
                var == 'nDbzWeak' or var == 'nDbmhcWeak' or \
                var == 'nDbmvcWeak' or var == 'nDbmhxWeak' or \
                var == 'nDbmvxWeak' or var == 'nZdrWeak' or \
                var == 'nXpolrWeak' or \
                var == 'unix_time'):
                values[var] = int(data[index])
            elif (var == 'fileName' or var == 'volTime'):
                values[var] = data[index]
            else:
                values[var] = float(data[index])

        # load observation times array

        year = values['year']
        month = values['month']
        day = values['day']
        hour = values['hour']
        minute = values['min']
        sec = values['sec']

        thisTime = datetime.datetime(year, month, day,
                                     hour, minute, sec)

        if (thisTime >= startTime and thisTime <= endTime):
            for index, var in enumerate(colHeaders, start=0):
                colData[var].append(values[var])
            obsTimes.append(thisTime)

    fp.close()

    return colData, obsTimes

########################################################################
# Moving average filter

def movingAverage(values, window):

    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'same')
    return sma

########################################################################
# Plot

def doPlot(biasData, biasTimes, cpData, cpTimes, cmData, cmTimes):

    fileName = options.biasFilePath
    titleStr = "File: " + fileName
    hfmt = dates.DateFormatter('%y/%m/%d')

    lenMeanFilter = int(options.lenMean)

    #   set up np arrays

    btimes = np.array(biasTimes).astype(datetime.datetime)

    biasMean = np.array(biasData["ZdrBiasMean"]).astype(np.double)
    biasMean = movingAverage(biasMean, lenMeanFilter)

    biasPercent15 = np.array(biasData["ZdrBiasPercentile15"]).astype(np.double)
    biasPercent15 = movingAverage(biasPercent15, lenMeanFilter)

    biasPercent20 = np.array(biasData["ZdrBiasPercentile20"]).astype(np.double)
    biasPercent20 = movingAverage(biasPercent20, lenMeanFilter)

    biasPercent25 = np.array(biasData["ZdrBiasPercentile25"]).astype(np.double)
    biasPercent25 = movingAverage(biasPercent25, lenMeanFilter)

    biasPercent33 = np.array(biasData["ZdrBiasPercentile33"]).astype(np.double)
    biasPercent33 = movingAverage(biasPercent33, lenMeanFilter)

    validMean = np.isfinite(biasMean)
    validPercent15 = np.isfinite(biasPercent15)
    validPercent20 = np.isfinite(biasPercent20)
    validPercent25 = np.isfinite(biasPercent25)
    validPercent33 = np.isfinite(biasPercent33)

    ctimes = np.array(cpTimes).astype(datetime.datetime)
    ZdrmVert = np.array(cpData["ZdrmVert"]).astype(np.double)
    validZdrmVert = np.isfinite(ZdrmVert)
    
    SunscanZdrm = np.array(cpData["SunscanZdrm"]).astype(np.double)
    validSunscanZdrm = np.isfinite(SunscanZdrm)

    # ZDR from strong clutter

    zdrStrong = np.array(cmData["meanZdrStrong"]).astype(np.double)
    zdrStrong = movingAverage(zdrStrong, lenMeanFilter)
    ztimes = np.array(cmTimes).astype(datetime.datetime)

    # remove end points

    lenBy2 = lenMeanFilter / 2 + 1
    zdrStrong = zdrStrong[lenBy2:-lenBy2]
    validZdrStrong = np.isfinite(zdrStrong)
    ztimes = ztimes[lenBy2:-lenBy2]

    # ax4 - Site Temperature

    cptimes = np.array(cpTimes).astype(datetime.datetime)
    tempSite = np.array(cpData["TempSite"]).astype(np.double)
    validTempSite = np.isfinite(tempSite)

    #validBtimes = btimes[validPercent20]
    #validBiases = biasPercent20[validPercent20]
    
    validBtimes = ztimes[validZdrStrong]
    validBiases = zdrStrong[validZdrStrong]
    
    tempVals = []
    biasVals = []

    for ii, biasVal in enumerate(validBiases, start=0):
        btime = validBtimes[ii]
        if (btime >= startTime and btime <= endTime):
            tempTime, tempVal = getClosestTemp(btime, cptimes, tempSite)
            if (np.isfinite(tempVal)):
                tempVals.append(tempVal)
                biasVals.append(biasVal)
                if (options.verbose):
                    print("==>> biasTime, biasVal, tempTime, tempVal:", \
                        btime, biasVal, tempTime, tempVal, file=sys.stderr)

    # linear regression bias vs temp

    A = array([tempVals, ones(len(tempVals))])
    ww = linalg.lstsq(A.T, biasVals)[0] # obtaining the fit, ww[0] is slope, ww[1] is intercept
    regrX = []
    regrY = []
    minTemp = min(tempVals)
    maxTemp = max(tempVals)
    regrX.append(minTemp)
    regrX.append(maxTemp)
    regrY.append(ww[0] * minTemp + ww[1])
    regrY.append(ww[0] * maxTemp + ww[1])
    
    # set up plots

    widthIn = float(options.figWidthMm) / 25.4
    htIn = float(options.figHeightMm) / 25.4

    fig1 = plt.figure(1, (widthIn, htIn))
    fig2 = plt.figure(2, (widthIn/2, htIn/2))

    ax1 = fig1.add_subplot(2,1,1,xmargin=0.0)
    ax2 = fig1.add_subplot(2,1,2,xmargin=0.0)

    ax3 = fig2.add_subplot(1,1,1,xmargin=1.0, ymargin=1.0)
    #ax3 = fig2.add_subplot(1,1,1,xmargin=0.0)

    oneDay = datetime.timedelta(1.0)
    ax1.set_xlim([btimes[0] - oneDay, btimes[-1] + oneDay])
    ax1.set_title("ZDR bias from clutter, SPOL, PECAN")
    ax2.set_xlim([btimes[0] - oneDay, btimes[-1] + oneDay])
    ax2.set_title("Site temperature (C)")

    # ax1.plot(btimes[validPercent20], biasPercent20[validPercent20], \
    #          "ro", label = 'ZDR Bias percentile 20', linewidth=1)

    # ax1.plot(btimes[validPercent20], biasPercent20[validPercent20], \
    #          label = 'ZDR Bias percentile 20', linewidth=1, color='red')

    # ax1.plot(ctimes[validSunscanZdrm], SunscanZdrm[validSunscanZdrm], \
    #          linewidth=2, label = 'Zdrm Sun/CP (dB)', color = 'green')
    
    # ax1.plot(ctimes[validZdrmVert], ZdrmVert[validZdrmVert], \
    #          "^", markersize=10, linewidth=1, label = 'Zdrm Vert (dB)', color = 'yellow')

    ax1.plot(ztimes[validZdrStrong], zdrStrong[validZdrStrong], \
             "o", label = 'ZDR Bias clutter', color='red')

    ax1.plot(ztimes[validZdrStrong], zdrStrong[validZdrStrong], \
             label = 'ZDR Bias clutter', linewidth=2, color='red')


    ax2.plot(cptimes[validTempSite], tempSite[validTempSite], \
             linewidth=1, label = 'Site Temp', color = 'blue')

    configDateAxis(ax1, -9999, 9999, "ZDR Bias (dB)", 'upper right')
    configDateAxis(ax2, -9999, 9999, "Temp (C)", 'upper right')
    label3 = "ZDR Bias = " + ("%.5f" % ww[0]) + " * temp + " + ("%.3f" % ww[1])
    ax3.plot(tempVals, biasVals, 
             "x", label = label3, color = 'blue')
    ax3.plot(regrX, regrY, linewidth=3, color = 'blue')
    
    legend3 = ax3.legend(loc="upper left", ncol=2)
    for label3 in legend3.get_texts():
        label3.set_fontsize(12)
    ax3.set_xlabel("Site temperature (C)")
    ax3.set_ylabel("Clutter ZDR Bias (dB)")
    ax3.grid(True)
    ax3.set_ylim([-3.0, 0.0])
    ax3.set_xlim([minTemp - 1, maxTemp + 1])

    fig2.suptitle("Clutter ZDR bias Vs Temp, SPOL, PECAN", fontsize=16)
    timeTitle = str(startTime) + " - " + str(endTime)
    ax3.set_title(timeTitle, fontsize=12)

    fig1.autofmt_xdate()

    fig1.tight_layout()
    fig1.subplots_adjust(bottom=0.05, left=0.06, right=0.97, top=0.95)

    fig2.tight_layout()
    fig2.subplots_adjust(bottom=0.07, left=0.1, right=0.95, top=0.9)

    plt.show()

########################################################################
# initialize legends etc

def configDateAxis(ax, miny, maxy, ylabel, legendLoc):
    
    legend = ax.legend(loc=legendLoc, ncol=6)
    for label in legend.get_texts():
        label.set_fontsize('x-small')
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    ax.grid(True)
    if (miny > -9990 and maxy > -9990):
        ax.set_ylim([miny, maxy])
    hfmt = dates.DateFormatter('%y/%m/%d')
    ax.xaxis.set_major_locator(dates.DayLocator())
    ax.xaxis.set_major_formatter(hfmt)
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(8) 

########################################################################
# get temp closest in time to the search time

def getClosestTemp(biasTime, tempTimes, obsTemps):

    twoHours = datetime.timedelta(0.0, 7200.0)

    validTimes = ((tempTimes > (biasTime - twoHours)) & \
                  (tempTimes < (biasTime + twoHours)))

    if (len(validTimes) < 1):
        return (biasTime, float('NaN'))
    
    searchTimes = tempTimes[validTimes]
    searchTemps = obsTemps[validTimes]

    if (len(searchTimes) < 1 or len(searchTemps) < 1):
        return (biasTime, float('NaN'))

    minDeltaTime = 1.0e99
    ttime = searchTimes[0]
    temp = searchTemps[0]
    for ii, temptime in enumerate(searchTimes, start=0):
        deltaTime = math.fabs((temptime - biasTime).total_seconds())
        if (deltaTime < minDeltaTime):
            minDeltaTime = deltaTime
            temp = searchTemps[ii]
            ttime = temptime

    return (ttime, temp)

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

