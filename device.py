import random
import numpy
import simpy
from file_manager import SharedFile


def new_inter_session_time():
    """
    Ritorna un valore per l'istanza di "inter-session time"
    """
    return numpy.random.lognormal(mean=7.971, sigma=1.308)


def new_session_duration():
    """
    Ritorna un valore per l'istanza di "session time"
    """
    return numpy.random.lognormal(mean=8.492, sigma=1.545)


def new_inter_upload_time():
    """
    Ritorna un valore per l'istanza di "inter-upload time"
    """
    return numpy.random.lognormal(mean=3.748, sigma=2.286)


def new_download_time(s, download_rate):
    """
    Ritorna un valore per l'istanza di "download time", relativa al file di dimensione "s"
    """
    if s == 0:
        return 0
    else:
        return s / download_rate


def new_download_rate(f):
    """
    Ritorna un valore per l'istanza di "download rate", relativa al file "f"
    """
    r = f.get_throughput()
    delta_r = (random.random() - 0.25) * 2 * r
    r += delta_r
    return r


def new_upload_time(file_size, upload_rate):
    """
    Ritorna un valore per l'istanza di "upload time", relativa al file di dimensione "file_size"
    """
    return new_download_time(file_size, upload_rate)


def new_upload_rate(f):
    """
    Ritorna un valore per l'istanza di "upload rate", relativa al file "f"
    """
    return new_download_rate(f)


