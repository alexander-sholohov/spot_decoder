#!/usr/bin/env python

#
# Author: Alexander Sholohov <ra9yer@yahoo.com>
#
# License: MIT
#

import sys
import os
import re
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
def utc_time_15s_rounded():
    x = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
    discard = datetime.timedelta(seconds=(x.second % 15),  microseconds=x.microsecond)
    return x - discard

#--------------------------------------------
def doPOST(url, src, magicKey, mode, utcTime, dbRatio, dtShift, freq, message):
    if not url:
        return
        
    rec = {}
    rec['mode'] = mode
    rec['utc_time'] = utcTime
    rec['db_ratio'] = dbRatio
    rec['dt_shift'] = dtShift
    rec['freq'] = freq
    rec['src'] = src
    rec['magic_key'] = magicKey
    rec['message'] = message

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
def is_callsign(s):
    m = re.search('^[A-Z]{1,2}[0-9][A-Z]{1,3}$', s)
    return m != None

#--------------------------------------------
def is_valid_callsign_in_array(arr):
    for s in arr:
        if not is_callsign(s):
            continue

        for elm in cfg.CALLSIGN_PREFIXES:
            if s.startswith(elm):
                return True
    return False

#--------------------------------------------
def decoder_proc(waveName, utcTime, outBaseName):
    decodeStartedStamp = datetime.datetime.now()
    if not os.path.isfile(waveName):
        print 'File {} not exist'.format(waveName)
        return
        # raise Exception('File {} not exist'.format(waveName))
    print "Decoding {0}...".format(waveName)

    occupiedFileNames = {}

    prepareToSend = []

    for mode, isFilterNeeded, cmdLine, parser in cfg.DECODER_CHAIN:
        print "Process mode: ", mode, isFilterNeeded
        fullCmdLine = cmdLine + [waveName]
        print "fullCmdLine=", fullCmdLine
        p = subprocess.Popen(fullCmdLine, shell=False, stdout=subprocess.PIPE)

        outdata, errdata = p.communicate()
        if errdata:
            print "errdata=", errdata
        print "OutData=", outdata

        validLineFound = False
        for line in StringIO.StringIO(outdata):
            params = parser(line)
            if not params['is_valid']:
                continue

            # check for empty message
            if not params['message'].strip():
                continue

            validLineFound = True
            if 'utc_time' in params:
                utcPrintableTime = params['utc_time']
            else:
                utcPrintableTime = utcTime.strftime("%H%M%S") if mode.startswith("msk") else utcTime.strftime("%H%M")

            itemToSend = (mode, utcPrintableTime, params['snr'].strip(), params['drift'].strip(), params['freq'].strip(), params['message'].strip())

            if not isFilterNeeded or is_valid_callsign_in_array(params['message'].split()):
                prepareToSend.append(itemToSend)

        if validLineFound and cfg.KEEP_DECODED_RESULT:
            for suffix in ["", "-1", "-2", "-3", "-4", "-5", "-6"]:
                fname = "{}-{}{}.txt".format(outBaseName, mode, suffix)
                if fname not in occupiedFileNames:
                    break

            occupiedFileNames[fname] = 1
            with open(fname, "w") as fv:
                fv.write(outdata)


    # remove duplicates
    newPrepareToSend = [elm for n,elm in enumerate(prepareToSend) if elm not in prepareToSend[:n]]

    # post
    for item in newPrepareToSend:
        print "Publish to {0}; item={1}".format(cfg.HTTP_SPOT_URI, item)
        mode, utcPrintableTime, dbRatio, dtShift, freq, message = item
        doPOST(cfg.HTTP_SPOT_URI, cfg.SRC, cfg.POST_MAGIC_KEY, mode, utcPrintableTime, dbRatio, dtShift, freq, message)

    # save flac
    if len(newPrepareToSend)>0 and cfg.KEEP_DECODED_RESULT:
        # compress
        print "Compress flac..."
        p = subprocess.Popen([cfg.FLAC_CMD, waveName], shell=False, stdout=subprocess.PIPE)
        p.communicate()

    # delete original wav file
    if hasattr(cfg, "KEEP_WAV_FILES") and cfg.KEEP_WAV_FILES:
        print "Keep wav file"
    else:
        print "Remove wav file"
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
            
            s = int(dStart.minute * 60.0 + dStart.second + dStart.microsecond / 1000000.0 + cfg.LEAD_START_IN_SECONDS)
            if s % int(cfg.START_INTERVAL_IN_SECONDS) == 0:
                break

            time.sleep(0.1)
            cnt += 1
            if cnt % 50 == 0:
                print "second=", dStart.second

        print "Started at {0}".format( str(dStart) )

        utcTime = utc_time_15s_rounded()
        if isfunction(cfg.WORKING_DIR):
            dirName = cfg.WORKING_DIR(utcTime)
        else:
            dirName = cfg.WORKING_DIR
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        baseName = cfg.BASE_FILE_NAME(dirName, dStart, utcTime)
        rawName = baseName + ".raw"
        waveName = baseName + ".wav"

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
            if cnt % 20 == 0:
                print "seconds writed =", diff.total_seconds()
            time.sleep(0.25)
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
        print "waveName=", waveName

        t1 = threading.Thread(target=decoder_proc, args=(waveName, utcTime, baseName))
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

