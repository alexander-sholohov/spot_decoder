
CSDR_CMD = './csdr'
MSK144_CMD = './msk144d2'
FLAC_CMD = 'flac'

# HTTP_SPOT_URI = 'http://192.168.1.200:9000/spotter/default/populate_spot'
HTTP_SPOT_URI = None


START_INTERVAL_IN_SECONDS = 15
LEAD_START_IN_SECONDS = 0.5
RECORD_DURATION_IN_SECONDS = 14

rfSampRate = 2048000
shift = str(float(145000000-144360000)/rfSampRate)
stage1SampRate = 32000
AUDIO_SAMPLE_RATE = 12000
decimation = str(2048000.0 / stage1SampRate)

CMD_CHAIN = []
CMD_CHAIN.append( ['nc', '192.168.1.200', '2223'] )
#CMD_CHAIN.append( ['cat', '/dev/urandom'] )
CMD_CHAIN.append( [CSDR_CMD, 'convert_u8_f']  )
CMD_CHAIN.append( [CSDR_CMD, 'shift_addition_cc', shift] )
CMD_CHAIN.append( [CSDR_CMD, 'fir_decimate_cc', decimation, '0.005', 'HAMMING'] )
CMD_CHAIN.append( [CSDR_CMD, 'bandpass_fir_fft_cc', '0', '0.12', '0.06'] )
CMD_CHAIN.append( [CSDR_CMD, 'realpart_cf'] )
CMD_CHAIN.append( [CSDR_CMD, 'rational_resampler_ff', '3', '8' ] ) 
CMD_CHAIN.append( [CSDR_CMD, 'gain_ff', '100.0'] ) 
#CMD_CHAIN.append( [CSDR_CMD, 'agc_ff' ] ) # ??? fastagc_ff ?? agc_ff
CMD_CHAIN.append( [CSDR_CMD, 'limit_ff'] )
CMD_CHAIN.append( [CSDR_CMD, 'convert_f_i16'] )


# rational_resampler_ff <interpolation> <decimation> [transition_bw [window]]

for item in CMD_CHAIN:
    print item

msk144_parser = lambda x: {'snr':x[7:11], 'drift':x[11:16], 'freq':x[16:21], 'message':x[25:47], 'is_valid':(x[21:25] == ' &  ' or x[21:25] == ' ^  ')}

DECODER_CHAIN = []
DECODER_CHAIN.append( ['msk144', False, [MSK144_CMD, '-f', '1500'], msk144_parser ] )

CALLSIGN_PREFIXES = ["R9", "RA9", "UB9", "UB0", "RV9", "RZ9", "RK9", "R0",
                "RA0", "UA9", "RU9", "RT9", "RT0", "RW9", "RW0", "UN7",
                "RC9", "RO9", "RG8", "RG9"]


WORKING_DIR = lambda x: x.strftime("tmp_msk144/%Y_%m_%d")
BASE_FILE_NAME = lambda d,local_time,utc_time: "{0}/{1}_{2}".format(d, local_time.strftime("%Y%m%d%H%M%S"), utc_time.strftime("%H%M%S"))
KEEP_DECODED_RESULT = True
KEEP_WAV_FILES = False

# WORKING_DIR = 'TMPFILES'
# KEEP_DECODED_RESULT = False
SRC = 'BRN'
POST_MAGIC_KEY = 'secret'
