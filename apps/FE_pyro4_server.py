# -*- coding: utf-8 -*-
import logging

from pyro_support import Pyro4Server, config

from Observatory import FrontEnd
from Observatory.WBDC import Attenuator
import Electronics.Interfaces.LabJack as LabJack

module_logger = logging.getLogger(__name__)

@config.expose
class FEServer(Pyro4Server):
    """
    Server that controls the Front End.
    """
    def __init__(self, logger=None, **kwargs):
        if not logger:
            logger = logging.getLogger(module_logger.name+".FEServer")
        Pyro4Server.__init__(self, "FE", logger=logger, **kwargs)
        self.lj = None # labjacks
        self.frontend = None # Front End
        self.atten = {}
        # Find available devices
        self.logger.debug("__init__: Finding LabJack devices.")
        available = LabJack.searchForDevices()
        self.logger.debug("__init__: available: {}".format(available))
        # Connect to LabJacks
        if len(available) > 0:
            self.logger.debug("__init__: Connecting to LabJacks.")
            self.lj = self.connect_to_Labjacks(available)
            self.atten = {}
            if 3 in self.lj:
                try:
                    self.frontend = FrontEnd.FE(self.lj[3])
                except:
                    self.logger.error("Couldn't connect to Front end", exc_info=True)
                try:
                    self.atten[5] = Attenuator(self.lj[3], 6)
                except:
                    self.logger.error("Couldn't connect to Noise Diode", exc_info=True)
            else:
                self.logger.error("Front end and noise diode attenuator not available")

    def connect_to_Labjacks(self, available):
        """
        Connect to Labjacks
        Args:
            available (dict):
        Returns:
            dict
        """
        #          global WBDCdigLJ, WBDCattLJ, FElj
        for LJ in available.keys():
            self.logger.debug("connect_to_Labjacks: Serial:{}, local ID: {}".format(LJ, available[LJ]['localId']))
        self.lj = LabJack.connect_to_U3s()
        self.logger.info("connect_to_Labjacks: {} LabJacks connected".format(len(self.lj)))
        #          WBDC.init_WBDC_U3s(self.lj)
        for LJ in self.lj.keys():
            self.logger.debug("connect_to_Labjacks: Checking name for LabJack {}".format(LJ))
            self.lj[LJ].name = LabJack.U3name[str(self.lj[LJ].serial)]
            self.logger.debug("connect_to_labjack: {} {}".format(self.lj[LJ].localID, self.lj[LJ].name))
        return self.lj

    def read_temp(self):
        """
        Read rx temperatures
        """
        temp_dict = self.frontend.get_temps()
        return temp_dict

    def set_feed(self, feed, state):
        """
        Set the feed to either 1 or 2.
        Args:
            feed (int): 1 or 2
            state (str): 'load' or 'sky'
        Returns:
            None
        """
        if state.strip().lower() == 'sky':
            state = FrontEnd.sky
        elif state.strip().lower() == 'load':
            state = FrontEnd.load
        self.frontend.set_feed(feed, state)

    def get_ND_state(self):
        """Return current state of Noise diode"""
        return self.frontend.ND_state()

    def set_ND_state(self, flag):
        """
        Set the noise diode state
        Args:
            flag (bool): Turn on or off. True is on, False is off.
        """
        if flag:
            state = FrontEnd.on
        else:
            state = FrontEnd.off
        self.logger.debug("Setting ND state to {}".format(state))
        self.frontend.set_ND(state)

    def set_preamp_bias(self, feed, state):
        """
        Set the preamp bias state
        Args:
            feed (int):
            flag (bool):
        Returns:
            None
        """
        self.logger.debug("Setting preamp bias for feed {} to {}".format(feed, state))
        self.frontend.preamp_bias(feed, state)

    # def initialize_signal_generator(self):
    #     try:
    #         self.sg = SG('SGen_8673g')
    #     except:
    #         self.logger.error("siggen_controls: Could not initialize Signal Generator")
    #     # 54 - Reset Signal Generator
    #     if opt == 1:
    #         self.sg.init()
    #         return "SigGen initialized"
    #
    #     # 55 - Read Signal Generator Status
    #     elif opt == 2:
    #         self.logger.warning("siggen_controls: option 2 is not fully implemented yet.. ")
    #         text = str(self.sg.get_status())
    #         return text
    #         # sleep(5)
    #
    #     # 56 - Turn Signal Generator Off
    #     elif opt == 3:
    #         try:
    #             self.sg.power_off()
    #             return "Completed"
    #         except:
    #             return "Rejected"
    #
    #     # 57 - Turn Signal Generator On
    #     elif opt == 4:
    #         try:
    #             self.sg.power_on()
    #             self.sg.set_freq(freq)
    #             self.sg.set_ampl(amp)
    #             return "Completed"
    #         except:
    #             return "Rejected"
def simple_parse_args():
    """
    """
    parser = argparse.ArgumentParser(description="Start WBDC-2 Pyro4 server")

    parser.add_argument('--remote_server_name', '-rsn', dest='remote_server_name',
                        action='store', default='localhost', type=str, required=False,
                        help="""Specify the name of the remote host. If you're trying to access a Pyro nameserver that
                             is running locally, then use localhost. If you supply a value other than 'localhost'
                             then make sure to give other remote login information.""")

    parser.add_argument('--remote_port', '-rp', dest='remote_port',
                        action='store', type=int, required=False, default=None,
                        help="""Specify the remote port.""")

    parser.add_argument("--ns_host", "-nsn", dest='ns_host', action='store', default='localhost',
                        help="Specify a host name for the Pyro name server. Default is localhost")

    parser.add_argument("--ns_port", "-nsp", dest='ns_port', action='store',default=50000,type=int,
                        help="Specify a port number for the Pyro name server. Default is 50000.")

    parser.add_argument("--simulated", "-s", dest='simulated', action='store_true', default=False,
                        help="Specify whether or not the server is running in simulator mode.")

    parser.add_argument("--local", "-l", dest='local', action='store_true', default=False,
                        help="Specify whether or not the server is running locally or on a remote server.")

    parser.add_argument("--verbose", "-v", dest="verbose", action='store_true', default=False,
                        help="Specify whether not the loglevel should be DEBUG")

    return parser

def setup_logging(logfile, level):
    """
    Setup logging.
    Args:
        logfile (str): The path to the logfile to use.
    Returns:
        None
    """
    logging.basicConfig(level=level)
    s_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    f_formatter = logging.Formatter('%(levelname)s:%(asctime)s:%(name)s:%(message)s')

    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(f_formatter)

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(s_formatter)

    root_logger = logging.getLogger('')
    root_logger.handlers = []
    root_logger.addHandler(fh)
    root_logger.addHandler(sh)

if __name__ == "__main__":
    from socket import gethostname
    import datetime

    parsed = simple_parse_args().parse_args()
    name = 'FE_pyro4_server-'+gethostname()

    if parsed.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    logpath = "/usr/local/logs"
    timestamp = datetime.datetime.utcnow().strftime("%j-%Hh%Mm")
    logfile = os.path.join(logpath,"{}_{}.log".format(name, timestamp))

    setup_logging(logfile, loglevel)
    logger = logging.getLogger(name)
    logger.setLevel(loglevel)

    fe_server = FEServer(logger=logger, logfile=logfile)
    fe_server.launch_server("crux", ns_port=50000)
    # try:
    #     fe_server.launch_server(remote_server_name='crux.cdscc.fltops.jpl.nasa.gov', ns_port=50000)
    # except:
    #     fe_server.launch_server(remote_server_name='crux.cdscc.jpl.nasa.gov', ns_port=50000)
