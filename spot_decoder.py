#!/usr/bin/env python

#
# Author: Alexander Sholohov <ra9yer@yahoo.com>
#
# License: MIT
#

import sys
import os
import subprocess
import signal
import time
import datetime
import wave
import StringIO
import threading
import httplib, urllib
import urlparse
from inspect import isfunction

#--------------------------------------------
def split_params(line):
    pos = line.find("#")
    if pos == -1:
        return (None, None)

    lArr = line[:pos].split()
    rArr = line[pos+1:].split()
    return (lArr, rArr)

#--------------------------------------------
def is_seconds_in_range(d, timeFrame):
    (sFrom, sTo) = timeFrame
    x = d.second + d.microsecond / 1000000.0
    if (sFrom <= x) and (x <= sTo):
        return True
    x += 60.0
    if (sFrom <= x) and (x <= sTo):
        return True

    return False

#--------------------------------------------
def seconds_before_range(d, timeFrame):
    (sFrom, sTo) = timeFrame
    x = d.second + d.microsecond / 1000000.0
    return (sFrom - x) if x < sFrom else (sFrom + 60 - x)

#--------------------------------------------
def is_even_minute(d):
    shift = datetime.timedelta(seconds=cfg.ROUND_TO_MINUTE_IN_SECONDS)
    d2 = d + shift
    return d2.minute % 2 == 0

#--------------------------------------------
def utc_time_minute_rounded():
    x = datetime.datetime.utcnow() + datetime.timedelta(seconds=cfg.ROUND_TO_MINUTE_IN_SECONDS)
    discard = datetime.timedelta(seconds=x.second,  microseconds=x.microsecond)
    return x - discard

#--------------------------------------------
def doPOST(url, mode, lArr, rArr):
    if not url:
        return
        
    rec = {}
    rec['mode'] = mode
    rec['utc_time'] = lArr[0]
    rec['db_ratio'] = lArr[1]
    rec['dt_shift'] = lArr[2]
    rec['freq'] = lArr[3]
    rec['message'] = " ".join(rArr)

    params = urllib.urlencode(rec)
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}

    netparam = urlparse.urlparse(url)

    conn = httplib.HTTPConnection(netparam.netloc)
    conn.request("POST", netparam.path, params, headers)
    response = conn.getresponse()
    print response.status, response.reason
    data = response.read()
    print data
    conn.close()



#--------------------------------------------
def decoder_proc(waveName, outName):
    decodeStartedStamp = datetime.datetime.now()
    print "Decoding {0}...".format(waveName)

    needSaveFlac = False

    for mode, cmdLine in cfg.DECODER_CHAIN:
        print "Process mode: ", mode
        fullCmdLine = cmdLine + [waveName]
        p = subprocess.Popen(fullCmdLine, shell=False, stdout=subprocess.PIPE)

        outdata, errdata = p.communicate()
        if errdata:
            print "errdata=", errdata
        print "OutData=", outdata

        needProcess = False
        for line in StringIO.StringIO(outdata):
            lArr, rArr = split_params(line)
            if rArr:
                needProcess = True
                needSaveFlac = True

        if needProcess:
            if cfg.KEEP_DECODED_RESULT:
                with open(outName, "w") as fv:
                    fv.write(outdata)

            print "Will publish to {0}".format(cfg.HTTP_SPOT_URI)
            
            for line in StringIO.StringIO(outdata):
                lArr, rArr = split_params(line)
                if rArr:
                    doPOST(cfg.HTTP_SPOT_URI, mode, lArr, rArr)

        else:
            print "No data present. Skip saving result."


    if needSaveFlac and cfg.KEEP_DECODED_RESULT:
        # compress
        print "Compress flac..."
        p = subprocess.Popen([cfg.FLAC_CMD, waveName], shell=False, stdout=subprocess.PIPE)
        p.communicate()

    # delete original wav file
    os.remove(waveName)

    decodeEndedStamp = datetime.datetime.now()

    diff = decodeEndedStamp - decodeStartedStamp
    print "Done. decode_duration={0}".format(diff.total_seconds())


#--------------------------------------------
def main():
    
    while(True):

        # wait begin of minute (actual 5x second)
        print "Wait for start..."
        cnt = 0
        while True:
            dStart = datetime.datetime.now()
            
            isOtherCondtionsOk = (not cfg.START_ONLY_AT_EVEN_MINUTE or is_even_minute(dStart))
            if isOtherCondtionsOk and is_seconds_in_range(dStart, cfg.START_WINDOW):
                break

            if isOtherCondtionsOk and seconds_before_range(dStart, cfg.START_WINDOW) < 2.0:
                time.sleep(0.1)
            else:
                if cnt % 5 == 0:
                    print "second=", dStart.second
                time.sleep(1)
                cnt += 1

        print "Started at {0}".format( str(dStart) )

        utcTime = utc_time_minute_rounded()
        if isfunction(cfg.WORKING_DIR):
            dirName = cfg.WORKING_DIR(utcTime)
        else:
            dirName = cfg.WORKING_DIR
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        baseName =  "{0}/{1}_{2}".format( dirName, dStart.strftime("%Y%m%d%H%M%S"), utcTime.strftime("%H%M") )
        rawName = baseName + ".raw"
        waveName = baseName + ".wav"
        outName = baseName + ".txt"


        fv = open(rawName, "wb")
        print "Start write to {0}".format(rawName)


        cn = []
        for item in cfg.CMD_CHAIN:
            if len(cn) == 0:
                p = subprocess.Popen(item, shell=False, stdout=subprocess.PIPE )  # first
            elif len(cn) == len(cfg.CMD_CHAIN) - 1 :
                p = subprocess.Popen(item, shell=False, stdin=cn[-1].stdout, stdout=fv)  # last
            else:
                p = subprocess.Popen(item, shell=False, stdin=cn[-1].stdout, stdout=subprocess.PIPE) # middle
                
            cn.append(p)

        print "Writing...Wait for end record..."

        cnt = 0
        while True:
            dCurr = datetime.datetime.now()
            diff = dCurr - dStart
            if diff.total_seconds() > cfg.RECORD_DURATION_IN_SECONDS:
                break
            if cnt % 10 == 0:
                print "seconds elapsed =", diff.total_seconds()
            time.sleep(0.8)
            cnt += 1

        print "Terminating..."
        # kill entire chain
        os.kill(cn[0].pid, signal.SIGTERM)
        for item in cn:
            item.wait()

        print "Record ended."

        numBytes = fv.tell()
        fv.close()

        # prepend wav header
        with open(waveName, "wb") as dst, open(rawName, "rb") as fv:
            w = wave.Wave_write(dst)
            w.setparams((1, 2, cfg.AUDIO_SAMPLE_RATE, numBytes/2, 'NONE', 'NONE'))
            w.writeframesraw(fv.read())
            w.close()

        os.remove(rawName) # delete raw file


        t1 = threading.Thread(target=decoder_proc, args=(waveName, outName))
        t1.start()



#--------------------------------------------
if __name__ == '__main__':

    # === Load configuration script ===
    if len(sys.argv)==1:
        config_script = 'spot_cfg'
    else:
        config_script = sys.argv[1]
    print "use config script {0}.py".format(config_script)
    cfg = __import__(config_script)

    main()

