import cloud_stats as cs
import simpy
from collections import deque
from numpy import random
from shared_folder import SharedFolder
from device import Device
import file_manager as fm


# shared folders per device - negative_binomial (s, mu)
DV_DG = [0.470, 1.119]
# device per shared folder - negative_binomial (s, mu)
SF_DG = [0.231, 0.537]


class CloudEnvironment(object):
    """
    La classe modellizza un servizio Cloud di file sharing
    """

    def __init__(self, n_devices, logger, server=True):
        """
        :param n_devices: numero di device della rete
        :param logger: elabora il file di log
        :param server: booleano, indica la presenza di un server centrale (False = P2P)
        """
        self.env = simpy.Environment()
        self.logger = logger
        self.file_manager = fm.FileManager(self.logger)
        self.devices = {}
        self.shared_folders = {}
        self.server = server
        self.stats = cs.StatsManager(n_devices, self.devices, self.env, server)
        self.generate_network(n_devices)

    def run(self, until):
        # Lancia la simulazione
        self.stats.new_simulation(until)
        self.env.run(until=until)
        # Statistiche di fine elaborazione
        self.stats.stats()

    def generate_network(self, num_dv):
        # derive the expected number of shared folders using the negative_binomials

        # this piece is just converting the parameterization of the
        # negative_binomials from (s, mu) to "p". Then, we use the rate between
        # the means to estimate the expected number of shared folders
        # from the given number of devices

        dv_s = DV_DG[0]
        dv_m = DV_DG[1]
        dv_p = dv_s / (dv_s + dv_m)
        nd = 1 + (dv_s * (1.0 - dv_p) / dv_p)

        sf_s = SF_DG[0]
        sf_m = SF_DG[1]
        sf_p = sf_s / (sf_s + sf_m)
        dn = 1 + (sf_s * (1.0 - sf_p) / sf_p)

        # the number of shared folders is finally derived
        num_sf = int(num_dv * nd / dn)

        # sample the number of devices per shared folder (shared folder degree)
        sf_dgr = [x + 1 for x in random.negative_binomial(sf_s, sf_p, num_sf)]

        # sample the number of shared folders per device (device degree)
        dv_dgr = [x + 1 for x in random.negative_binomial(dv_s, dv_p, num_dv)]

        # create the population of edges leaving shared folders
        l = [i for i, j in enumerate(sf_dgr) for k in range(min(j, num_dv))]
        random.shuffle(l)
        sf_pop = deque(l)

        # create empty shared folders
        for sf_id in range(num_sf):
            self.shared_folders[sf_id] = SharedFolder(sf_id)

        # first we pick a random shared folder for each device
        for dv_id in range(num_dv):
            self.devices[dv_id] = Device(dv_id, self.env, self.file_manager, self.stats, self)

            sf_id = sf_pop.pop()
            self.devices[dv_id].add_shared_folder(self.shared_folders[sf_id])
            self.shared_folders[sf_id].add_device(self.devices[dv_id])

        # then we complement the shared folder degree

        # we skip devices with degree 1 in a first pass, since they just got 1 sf
        r = 1

        # we might have less edges leaving devices than necessary
        while sf_pop:
            # create the population of edges leaving devices
            l = [i for i, j in enumerate(dv_dgr) for k in range(min(j - r, num_sf))]
            random.shuffle(l)
            dv_pop = deque(l)

            # if we need to recreate the population, we use devices w/ degree 1 too
            r = 0

            while sf_pop and dv_pop:
                dv = dv_pop.pop()
                sf = sf_pop.pop()

                # we are lazy and simply skip the unfortunate repetitions
                if not self.shared_folders[sf] in self.devices[dv].my_shared_folders:
                    self.devices[dv].add_shared_folder(self.shared_folders[sf])
                    self.shared_folders[sf].add_device(self.devices[dv])
                else:
                    sf_pop.append(sf)

    def look_for_peers(self, f):
        """
        Ritorna l'elenco di dispositivi attualmente loggati che hanno il file "f" di interesse
        """
        sf = f.get_shared_folder()
        on_devices = filter(lambda d: d.is_on(), self.devices.values())
        return filter(lambda d: d.has_file(f) and d.has_shared_folder(sf), on_devices)
