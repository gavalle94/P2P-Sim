import timed_structures as ts
import qs_plots as plots
import input_controls as ic


class StatsManager(object):
    """
    La classe modellizza un manager per le statistiche di un servizio di file sharing
    """

    def __init__(self, n_devices, devices, env, server=True):
        # Server centrale per i download di files
        self.server = server
        # Ambiente di simulazione
        self.env = env
        # Numero totale di device della rete
        self.n_devices = n_devices
        self.devices = devices
        # Numero di device connessi attualmente al servizio
        self.current_online_devices = 0
        self.current_downloading = 0
        self.current_uploading = 0
        # Dati per le trasmissioni dati P2P
        self.current_p2p_exchanges = 0
        self.p2p_downloaded_data = 0.0
        # Storico del numero di device attivi
        self.online_devices = ts.TimedArray(empty=False)
        self.downloading = ts.TimedArray(empty=False)
        self.uploading = ts.TimedArray(empty=False)
        # Storico del numero di conessioni P2P attive
        self.p2p_downloading = ts.TimedArray(empty=False)
        # Strico attivita' devices
        self.online_for = ts.TimedArray(timestamp=False)
        self.download_for = ts.TimedArray(timestamp=False)
        self.download_for_success = ts.TimedArray(timestamp=False)
        self.upload_for = ts.TimedArray(timestamp=False)
        self.upload_for_success = ts.TimedArray(timestamp=False)
        # Dati temporanei
        self.pending_online = ts.TimedArray()
        self.pending_download = ts.TimedArray()
        self.pending_upload = ts.TimedArray()
        # Carico sul server: l'indice del vettore coincide con il timestamp di simulazione -1
        self.server_load_in = []
        self.server_load_out = []
        self.server_downloaded_data = 0.0

    def now(self):
        return int(self.env.now)

    def new_simulation(self, until):
        """
        Nuova simulazione, la cui durata viene passata come parametro
        """
        duration = until - len(self.server_load_in)
        self.server_load_in += [0] * duration
        self.server_load_out += [0] * duration

    def login(self, d):
        """
        Un nuovo device "d" effettua il login
        """
        # Timestamp corrente
        t = self.now()
        # Ho un nuovo device connesso
        self.current_online_devices += 1
        # Aggiorno il numero di dispositivi connessi nello storico dati
        self.online_devices.insert_or_update(t, self.current_online_devices)
        # Salvo l'informazione di login, per calcolare al momento del logout la durata della sessione
        self.pending_online.append(ts.TimedData(d.id, t))

    def logout(self, d):
        """
        Un device "d" effettua il logout
        """
        # Timestamp corrente
        t = self.now()
        # Ho un device che si disconnette
        self.current_online_devices -= 1
        # Aggiorno il numero di dispositivi connessi nello storico daticurrent_uploading
        self.online_devices.insert_or_update(t, self.current_online_devices)
        # Ricavo la durata di sessione, partendo dal timestamp di login
        x = self.pending_online.search_by_data(d.id)[0]
        self.pending_online.remove(x)
        t_login = x.get_time()
        session = t - t_login
        self.online_for.append(
            ts.TimedData(d.id, session, timestamp=False)
        )

    def download_start(self, d, f):
        """
        Un device "d" inizia a scaricare il file "f" dal server
        """
        # Timestamp corrente
        t = self.now()
        # Ho un nuovo file in download
        self.current_downloading += 1
        # Aggiorno il numero di download in parallelo nello storico dati
        self.downloading.insert_or_update(t, self.current_downloading)
        # Salvo l'informazione di download, per calcolare al suo termine la durata del trasferimento
        self.pending_download.append(ts.TimedData(str(d.id) + '_' + str(f.get_id()), t))

    def p2p_download_start(self):
        """
        Un device "d" inizia a scaricare una porzione di file da un peer
        """
        # Timestamp corrente
        t = self.now()
        # Ho un nuovo download da peer
        self.current_p2p_exchanges += 1
        # Aggiorno il numero di download in parallelo nello storico dati
        self.p2p_downloading.insert_or_update(t, self.current_p2p_exchanges)

    def download_end(self, d, f, dw_rate):
        """
        Un device "d" finisce di scaricare il file "f"
        """
        # Timestamp corrente
        t = self.now()
        # Ho un download che termina (con o senza successo)
        self.current_downloading -= 1
        # Aggiorno il numero di download in parallelo nello storico dati
        self.downloading.insert_or_update(t, self.current_downloading)
        # Ricavo la durata del trasferimento, partendo dal timestamp di inizio download
        x = self.pending_download.search_by_data(str(d.id) + '_' + str(f.get_id()))[0]
        self.pending_download.remove(x)
        t_start = x.get_time()
        dw_duration = t - t_start
        self.download_for.append(
            ts.TimedData(d.id + f.get_id(), dw_duration, timestamp=False)
        )
        # Valori di carico sul server
        i = t_start
        while i <= t:
            self.server_load_out[i - 1] += dw_rate
            i += 1
        self.server_downloaded_data += dw_duration * dw_rate

    def p2p_download_end(self, data_size):
        """
        Un device finisce di scaricare una porzione di file di dimensione "data_size" da un peer
        """
        # Timestamp corrente
        t = self.now()
        # Ho un download che termina (con o senza successo)
        self.current_p2p_exchanges -= 1
        # Aggiorno il numero di download in parallelo nello storico dati
        self.p2p_downloading.insert_or_update(t, self.current_downloading)
        # Aggiorno l'ammontare di bit scambiato da peers
        self.p2p_downloaded_data += data_size

    def upload_start(self, d, f):
        """
        Un device "d" inizia a caricare il file "f"
        """
        # Timestamp corrente
        t = self.now()
        # Ho un nuovo file in upload
        self.current_uploading += 1
        # Aggiorno il numero di upload in parallelo nello storico dati
        self.uploading.insert_or_update(t, self.current_uploading)
        # Salvo l'informazione di upload, per calcolare al suo termine la durata del trasferimento
        self.pending_upload.append(ts.TimedData(d.id + f.get_id(), t))

    def p2p_upload_start(self):
        """
        Un device inizia ad inviare dati in upload verso un altro peer
        """
        # TODO: forse, questo metodo non serve, perche' le statistiche sono gia' elaborate in p2p_download_start
        pass

    def upload_end(self, d, f, up_rate):
        """
        Un device "d" finisce di caricare il file "f"
        """
        # Timestamp corrente
        t = self.now()
        # Ho un upload che termina (con o senza successo)
        self.current_uploading -= 1
        # Aggiorno il numero di download in parallelo nello storico dati
        self.uploading.insert_or_update(t, self.current_uploading)
        # Ricavo la durata del trasferimento, partendo dal timestamp di inizio upload
        x = self.pending_upload.search_by_data(d.id + f.get_id())[0]
        self.pending_upload.remove(x)
        t_login = x.get_time()
        session = t - t_login
        self.upload_for.append(
            ts.TimedData(d.id + f.get_id(), session, timestamp=False)
        )
        # Valori di carico sul server
        i = t_login
        while i <= t:
            self.server_load_in[i - 1] += up_rate
            i += 1

    def p2p_upload_end(self):
        # TODO: forse, questo metodo non serve, perche' le statistiche sono gia' elaborate in p2p_download_end
        pass

    def download_successful(self, d, f, download_time):
        """
        Un device "d" scarica in download correttamente il file "f"
        :param d: device
        :param f: file scaricato
        :param download_time: tempo di download
        """
        self.download_for_success.append(
            ts.TimedData(d.id + f.get_id(), download_time, timestamp=False)
        )

    def upload_successful(self, d, f, upload_time):
        """
        Un device "d" carica in upload correttamente il file "f"
        :param d: device
        :param f: file caricato
        :param upload_time: tempo di upload
        """
        self.upload_for_success.append(
            ts.TimedData(d.id + f.get_id(), upload_time, timestamp=False)
        )

    def stats(self):
        """
        Elabora statistiche finali e stampa a schermo dei grafici
        """
        print '### STATS ###'
        print('Total number of devices in the network: %d' % self.n_devices)
        print('Total amount of data downloaded from the server: %d bits' % self.server_downloaded_data)
        if not self.server:
            tmp = self.p2p_downloaded_data + self.server_downloaded_data
            if tmp > 0:
                tmp = ' (' + str(round(self.p2p_downloaded_data / tmp * 100, 2)) + '% of the total)'
            else:
                tmp = ''
            print('P2P exchanged traffic: %d bits%s' % (self.p2p_downloaded_data, tmp))
            if self.n_devices >= 5:
                print('Top 5 P2P contributors:')
                contributions = map(lambda d: (d.p2p_contribution, d.id), self.devices.values())
                contributions.sort(key=lambda d: d[0], reverse=True)
                for i in range(5):
                    print('Device "%d": %d bits' % (contributions[i][1], contributions[i][0]))
        print('Number of devices currently online: %d' % self.current_online_devices)
        print('Number of devices currently downloading files: %d' % self.current_downloading)
        print('Number of devices currently uploading files: %d' % self.current_uploading)
        if not self.server:
            print('Number of P2P connections currently active: %d' % self.current_p2p_exchanges)
        print('Average time spent by a device downloading data: %s s' % self.mean_downloading_time())
        print('Average time spent by a device uploading data: %s s' % self.mean_uploading_time())
        print('Average download duration: %s s' % self.mean_download_time())
        print('Average upload duration: %s s' % self.mean_upload_time())
        print('Average server incoming traffic: %s b/s' % self.mean_in_traffic())
        print('Average server outgoing traffic: %s b/s' % self.mean_out_traffic())
        # Aggiorna i grafici
        t = self.now()
        self.online_devices.insert_or_update(t, self.current_online_devices)
        self.downloading.insert_or_update(t, self.current_downloading)
        self.uploading.insert_or_update(t, self.current_uploading)
        # Dispositivi online
        if len(self.online_devices.get_list()) > 2:
            fig_online, area_online = plots.figure(title='Online devices')
            plots.step_plot2(area_online, self.online_devices.get_time_list(), self.online_devices.get_data_list(),
                             'Time', '#Devices')
        # Dispositivi in download
        if len(self.downloading.get_list()) > 2:
            fig_dw, area_dw = plots.figure(title='Devices downloading a file')
            plots.step_plot2(area_dw, self.downloading.get_time_list(), self.downloading.get_data_list(), 'Time',
                             '#Device', style='g')
        # Dispositivi in upload
        if len(self.uploading.get_list()) > 2:
            fig_up, area_up = plots.figure(title='Devices uploading a file')
            plots.step_plot2(area_up, self.uploading.get_time_list(), self.uploading.get_data_list(), 'Time',
                             '#Device', style='r')
        # Connessioni P2P
        if (not self.server) and len(self.p2p_downloading.get_list()) > 2:
            fig_p2p_dw, area_p2p_dw = plots.figure(title='P2P connections')
            plots.step_plot2(area_p2p_dw, self.p2p_downloading.get_time_list(), self.p2p_downloading.get_data_list(),
                             'Time', '#Connections', style='k')
        # Traffico in ingresso al server
        fig_in_traffic, area_in_traffic = plots.figure(title='Server incoming traffic')
        plots.step_plot(area_in_traffic, self.server_load_in, 'Time', 'bit/s', style='m')
        # Traffico in uscita dal server
        fig_out_traffic, area_out_traffic = plots.figure(title='Server outgoing traffic')
        plots.step_plot(area_out_traffic, self.server_load_out, 'Time', 'bit/s', style='y')
        plots.show()

    def mean_downloading_time(self):
        """
        La funzione ritorna la media dei tempi medi spesi da ogni device per scaricare dati (con o senza successo)
        """
        return reduce(lambda x, y: x + y, self.download_for.get_time_list(), 0.0) / self.n_devices

    def mean_uploading_time(self):
        """
        La funzione ritorna la media dei tempi medi spesi da ogni device per caricare dati (con o senza successo)
        """
        return reduce(lambda x, y: x + y, self.upload_for.get_time_list(), 0.0) / self.n_devices

    def mean_download_time(self):
        """
        La funzione ritorna la durata media di un download (con o senza successo)
        """
        return mean(self.download_for_success.get_time_list())

    def mean_upload_time(self):
        """
        La funzione ritorna la durata media di un upload (con o senza successo)
        """
        return mean(self.upload_for_success.get_time_list())

    def mean_in_traffic(self):
        """
        La funzione ritorna il valor medio di traffico in ingresso al server (upload di file dei device)
        """
        return mean(self.server_load_in)

    def mean_out_traffic(self):
        """
        La funzione ritorna il valor medio di traffico in ingresso al server (upload di file dei device)
        """
        return mean(self.server_load_out)


