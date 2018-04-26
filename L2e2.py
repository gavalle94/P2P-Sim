import cloud_env
import my_logger


# Numero di dispositivi
NUM_DEV = 300
# Debug flag
DEBUG = False
# Tempo di simulazione
SIM_TIME = 360000
# Log file
LOG_FILE = 'log.txt'
# Logger
log = my_logger.Logger(LOG_FILE)

try:
    env = cloud_env.CloudEnvironment(NUM_DEV, log, server=False)
    env.run(SIM_TIME)
except:
    # In case of errors, close the input file
    print 'An error occured. The program will be stopped'
    log.close()
    raise
