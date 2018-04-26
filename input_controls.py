from timed_structures import TimedArray
import types


def check_integer(value, name, min_value=None, max_value=None):
    """
    La funzione verifica che la variabile "value" sia di tipo intero e compresa nell'intervallo dichiarato
    """
    # Verifico il tipo intero per variabile ed estremi del range (se dichiarati)
    if not isinstance(value, (int, long)):
        raise TypeError('the parameter "%s" is invalid: it must be an integer' % name)
    if min_value is not None and not isinstance(min_value, (int, long)):
        raise TypeError('the parameter "minValue" is invalid: it must be an integer')
    if max_value is not None and not isinstance(max_value, (int, long)):
        raise TypeError('the parameter "maxValue" is invalid: it must be an integer')
    # Verifico l'appartenenza al range
    if min_value is not None and value < min_value:
        raise ValueError('the parameter "%s" must be an integer greater than or equal to %d' % (name, min_value))
    if max_value is not None and value > max_value:
        raise ValueError('the parameter "%s" must be an integer lower than or equal to %d' % (name, max_value))


def check_number(value, name, min_value=None, max_value=None):
    """
    La funzione verifica che la variabile "value" sia un numero reale, compreso nell'intervallo dichiarato
    """
    # Verifico fino al tipo float, per variabile ed estremi del range (se dichiarati)
    if not isinstance(value, (int, long, float)):
        raise TypeError('the parameter "%s" is invalid: it must be a number' % name)
    if min_value is not None and not isinstance(min_value, (int, long, float)):
        raise TypeError('the parameter "minValue" is invalid: it must be a number')
    if max_value is not None and not isinstance(max_value, (int, long, float)):
        raise TypeError('the parameter "maxValue" is invalid: it must be a number')
    # Verifico l'appartenenza al range
    if min_value is not None and value < min_value:
        raise ValueError('the parameter "%s" must be a number greater than or equal to %d' % (name, min_value))
    if max_value is not None and value > max_value:
        raise ValueError('the parameter "%s" must be a number lower than or equal to %d' % (name, max_value))


def check_array(value, name, dimensions=1, of=None):
    """
    La funzione verifica che la variabile "value" sia un vettore multidimensionale.
    Eventualmente, posso verificare il tipo di dato delle singole celle (pari a of)
    """
    # Controllo dell'input
    check_integer(dimensions, 'dimensions', min_value=1)

    def recursive_check(val, actual_dimension, of_type):
        """
        Funzione ricorsiva, usata per effettuare il controllo vero e proprio
        """
        # Condizione di terminazione
        if actual_dimension == 1:
            # Eventuale controllo sul tipo di dato
            typeok = True
            if of_type is not None:
                try:
                    for x in val:
                        if not isinstance(x, of_type):
                            typeok = False
                            break
                except TypeError:
                    typeok = False
            # Risultato
            return typeok and isinstance(val, (list, tuple, set))

        # Ricorsione
        for x in val:
            if not recursive_check(x, actual_dimension - 1, of_type):
                return False
        return True

    # Controllo la variabile
    if not recursive_check(value, dimensions, of):
        raise TypeError('the parameter "%s" is invalid: it must be a %d-dimensional array' % (name, dimensions))


def check_timed_array(value, name):
    """
    La funzione verifica che "value" sia un'istanza della classe "TimedArray"
    """
    if not isinstance(value, TimedArray):
        raise TypeError('the parameter "%s" is invalid: it must be a timed array' % name)


def check_function(value, name):
    """
    La funzione verifica che la variabile "value" sia una funzione
    """
    if not isinstance(value, types.FunctionType):
        raise TypeError('the parameter "%s" is invalid: it must be a function' % name)


def check_dict(value, name):
    """
    La funzione verifica che la variabile "value" sia un dizionario Python
    """
    if not isinstance(value, dict):
        raise TypeError('the parameter "%s" is invalid: it must be a function' % name)


def input_int(msg, min_value=None, max_value=None):
    """
    La funzione permette di ricavare un numero intero come input utente.
    Se specificato, posso decidere un range di valori accettabili
    """
    # Controllo dell'input
    # minValue
    if min_value is not None:
        check_integer(min_value, 'minValue')
    # maxValue
    if max_value is not None:
        check_integer(max_value, 'maxValue', min_value=min_value)

    # Algoritmo
    while True:
        try:
            # Input utente: se non e' un numero intero, int() lancia un'eccezione
            n = int(input(msg + ': '))
            # Con assert, verifico il range di valori accettabili (se specificato)
            if min_value is not None:
                assert n >= min_value
            if max_value is not None:
                assert n <= max_value
            # Se arrivo fino a qui, l'input e' corretto ed esco dal ciclo
            break
        except:
            # L'input non e' un numero intero: creo il messaggio di errore
            msg_err = '\nPlease, insert an integer'
            if min_value is not None and max_value is not None:
                msg_err += ' between %d and %d' % (min_value, max_value)
            elif min_value is not None:
                msg_err += ' greater than or equal to %d' % min_value
            elif max_value is not None:
                msg_err += ' lower than or equal to %d' % max_value
            # Stampo a schermo il messaggio di errore
            print(msg_err)
    # Risultato
    return n


def input_float(msg, min_value=None, max_value=None):
    """
    La funzione permette di ricavare un numero reale come input utente.
    Se specificato, posso decidere un range di valori accettabili
    """
    # Controllo dell'input
    # minValue
    if min_value is not None:
        check_integer(min_value, 'minValue')
    # maxValue
    if max_value is not None:
        check_integer(max_value, 'maxValue', min_value=min_value)

    # Algoritmo
    while True:
        try:
            # Input utente: se non e' un numero reale, float() lancia un'eccezione
            n = float(input(msg + ': '))
            # Con assert, verifico il range di valori accettabili (se specificato)
            if min_value is not None:
                assert n >= min_value
            if max_value is not None:
                assert n <= max_value
            # Se arrivo fino a qui, l'input e' corretto ed esco dal ciclo
            break
        except:
            # L'input non e' un numero reale: creo il messaggio di errore
            msg_err = '\nPlease, insert a number'
            if min_value is not None and max_value is not None:
                msg_err += ' between %d and %d' % (min_value, max_value)
            elif min_value is not None:
                msg_err += ' greater than or equal to %d' % min_value
            elif max_value is not None:
                msg_err += ' lower than or equal to %d' % max_value
            # Stampo a schermo il messaggio di errore
            print(msg_err)
    # Risultato
    return n