class Device(object):
    # cosftructor
    def __init__(self, device_id, env, fm, cs, cenv):
        """
        :param device_id: id del dispositivo
        :param env: ambiente di simulazione simpy
        :param fm: file manager
        :param cs: cloud stats
        """
        # ID del dispositivo
        self.id = device_id
        # Elenco delle cartelle condivise
        self.my_shared_folders = []
        # Ambiente di simulazione
        self.env = env
        # Ambiente cloud
        self.cloud_env = cenv
        # File manager
        self.fm = fm
        # Gestore statistiche
        self.stats = cs
        # Cartella condivisa di lavoro (per una certa sessione)
        self.current_sf = None
        # Timestamp di fine sessione
        self.end_session = -1
        # Flag di login
        self.logged_in = False
        # Elenco dei file obsoleti/mancanti, da scaricare
        self.missing_files = set([])
        # Elenco dei file che non sono stati caricati in upload
        self.missed_uploads = set([])
        # Elenco dei file da scaricare al volo
        self.triggered_list = set([])
        # Risorsa condivisa per i triggered download: utile per scaricare i file al volo
        self.trigger_lock = simpy.Container(self.env, init=0)
        # Flag: se vero, il dispositivo viene notificato realtime sull'upload di nuovi file su Cloud
        self.triggerable = False
        # Contributo nel trasferimento file P2P
        self.p2p_contribution = 0.0
        # Preparazione alla simulazione
        self.prepare()

    # fancy printing as string
    def __str__(self):
        sf_str = ", ".join([str(i) for i in self.my_shared_folders])
        return "Device: " + str(self.id) + ", Shared Folders [" + sf_str + "]"

    # add a shared folder to this device
    def add_shared_folder(self, sf):
        self.my_shared_folders.append(sf)

    def is_working_in_sf(self, sf):
        """
        Verifica che il dispositivo stia lavorando nella cartella condivisa specificata
        """
        return self.current_sf == sf

    def is_on(self):
        """
        Verifica che il dispositivo sia loggato
        """
        return self.logged_in

    def has_file(self, f):
        """
        Verifica che il dispositivo abbia gia' scaricato il file "f"
        """
        return f not in self.missing_files

    def has_shared_folder(self, sf):
        """
        Verifica che il dispositivo abbia i privilegi per lavorare in una certa cartella condivisa
        """
        return sf in self.my_shared_folders

    def get_id(self):
        return self.id

    def random_sf(self):
        """
        Ritorna una delle shared folder, scelta casualmente
        """
        return random.choice(self.my_shared_folders)

    def residual_session_duration(self):
        """
        Ritorna il numero di secondi rimanenti prima del logout
        """
        return self.end_session - int(self.env.now)

    def prepare(self):
        """
        La funzione prepara i processi di simulazione per il dispositivo in questione
        """
        self.env.process(self.run())

    def run(self):
        """
        Questo metodo alterna lo stato di online/offline per il device
        """
        while True:
            # Tempo di attesa, prima di diventare online
            inter_session_time = new_inter_session_time()
            yield self.env.timeout(inter_session_time)
            # Scelgo la shared folder su cui operare in questa sessione
            self.current_sf = self.random_sf()
            # Il device effettua il login
            session_duration = new_session_duration()
            # La sessione ha una durata massima, entro cui posso svolgere le operazioni: quando session_duration ha
            # valore negativo, significa che l'operazione corrente di upload/download viene troncata
            self.session_start(session_duration)

            # DOWNLOADS
            residual_time = session_duration
            # Ricaviamo l'elenco dei file che dovrei scaricare
            if len(self.downloads()) == 0:
                self.fm.log('Device %d has no file to download from the server' % self.id)
            else:
                while len(self.downloads()) > 0:
                    # File da scaricare
                    f = self.downloads().pop()
                    file_size_to_download = f.get_size()
                    server_download = True
                    # Verifico il download P2P
                    if not self.cloud_env.server:
                        server_download = False
                        # Elenco dei dispositivi loggati che dispongono del file
                        peers = self.cloud_env.look_for_peers(f)
                        if len(peers) > 0:
                            # Ricavo le durate utili residue relative alle sessioni dei peers
                            residual_times = map(lambda p: min(p.residual_session_duration(), residual_time), peers)
                            # Calcolo un valore di throughput per il trasferimento dati del file dai vari peers
                            rates = map(lambda p: new_download_rate(f), peers)

                            # Funzione locale, verifica se ho tempo a disposizione per scaricare il file da altri peers
                            def p2p_check():
                                for t in residual_times:
                                    if t > 0:
                                        return True
                                return False

                            # Calcolo ora per quanto tempo rimanere connesso ai vari peers, per scaricare il file
                            durations = [0] * len(peers)
                            downloaded_data = 0.0
                            file_size = f.get_size()
                            downloaded = False
                            while (not downloaded) and p2p_check():
                                for i in range(len(peers)):
                                    if residual_times[i] > 0:
                                        # Scarichero' un secondo di dati dal peer i-esimo
                                        residual_times[i] -= 1
                                        durations[i] += 1
                                        downloaded_data += rates[i]
                                        # Se il file puo' essere scaricato, interrompo i cicli
                                        if downloaded_data >= file_size:
                                            downloaded = True
                                            break
                            # Eseguo il download in parallelo dai vari peers
                            events = []
                            for i in range(len(peers)):
                                if durations[i] > 0:
                                    events.append(self.env.process(peers[i].p2p_upload(f, durations[i], rates[i])))
                                    self.env.process(self.p2p_download(f, durations[i], rates[i], peers[i].get_id()))
                            if len(events) > 0:
                                yield simpy.events.AllOf(self.env, events)
                            # Terminato il download dai peer, se il file e' troppo grande la parte residua viene
                            # scaricata dal server centrale
                            if not downloaded:
                                file_size_to_download -= downloaded_data
                                server_download = True
                            else:
                                self.missing_files.remove(f)
                        else:
                            # Non ci sono peer che dispongono del file che sto cercando
                            server_download = True
                    if server_download:
                        # Devo scaricare il file da server
                        # Tempo richiesto per il download del file
                        server_download_rate = new_download_rate(f)
                        server_download_time = new_download_time(file_size_to_download, server_download_rate)
                        residual_time -= server_download_time
                        # Verifico di avere tempo sufficiente per eseguire correttamente il download del file
                        if residual_time >= 0:
                            # Riesco a scaricare correttamente il file
                            yield self.env.process(self.download(f, server_download_time, server_download_rate, True))
                        else:
                            # L'operazione di download e' stata prematuramente interrotta
                            self.missing_files.add(f)
                            self.stats.download_start(self, f)
                            yield self.env.timeout(residual_time + server_download_time)
                            self.stats.download_end(self, f, server_download_rate)
                            self.fm.log('Device %s fails to download on fly file "%d" at %d' % (self.id, f.get_id(),
                                                                                         int(self.env.now)))
                            return
                self.fm.log('Device %s finishes its downloads at %d' % (self.id, int(self.env.now)))
            # Nell'eventuale parte rimanente della sessione, il dispositivo effettua upload di file e scarica le nuove
            # modifiche
            if residual_time > 0:
                # TRIGGERED DOWNLOADS
                # In parallelo agli uploads, il dispositivo rimane in ascolto per scaricare file caricati da altri sulla
                # cartella condivisa corrente
                self.triggerable = True
                # UPLOADS
                # Se la parte di download e' terminata con successo, procedo nel caricare in upload piu' file possibile
                yield self.env.process(self.uploads(residual_time))
                '''tdw_proc = self.env.process(self.triggered_downloads(residual_time))
                yield up_proc or tdw_proc'''
                self.triggerable = False
                # up_proc.interrupt('')
                # tdw_proc.interrupt('')
            self.session_end()
            self.fm.log('Device %d logs out at %d: session lasts for %d' % (self.id, int(self.env.now),
                                                                            int(session_duration)))

    def downloads(self):
        """
        La funzione restituisce l'elenco di file da scaricare (perche' nuovi o modificati) da una specifica cartella
        condivisa
        """
        return filter(lambda x: x.get_shared_folder() == self.current_sf, self.missing_files)

    def download(self, f, download_time, download_rate, on_fly=False):
        """
        La funzione simula il download del file "f"
        """
        # Eseguo il download del file, che puo' essere server o P2P
        self.stats.download_start(self, f)
        yield self.env.timeout(download_time)
        self.stats.download_end(self, f, download_rate)
        self.stats.download_successful(self, f, download_time)
        # Ho scaricato il file, quindi lo segnalo come aggiornato
        self.missing_files.remove(f)
        self.fm.log(
            'Device %d downloads %sfile "%d" from the server at %d: download lasts for %.2f' %
            (self.id, 'on fly ' if on_fly else '', f.get_id(), int(self.env.now), download_time)
        )

    def p2p_download(self, f, download_time, download_rate, peer_id):
        """
        La funzione simula il download di una porzione di file da un peer
        :param f: file scaricato
        :param download_time: tempo impiegato per scaricare la porzione di file (s)
        :param download_rate: velcoita' di download (bit/s)
        :param peer_id: id del peer che effettua l'upload dei dati
        """
        size = download_time * download_rate
        self.stats.p2p_download_start()
        yield self.env.timeout(download_time)
        self.stats.p2p_download_end(size)
        if f.get_size() == size:
            # Sto scaricando l'intero file da un unico peer
            tmp = 'the entire'
        else:
            tmp = 'a portion of'
        self.fm.log('Device %d downloads %s file "%d" (size: %.2f bits) from the peer "%d" at %d: download '
                    'lasts for %.2f' % (self.id, tmp, f.get_id(), size, peer_id, int(self.env.now), download_time))

    def uploads(self, residual_time):
        """
        La funzione esegue, per il tempo rimasto, l'upload di piu' file possibile sulla cartella condivisa
        - "residual_time" e' il tempo di sessione rimasto
        """
        try:
            while residual_time > 0:
                # Verifico che l'upload possa avere luogo
                inter_upload_time = new_inter_upload_time()
                self.fm.log('Device %s starts waiting an inter-upload time of %d at %s' % (self.id, inter_upload_time,
                                                                                           int(self.env.now)))
                # File da mandare in upload
                f = self.to_upload()
                if inter_upload_time >= residual_time:
                    # Non riesco a fare altri uploads
                    self.missed_uploads.add(f)
                    yield self.env.timeout(residual_time)
                    self.fm.log('Device %s has no time to upload file (inter-upload time) at %s' % (self.id,
                                                                                                    int(self.env.now)))
                    residual_time = 0
                else:
                    # Posso tentare un nuovo upload
                    yield self.env.timeout(inter_upload_time)
                    residual_time -= inter_upload_time
                    # UPLOAD
                    upload_rate = new_upload_rate(f)
                    upload_time = new_upload_time(f.get_size(), upload_rate)
                    if residual_time >= upload_time:
                        # Posso effettuare correttamente l'upload del file
                        yield self.env.process(self.upload(f, upload_time, upload_rate))
                        residual_time -= upload_time
                    else:
                        # L'operazione di upload viene interrotta prematuramente a causa del logout
                        self.stats.upload_start(self, f)
                        yield self.env.timeout(residual_time)
                        self.stats.upload_end(self, f, upload_rate)
                        self.fm.log(
                            'Device %s fails to upload file "%s" at %s' % (self.id, f.get_id(), int(self.env.now)))
                        residual_time = 0
        except simpy.Interrupt:
            pass

    def to_upload(self):
        """
        La funzione restituisce il prossimo file da caricare in upload: se l'operazione non viene troncata da un logout
        prematuro, allora gli altri device che condividono la cartella riceveranno questo file
        """
        # Per prima cosa, guardo i file che non sono riuscito a caricare in precedenza
        for x in self.missed_uploads:
            # Mi soffermo sulla cartella condivisa su cui il device opera in questa sua sessione
            if x.get_shared_folder() == self.current_sf:
                if self.current_sf.has_file(x):
                    if x.get_last_modified() > self.current_sf.get_last_modified(x):
                        # File da aggiornare
                        self.missed_uploads.remove(x)
                        return x
                    else:
                        # File obsoleto
                        self.missed_uploads.remove(x)
                else:
                    # File non presente su cloud
                    self.missed_uploads.remove(x)
                    return x
        # Se non ho file in arretrato, carico qualcosa di nuovo
        fc = self.fm.new_upload()
        t = int(self.env.now)
        return SharedFile.from_cloud(fc, self.current_sf, t, self.id)

    def upload(self, f, upload_time, upload_rate):
        """
        La funzione simula l'upload del file "f" su server, di durata "upload_time" e rate "upload_rate"
        :param f: file da mandare in upload
        :param upload_time: durata del trasferimento dati
        :param upload_rate: velocita' di trasferimento dei dati
        """
        # Eseguo l'upload del file
        self.stats.upload_start(self, f)
        yield self.env.timeout(upload_time)
        # Aggiorna i riferimenti su cartella condivisa e notifica gli altri device
        sf = f.get_shared_folder()
        sf.upload_file(f, int(self.env.now))
        self.stats.upload_end(self, f, upload_rate)
        self.stats.upload_successful(self, f, upload_time)
        self.fm.log(
            'Device %d uploads file "%d" in shared folder "%d", at %d: upload lasts for %.2f' %
            (self.id, f.get_id(), sf.get_id(), int(self.env.now), int(upload_time))
        )

    def p2p_upload(self, f, upload_time, upload_rate):
        """
        La funzione simula l'upload del file "f", di durata "upload_time" e rate "upload_rate"
        :param f: file da mandare in upload
        :param upload_time: durata del trasferimento dati
        :param upload_rate: velocita' di trasferimento dei dati
        """
        self.fm.log(
            'Device %d starts uploading file "%d" to a peer, at %d: upload will lasts for %.2f' %
            (self.id, f.get_id(), int(self.env.now), int(upload_time))
        )
        # Il contatore deve essere veritiero anche nel caso in cui la simulazione si interrompa
        for t in range(upload_time):
            yield self.env.timeout(1)
            self.p2p_contribution += upload_rate

    '''
    def triggered_downloads(self, residual_time):
        """
        La funzione permette di scaricare in real-time i file caricati/modificati da altri dispositivi sulla cartella
        condivisa
        """
        while self.env.now < self.end_session and self.triggerable:
            # Attendo notifica da parte del server
            yield self.trigger_lock.get(1)
            if self.env.now < self.end_session and self.triggerable:
                # Scarico il nuovo file, in parallelo agli upload
                f = self.triggered_list.pop()
                dr = new_download_rate(f)
                dt = new_download_time(f.get_size(), dr)
                if self.env.now + dt <= self.end_session:
                    yield self.env.process(self.download(f, dt, dr))
                else:
                    self.stats.download_start(self, f)
                    yield self.env.timeout(int(self.end_session - self.env.now))
                    self.stats.download_end(self, f, dr)
                    self.fm.log('Device %s fails to download file "%d" on the fly at %d' % (self.id, f.get_id(),
                                                                                            int(self.env.now)))
    '''

    def trigger_download(self, f):
        """
        La funzione permette di far scaricare al volo il file "f" al dispositivo, appena caricato su Cloud da altri
        """
        # Il singolo device puo' scaricare un solo file per volta dal server -> Risorsa condivisa
        yield self.trigger_lock.get(1)
        # Tento di scaricare il file dal server
        # Nota: in realta', qui potrei essere al di fuori della sessione, o in una nuova. Occorre tenerne conto,
        # verificando che il dispositivo sia "triggerable" e che il file non sia stato gia' scaricato
        if self.triggerable and (f in self.missing_files):
            dr = new_download_rate(f)
            dt = new_download_time(f.get_size(), dr)
            if self.env.now + dt <= self.end_session:
                # Ho tempo sufficiente per completare il download
                yield self.env.process(self.download(f, dt, dr))
            else:
                # Non riesco a scaricare il file per intero
                self.stats.download_start(self, f)
                yield self.env.timeout(int(self.end_session - self.env.now))
                self.stats.download_end(self, f, dr)
                self.fm.log('Device %s fails to download file "%d" on the fly at %d' % (self.id, f.get_id(),
                                                                                        int(self.env.now)))
        # Rilascio la risorsa
        yield self.trigger_lock.put(1)

    def new_file_to_download(self, f):
        """
        La funzione tiene traccia dei file che il dispositivo deve scaricare, emulando la notifica dell'elenco file
        da parte del Cloud Server
        """
        self.missing_files.add(f)

    def session_start(self, session_duration):
        """
        La funzione esegue routine in fase di login del dispositivo
        """
        self.fm.log('Device %s logged in at %s, on shared folder "%d"' % (self.id, int(self.env.now),
                                                                          self.current_sf.get_id()))
        self.end_session = int(self.env.now) + session_duration
        self.logged_in = True
        self.stats.login(self)

    def session_end(self):
        """
        La funzinoe esegue routine in fase di logout del dispositivo
        """
        # Triggered download non scaricati
        self.triggerable = False
        self.triggered_list.clear()
        if self.trigger_lock.level > 0:
            self.trigger_lock.get(self.trigger_lock.level)
        self.logged_in = False
        self.stats.logout(self)
