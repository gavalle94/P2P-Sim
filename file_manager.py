import random


def prepare_input(line):
    """
    A partire da una linea del file di testo di input, la funzione elabora il valore di tempo di download del file
    """
    splitted = line.split(' ')
    file_size = float(splitted[0])
    throughput = float(splitted[-1].rstrip('\n'))
    return file_size, throughput


def get_files():
    """
    La funzione legge il file "throughput.txt" e crea un elenco di file: il loro ordine viene alterato casualmente
    """
    # Input da file
    with open('throughput.txt', 'r') as fp:
        lines = fp.readlines()
    splitted_lines = map(lambda x: prepare_input(x), lines[1:])
    random.shuffle(splitted_lines)
    # Creo la lista di file da memorizzare nel FileManager
    res = []
    next_id = 0
    while len(splitted_lines) > 0:
        file_size, throughput = splitted_lines.pop()
        res.append(CloudFile(next_id, file_size, throughput))
        next_id += 1
    return res


class CloudFile(object):
    """
    La classe modellizza uno dei file che vengono scambiati sul cloud
    """

    def __init__(self, fid, size, th):
        """
        file_id: numero intero
        size: dimensione del file, in bits
        throughput: throughput medio sperimentato dagli utenti in upload/download [bit/s]
        """
        self.file_id = fid
        self.size = float(size)*8
        self.throughput = float(th)

    def get_id(self):
        return self.file_id

    def get_size(self):
        return self.size

    def get_throughput(self):
        return self.throughput


class SharedFile(CloudFile):
    """
    La classe modellizza un file condiviso su Cloud tra piu' device
    """

    @staticmethod
    def from_cloud(fc, sf, t, d):
        """
        Crea e ritorna uno SharedFile a partire da un CloudFile
        """
        fid = fc.get_id()
        size = fc.get_size()
        th = fc.get_throughput()
        return SharedFile(fid, size, th, sf, t, d)

    def __init__(self, fid, size, th, shared_folder, last_modified, last_device):
        """
        :param fid: id del file
        :param size: dimensioni del file, in bytes
        :param th: throughput medio sperimentato dagli utenti per il file [bit/s]
        :param shared_folder: cartella condivisa in cui il file e' stato caricato
        :param last_modified: timestamp di ultima modifica del file
        :param last_device: device che ha effettuato l'ultima modifica al file condiviso
        """
        # Come il CloudFile
        super(SharedFile, self).__init__(fid, size, th)
        # Cartella condivisa su cui viene caricato
        self.sf = shared_folder
        # Data di ultima modifica del file
        self.last_modified = last_modified
        # Ultimo device che l'ha caricato/modificato
        self.last_device = last_device

    def __eq__(self, other):
        return self.file_id == other.file_id and self.sf == other.sf

    def get_shared_folder(self):
        return self.sf

    def get_last_modified(self):
        return self.last_modified

    def update(self, timestamp):
        if self.last_modified < timestamp:
            # La modifica al file e' valida
            self.last_modified = timestamp
            return True
        return False

    def get_last_device(self):
        return self.last_device


class FileManager(object):
    """
    La classe serve per generare, in fase di simulazione, nuovi file in upload o modifiche di quelli gia' esistenti. La 
    classe tiene inoltre traccia dell'id corrente del file
    """

    def __init__(self, logger):
        """
        Per semplificare il codice ma allo stesso tempo non discostarci dai dati reali, ipotizziamo che il numero di 
        file sia finito: l'elenco di file che andiamo a considerare e' quello del file di testo "throughput.txt"
        => L'id del file e' l'indice del file all'interno del vettore in cui sono memorizzati
        """
        self.next_id = 0
        self.files = get_files()
        self.logger = logger

    def get_files_list(self):
        return self.files

    def new_file(self):
        f = self.files[self.next_id]
        self.next_id += 1
        return f

    def update_file(self):
        f = random.choice(self.files[0:self.next_id])
        return f

    def new_upload(self):
        p = round(self.next_id / len(self.files), 2)
        p2 = random.random()
        if p2 < p:
            # Update di file esistente
            return self.update_file()
        else:
            # Upload di un nuovo file nel Cloud
            return self.new_file()

    def log(self, msg):
        self.logger.log(msg)


if __name__ == '__main__':
    # Libreria per i grafici
    import qs_plots as qsp
    import my_logger

    # Creo il file manager, leggendo le informazioni dei file in input da file di testo
    log = my_logger.Logger('cloud_files.txt')
    fm = FileManager(log)
    files = fm.get_files_list()
    file_sizes = []
    throughputs = []
    download_times = []
    while len(files) > 0:
        f = files.pop()
        file_sizes.append(f.get_size())
        throughputs.append(f.get_throughput())
        download_times.append(f.get_transfer_time())

    # File sizes
    (fig_fs_pdf, area_fs_pdf) = qsp.figure(title='File sizes PDF')
    qsp.pdf_plot(area_fs_pdf, file_sizes, 'File size [b]')
    (fig_fs_cdf, area_fs_cdf) = qsp.figure(title='File sizes CDF')
    qsp.cdf_plot(area_fs_cdf, file_sizes, 'File size [b]', 's')
    qsp.show()

    # Throughputs
    (fig_th_pdf, area_th_pdf) = qsp.figure(title='Throughputs PDF')
    qsp.pdf_plot(area_th_pdf, throughputs, 'Mean throughput [b/s]')
    (fig_th_cdf, area_th_cdf) = qsp.figure(title='Throughputs CDF')
    qsp.cdf_plot(area_th_cdf, throughputs, 'Mean throughput [b/s]', 'th')
    qsp.show()

    # Tempi di download
    (fig_dw_pdf, area_dw_pdf) = qsp.figure(title='File download times PDF')
    qsp.pdf_plot(area_dw_pdf, download_times, 'Download required time [s]')
    (fig_dw_cdf, area_dw_cdf) = qsp.figure(title='File download times CDF')
    qsp.cdf_plot(area_dw_cdf, download_times, 'Download required time [s]', 't')
    qsp.show()
