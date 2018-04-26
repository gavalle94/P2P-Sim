class SharedFile(object):
    """
    La classe modellizza un file condiviso su Cloud tra piu' device
    """
    def __init__(self, file_id, file_size, shared_folder, last_modified):
        # ID del file
        self.id = file_id
        # Dimensioni, in Byte
        self.size = file_size
        # Cartella condivisa su cui viene caricato
        self.sf = shared_folder
        # Data di ultima modifica del file
        self.last_modified = last_modified

    def __eq__(self, other):
        return self.id == other.id and self.sf == other.sf

    def update(self, timestamp):
        if self.last_modified < timestamp:
            # La modifica al file e' valida
            self.last_modified = timestamp
            return True
        return False

    def get_shared_folder(self):
        return self.sf
