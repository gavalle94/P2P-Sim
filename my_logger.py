class Logger(object):
    """
    La classe modellizza un logger, per generare un file di testo di output
    """

    def __init__(self, fp):
        self.fp = open(fp, 'w')

    def log(self, msg):
        self.fp.write(msg + '\n')

    def close(self):
        self.fp.close()