def mean(array):
    """
    Calcola la media di un vettore "array" di numeri
    """
    # Controllo dell'input, tramite eccezioni
    ic.check_array(array, 'array', of=(int, long, float))
    l = len(array)
    if l > 0:
        s = reduce(lambda x, y: x + y, array)
        m = round(s / l, 2)
    else:
        m = 'N/A'
    # Risultato
    return m


def integral_mean(t_array, end_time):
    """
    Calcola la media integrale di un TimedArray "tArray" (peso i valori "data" a seconda dell'intervallo "time" a 
    loro associato)
    Per il momento, la funzione e' pensata per TimedArray con timestamp = False
    """
    # Controllo dell'input
    try:
        ic.check_timed_array(t_array, 'tArray')
        s = 0.0
        total_time = 0.0
        prev_time = 0.0
        prev_value = 0.0
        val = 0.0
        has_intervals = t_array.has_time_intervals()
        for x in t_array.get_list():
            # Ricavo i campi dell'elemento in analisi
            t = x.get_time()
            d = x.get_data()
            # Il vettore puo' contenere intervalli o timestamp
            # Nel secondo caso, devo computare l'intervallo di tempo trascorso
            if not has_intervals:
                time_interval = t - prev_time
                val = prev_value
                prev_time = float(t)
                prev_value = d
            else:
                time_interval = t
            # Quindi, aggiorno i valori di somma e tempo totale
            total_time += time_interval
            s += val * time_interval
        # Ultimo dato
        total_time += end_time - prev_time
        s += prev_value * (end_time - prev_time)
        # Risultato
        m = round(s / total_time, 2)
    except TypeError:
        m = 'N/A'
    return m


def time_mean_per_data(array, n_data):
    """
    La funzione ritorna la media dei valor medi di intervalli temporali, calcolati per ogni valore possibile di data
    :param array: vettore TimedArray da cui calcolare la media
    :param n_data: numero di valori data in esso contenuti
    """
    s = 0.0
    for i in range(n_data):
        s += reduce(lambda x, y: x + y, map(lambda x: x.get_time(), filter(lambda x: x.get_data() == i,
                                                                           array.get_list())), 0)
    return s / n_data
