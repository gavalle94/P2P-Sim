class SharedFolder(object):
    """
    La classe modellizza una cartella di file condivisa tra diversi dispositivi su Cloud storage
    """

    def __init__(self, id_folder):
        # ID della cartella condivisa
        self.id = id_folder
        # Dispositivi che condividono la cartella
        self.devices = []
        # Elenco aggiornato dei file nella cartella condivisa
        self.files = set([])

    # fancy printing as string
    def __str__(self):
        return str(self.id)

    def __eq__(self, other):
        return self.id == other.id

    # add a device to the list of devices registering this shared folder
    def add_device(self, device):
        self.devices.append(device)
        # Notifico il device circa i file da scaricare, presenti nella cartella a cui si e' unito
        for f in self.files:
            device.new_file_to_download(f)

    def has_file(self, f):
        """
        Verifica che il file sia presente all'interno della cartella condivisa
        """
        return f in self.files

    def upload_file(self, f, timestamp):
        if self.has_file(f):
            # Aggiorno il riferimento puntatore
            if f.update(timestamp):
                # Notifico gli altri client delle nuove modifiche al file
                self.notify_devices(f)
        else:
            # Aggiungo il file (nuovo)
            self.files.add(f)
            self.notify_devices(f)

    def notify_devices(self, f):
        """
        La funzione notifica i device che condividono la cartella circa un nuovo upload/modifica del file "f"
        """
        for d in self.devices:
            if d.id != f.get_last_device():
                d.new_file_to_download(f)
                if d.env.now < d.end_session and d.triggerable:
                    # Scarico il nuovo file, in parallelo agli upload
                    d.trigger_download(f)

    def get_id(self):
        return self.id

    def get_last_modified(self, f):
        """
        Ritorna il time stamp di ultima modifica del file, contenuto all'interno di questa cartella condivisa
        """
        for x in self.files:
            if x == f:
                return x.get_last_modified()
