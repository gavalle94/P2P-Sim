class TimedData(object):
    """
    Struttura dati per eventi accompagnati da un informazione temporale discreta (timestamp o intervallo)
    """

    def __init__(self, data, time, timestamp=True):
        """
        I parametri di input sono
        - "data": il dato che si vuole memorizzare (di qualsiasi natura)
        - "time": l'informazione temporale associata al dato (numero intero)
        - "timestamp": flag booleana. Se vero, il campo "time" e' un timestamp; altrimenti,
            e' un intervallo di tempo
        """
        # Controllo dell'input: parametro "time"
        try:
            time = int(time)
        except:
            raise TypeError('"time" parameter is invalid. It must be an integer number')
        # Creo la struttura dati
        self.data = data
        self.time = time
        self.timestamp = True if timestamp else False

    def __eq__(self, other):
        c1 = self.data == other.data
        c2 = self.time == other.time
        c3 = self.timestamp == other.timestamp
        return c1 and c2 and c3

    def __str__(self):
        return '(data=%s, time=%s, timestamp=%s)' % (self.data, self.time, self.timestamp)

    def get_data(self):
        """
        Ritorna il campo "data"
        """
        return self.data

    def get_time(self):
        """
        Ritorna il campo "time"
        """
        return self.time


class TimedArray(object):
    """
    Array di oggetti TimedData
    """

    def __init__(self, timestamp=True, empty=True):
        """
        La flag "timestamp" serve per specificare se la lista contiene dati con un timestamp (True) oppure un 
        intervallo temporale (False) associato: la flag "empty" permette invece di creare, se settata a False, 
        un TimedArray contenente al suo interno un nodo di partenza (d = 0, t = 0)
        """
        self._list = []
        self.timestamp = (timestamp is True)
        if not empty:
            # Creo il nodo di partenza
            self.append(TimedData(0, 0, self.timestamp))

    def __str__(self):
        x = ''
        first = True
        for i in self._list:
            if first:
                x += str(i)
                first = False
            else:
                x += ', ' + str(i)
        return '(timestamp=%s, [%s]' % (self.timestamp, x)

    def get_list(self):
        """
        Ritorna l'elenco di oggetti "TimedData", memorizzati come lista
        """
        return self._list

    def get_data_list(self):
        """
        Ritorna gli attributi "data" di ogni elemento del vettore, sottoforma di lista
        """
        return map(lambda x: x.get_data(), self._list)

    def get_time_list(self):
        """
        Ritorna gli attributi "time" di ogni elemento del vettore, sottoforma di lista
        """
        return map(lambda x: x.get_time(), self._list)

    def has_time_intervals(self):
        """
        Ritorna True se gli elementi del vettore hanno associato un intervallo temporale
        """
        return self.timestamp is False

    def append(self, item):
        """
        Aggiungo un elemento alla lista
        """
        # Controllo dei parametri di input: "item"
        if not isinstance(item, TimedData):
            raise TypeError('cannot add a non-"TimedData" object to a "TimedArray" list')
        if item.timestamp != self.timestamp:
            raise ValueError(
                '"item" parameter is invalid: its "timestamp" attribute must be equal to %s' % self.timestamp)
        # Accodo l'elemento alla lista
        self._list.append(item)

    def remove(self, item):
        """
        Questa funzione rimuove "item" (se presente) dall'array
        """
        # Controllo dei parametri di input: "item"
        if not isinstance(item, TimedData):
            raise TypeError('the item to remove must be a "TimedData" object')
        # Elimino l'oggetto, se presente
        if item in self._list:
            self._list.remove(item)

    def remove_all(self, items):
        """
        Questa funzione permette di rimuovere un elenco di oggetti "TimedData"
        """
        # Controllo dei parametri di input: "items"
        if not isinstance(items, (list, tuple)):
            raise TypeError('"items" parameter must be an array')
        # Elimino un oggetto per volta
        try:
            for x in items:
                self.remove(x)
        except TypeError:
            raise TypeError('the items list must contain only "TimedData" objects')

    def filter(self, f):
        """
        Questa funzione applica la funzione f per filtrare il contenuto del vettore
        """
        res = TimedArray(self.timestamp, empty=True)
        res._list = filter(
            f,
            self._list
        )
        return res

    def filter_data_range(self, start, end):
        """
        La funzione filtra il vettore per range di valori "Data"
        """
        return self.filter(
            lambda x: start <= x.get_data() <= end
        )

    def filter_time_range(self, start, end):
        """
        La funzione filtra il vettore per range di valori "Data"
        """
        return self.filter(
            lambda x: start <= x.get_time() <= end
        )

    def search(self, to_search):
        """
        Funzione di ricerca all'interno del contenuto del vettore.
        Se "timestamp" e' True, la chiave per la ricerca e' il timestamp: altrimenti,
        la chiave diventa il contenuto a cui e' associato l'intervallo temporale.
        """
        if self.timestamp:
            # La chiave di ricerca e' "time", un numero intero
            res = self.search_by_time(to_search)
        else:
            # La chiave di ricerca e' "data", un dato di qualsiasi tipo
            res = self.search_by_data(to_search)
        # Risultati di ricerca
        return res

    def search_by_data(self, to_search):
        """
        Funzione di ricerca per campo "data", all'interno del vettore
        """
        research = (lambda x: x.data == to_search)
        return filter(research, self._list)

    def search_by_datas(self, search_params):
        """
        Funzione di ricerca per campo "data", all'interno del vettore: il parametro di ricerca e' un vettore
        """
        # Controllo dei parametri di input: "searchParams"
        if not isinstance(search_params, (list, tuple)):
            raise TypeError('"searchParams" parameter is invalid. It must be an array')
        # Effettuo tante ricerche quanti sono i parametri specificati
        result = []
        for x in search_params:
            # Ricerca per data, parametro "x" 
            tmp = self.search_by_data(x)
            # Accodo quanto ottenuto al risultato di ricerca globale
            for t in tmp:
                result.append(t)
        # Risultati della ricerca multipla
        return result

    def search_by_time(self, to_search):
        """
        Funzione di ricerca per campo "time", all'interno del vettore
        Il parametro "toSearch" deve essere un numero intero
        """
        if not isinstance(to_search, (int, long)):
            raise TypeError('the research parameter must be an integer number (timestamp)')
        research = (lambda x: x.time == to_search)
        return filter(research, self._list)

    def search_by_times(self, search_params):
        """
        Funzione di ricerca per campo "time", all'interno del vettore: il parametro di ricerca e' un vettore
        """
        # Controllo dei parametri di input: "searchParams"
        if not isinstance(search_params, (list, tuple)):
            raise TypeError('"searchParams" parameter is invalid. It must be an array')
        # Effettuo tante ricerche quanti sono i parametri specificati
        result = []
        for x in search_params:
            # Ricerca per data, parametro "x" 
            tmp = self.search_by_time(x)
            # Accodo quanto ottenuto al risultato di ricerca globale
            for t in tmp:
                result.append(t)
        # Risultati della ricerca multipla
        return result

    def contains(self, to_search):
        """
        La funzione mi dice se la ricerca nel vettore, sulla base della chiave di ricerca 
        "toSearch" specificata, produce risultati
        """
        return len(self.search(to_search)) > 0

    def update(self, to_search, new_value):
        """
        Questa funzione aggiorna il contenuto degli elementi del vettore che
        soddisfano il criterio di ricerca specificato
        - "toSearch" e' la chiave di ricerca
        - "newValue" e' il valore aggiornato da inserire
        """
        # Effettuo una ricerca
        items = self.search(to_search)
        # Definisco il criterio di aggiornamento
        if self.timestamp:
            # La chiave di ricerca e' "time": aggiorno "data"
            # update_function = (lambda x: x.data = newValue)
            def update_function(x):
                x.data = new_value
        else:
            # La chiave di ricerca e' "data": aggiorno "time"
            # update_function = (lambda x: x.time = newValue)
            def update_function(x):
                x.time = new_value
        # Aggiorno gli elementi
        map(update_function, items)

    def insert_or_update(self, time_to_search, data_value):
        if self.contains(time_to_search):
            self.update(time_to_search, data_value)
        else:
            self.append(
                TimedData(data_value, time_to_search, self.timestamp)
            )
