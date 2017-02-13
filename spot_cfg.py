
CSDR_CMD = 'csdr'
JT65_CMD = 'jt65'
FLAC_CMD = 'flac'

HTTP_SPOT_URI = 'http://192.168.1.200:9000/spotter/default/populate_spot'


START_WINDOW = (59.5, 60.5)
RECORD_DURATION_IN_SECONDS = 55
START_ONLY_AT_EVEN_MINUTE = False
ROUND_TO_MINUTE_IN_SECONDS = 15

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

# TODO: remove
for item in CMD_CHAIN:
    print item


DECODER_CHAIN = []
DECODER_CHAIN.append( ['jt65a', [JT65_CMD, '-m', 'A']  ] )
DECODER_CHAIN.append( ['jt65b', [JT65_CMD, '-m', 'B']  ] )

# WORKING_DIR = lambda x: x.strftime("%Y_%m_%d")
# KEEP_DECODED_RESULT = True

WORKING_DIR = 'TMPFILES'
KEEP_DECODED_RESULT = False

SRC = 'BRN'
POST_MAGIC_KEY = 'secret'

