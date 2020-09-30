"""
Simulator and template for K-band (17-27) front ends

The current (2020-09-20) K-band control software is based on an *ad hoc* 
numerical menu based program written as needed during the lab tests of K1,
the prototype for K2.  This version defines a new controller in the object-
oriented style of ``MonitorControl``.

The commands from the old program that are still in use are implemented here in
the new OO framework.

Features
========

Feeds
-----

K2 has two feeds positioned along the focus ring at equal distances from the K
feed position.  They enable beam switching for cancelling out atmospheric
fluctuations.  Each feed has a digitally controlled wave-guide **ambient load**
for calibration.  Each feed also has a linear **orthomode** for separating the 
E-plane (=X, =H) polarization from the H-plane (=Y, =V).

Noise Diode
-----------
One noise diode feeds digitable controlled adjustable noise power *via* a 
four-way splitter into the waveguides behind the ambient loads.

Pre-Amplifiers
--------------
Cryogenic amplifiers provide about 30 dB of gain over the 17-27 GHz passbands.
The amplifier bias can be digitally switched off and on.

"""
# -*- coding: utf-8 -*-
import logging

from MonitorControl.FrontEnd import FrontEnd
from Observatory.WBDC import Attenuator

from local_dirs import log_dir
import support
from support.pyro import Pyro5Server
#import Electronics.Interfaces.LabJack as LabJack

  
module_logger = logging.getLogger(__name__)

class K_FE(support.PropertiedClass):
  """
  """
  def __init__(self):
    """
    """
    self.feed = {1: Feed(1), 2: Feed(2)}
    self.nd = NoiseDiode()
                 2: {"E": Channel(beam=2, pol="E"),
                     "H": Channel(beam=2, pol="H")}}
  
  class Feed(object):
    """
    Feed horn and associated waveguide components
    """
    def __init__(self, number):
      """
      Assign Feed to a beam defined by the feed position
      """
      self.number = number # number
      self.position = [0, -0.012, +0.012][number] # inch
      self.name = [None, "minus", "plus"][number]
      self.load = AmbientLoad()
      self.chan = {"E": Channel(pol="E"), "H": Channel(pol="H")}

    class AmbientLoad(object):
      """
      Waveguide load attached behind feed
      """
      def __init__(self):
        """
        assign an ambient load to parent Feed
        """
        self.state = 0 # out
    
      def set_state(self, state):
        """
        """
        self.state = state
    
      def get_state(self):
        """
        """
        return self.state
    
    class Channel(object):
      """
      Output for one polarization from an orthomode
      """
      def __init__(self, pol):
        """
        assign polarization
        """
        self.pol = pol
      
      def read_PM(self):
        """
        read power meter attached to channel
        """
        pass
  
  class NoiseDiode(object):
    """
    Noise diode which injects noise power into all channels
    """
    def __init__(self):
      """
      """
      self.state = 0 # off
    
    def set_state(self, state):
      """
      """
      self.state = state
    
    def get_state(self):
      """
      """
      return self.state
    
    class Attenuator(object):
      """
      PIN diode attenuator for noise diode signal
      """
      def __init__(self, atten=0):
        """
        initialize attenuator at 0 dB
        """
        self.atten = atten
      
      def set_atten(self, atten):
        """
        """
        self.atten = atten
      
      def get_atten(self):
        """
        """
        return self.atten
      
  
@Pyro5.api.expose
class FEServer(Pyro5Server, K_FE):
    """
    Server that controls the Front End.
    """
    def __init__(self, logger=None, **kwargs):
        if not logger:
            logger = logging.getLogger(module_logger.name+".FEServer")
        Pyro5Server.__init__(self, "FE", logger=logger, **kwargs)
        K_FE.__init__(self)

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
            self.load = 0
        elif state.strip().lower() == 'load':
            self.load = 1
        self.frontend.set_feed(feed, state)

    def get_ND_state(self):
        """Return current state of Noise diode"""
        return self.load.get_state()

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
def create_arg_parser():
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
    

def main(server_cls):
    """
    starts logging, creates a server_cls object, launches the server object
    
    This is generic; not specific to the spectrometer server.
    """
    def _main():
        from support.logs import setup_logging
        import datetime
        import os
        
        parsed = create_arg_parser().parse_args()
        
        level = logging.DEBUG
        if not parsed.verbose:
            level = logging.INFO
        logdir = "/usr/local/Logs/"+socket.gethostname()
        if not os.path.exists(logdir):
            logdir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.datetime.utcnow().strftime("%Y-%j-%Hh%Mm%Ss")
        logfile = os.path.join(
            logdir, "{}_{}.log".format(
                server_cls.__name__, timestamp
            )
        )
        setup_logging(logLevel=level, logfile=None)
        server = server_cls(
           name="test"
        )
        # print(server.feed_change(0, 0, 0))
        server.launch_server(
            ns=False,
            objectId="backend",
            objectPort=50000,
            local=parsed.local,
            threaded=False
        )

    return _main
    
if __name__ == "__main__":
    main(FEServer)()

