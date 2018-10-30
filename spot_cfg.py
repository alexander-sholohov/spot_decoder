
CSDR_CMD = './csdr'
JT65_CMD = './jt65'
FLAC_CMD = 'flac'

HTTP_SPOT_URI = 'http://192.168.1.200:9000/spotter/default/populate_spot'

START_INTERVAL_IN_SECONDS = 60
LEAD_START_IN_SECONDS = 0.5
RECORD_DURATION_IN_SECONDS = 55

rfSampRate = 2048000
shift = str(float(145000000-144176200)/rfSampRate)
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


jt65_parser = lambda x: {'snr':x[4:9], 'drift':x[20:24], 'freq':x[15:20], 'message':x[28:50], 'is_valid':(x[50:55] == ' JT65')}

DECODER_CHAIN = []
DECODER_CHAIN.append( ['jt65a', False, [JT65_CMD, '-a', '1', '-n', '1000', '-m', 'A'], jt65_parser ] )
DECODER_CHAIN.append( ['jt65a', True,  [JT65_CMD, '-n', '9000', '-m', 'A'], jt65_parser  ] )
# DECODER_CHAIN.append( ['jt65b', False, [JT65_CMD, '-a', '1', '-n', '1000', '-m', 'B'], jt65_parser ] )
# DECODER_CHAIN.append( ['jt65b', True,  [JT65_CMD, '-n', '9000', '-m', 'B'], jt65_parser ] )
DECODER_CHAIN.append( ['qra64a', False,  [JT65_CMD, '-m', '1'], jt65_parser ] )

CALLSIGN_PREFIXES = ["R9", "RA9", "UB9", "UB0", "RV9", "RZ9", "RK9", "R0",
                "RA0", "UA9", "RU9", "RT9", "RT0", "RW9", "RW0", "UN7",
                "RC9", "RO9", "RG8", "RG9"]


WORKING_DIR = lambda x: x.strftime("tmp/%Y_%m_%d")
BASE_FILE_NAME = lambda d,local_time,utc_time: "{0}/{1}_{2}".format(d, local_time.strftime("%Y%m%d%H%M%S"), utc_time.strftime("%H%M"))
KEEP_DECODED_RESULT = True

# WORKING_DIR = 'TMPFILES'
# KEEP_DECODED_RESULT = False
SRC = 'BRN'
POST_MAGIC_KEY = 'secret'
