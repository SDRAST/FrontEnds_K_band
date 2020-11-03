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

Pulse Code Generator
--------------------
A digitally controlled PCG can inject rails of tones with 1 or 4 MHz spacing via
the same path as the noise diodes.

Pre-Amplifiers
--------------
Cryogenic amplifiers provide about 30 dB of gain over the 17-27 GHz passbands.
The amplifier bias can be digitally switched off and on, by feed pairs, *i.e.*
one control for both polarizations.

Reference
=========
T.B.H.~Kuiper, M.~Franco, S.~Smith, G.~Baines, L.J.~Greenhill, S.~Horiuchi, 
T.~Olin, D.C.~Price, D.~Shaff, L.P.~Teitelbaum, S.~Weinreb, L.~White, I.~Zaw
"The 17-27 GHz Dual Horn Receiver on the NASA 70 m Canberra Antenna",
J. Astron. Instr., **8**, Issue 4, id. 1950014 (2019)



Legacy Option Codes
===================
From ``Observatory/Receivers/WBDC/WBDC-Python/WBDC_control.py``.  These are only
the codes that pertain to the front end. Only those followed by * are 
implemented here::

  Front End Primitives:
  19 - show front end bit states
  20 - toggle feed 1 position
  21 - toggle feed 2 position
  Front end M&C
  12 - check feeds *
  13 - set feed 1 to sky *
  14 - set feed 1 to load *
  15 - set feed 2 to sky *
  16 - set feed 2 to load *
  22 - get noise diode state *
  23 - noise diode on *
  24 - noise diode off *
  25 - pre-amp 1 bias on *
  26 - pre-amp 1 bias off *
  27 - pre-amp 2 bias on *
  28 - pre-amp 2 bias off *
  33 - phase cal rail 1 MHz
  34 - phase cal rail 4 MHz
  35 - phase cal on
  36 - phase cal off
  Other primitives:
  17 - read power meters *
  39 - set power meters to 'W' *
  40 - set power meters to 'dBm' *
  31 - read temperatures *
  60 - Modulate noise diode at 4Hz for ACME calibration
  
  Signal Generator Controls:
  54 - Reset Signal Generator
  55 - Read Signal Generator Status
  56 - Turn RF off
  57 - Turn RF On
  58 - Set Signal Generator Freq
  59 - Set Signal Generator Amplitude
  Option 55 is not functioning correctly. Right GPIB commands need to be found 
  for reading the Amplitude and RF status
"""
# -*- coding: utf-8 -*-
import logging
import Pyro5
import random

from local_dirs import log_dir
import Radio_Astronomy as RA
import support
from support.pyro.pyro5_server import Pyro5Server

logger = logging.getLogger(__name__)

T_CBG = 2.73 # K
T_rx = {1: {"E": 19.65, "H": 19.75}, 2: {"E": 22.27, "H": 20.55}} # from paper
T_rs = 2 # K, blockage, spillover, ohmic losses, from paper
T_atm = 9 # K, median atmospheric brightness, from paper
T_amb = 273.15 + 20 # inside feed cone

def T_sky(feed, pol):
  return T_CBG + T_rx[feed][pol] + T_rs + T_atm
  
def T_load(feed, pol):
  return T_rx[feed][pol] + T_amb

# these divide T_op to give power in W
tsys_factor = {1: {'E':  999883083, 'H': 840000000},
               2: {'E':  690000000, 'H': 705797017}}

@Pyro5.api.expose                
class K_FE(support.PropertiedClass):
  """
  """
  def __init__(self):
    """
    """
    support.PropertiedClass.__init__(self)
    self.logger = logging.getLogger(logger.name+'.K_FE')
    self.feed = {1: K_FE.Feed(self, 1), 2: K_FE.Feed(self, 2)}
    self.nd = K_FE.NoiseDiode()
    # These are receiver properties as well as signal properties
    self.data['frequency'] = 22.0 # GHz
    self.data['bandwidth'] = 10.  # GHz
  
  class Feed(object):
    """
    Feed horn and associated waveguide components
    """
    def __init__(self, parent, number):
      """
      Assign Feed to a beam defined by the feed position 1 or 2
      """
      self.parent = parent
      self.logger = logging.getLogger(logger.name+'.K_FE.Feed')
      self.number = number # number
      self.position = [0, -0.012, +0.012][number] # inch
      self.name = [None, "minus", "plus"][number]
      self.load = K_FE.Feed.AmbientLoad()
      self.chan = {"E": K_FE.Feed.Channel(self, pol="E"), 
                   "H": K_FE.Feed.Channel(self, pol="H")}
      self.set_preamp_bias(state=1)
      
    def set_preamp_bias(self, state=1):
      """
      preamp state 0 is bias off, state 1 is bias on
      """
      self.preamp_state = state

    class AmbientLoad(object):
      """
      Waveguide load attached behind feed
      """
      def __init__(self):
        """
        assign an ambient load to parent Feed
        """
        self.logger = logging.getLogger(logger.name+'.K_FE.Feed.AmbientLoad')
        self.state = 0 # out
        self.temp = 320 # K, approx. physical temperature
    
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
      def __init__(self, parent, pol):
        """
        assign polarization
        """
        self.logger = logging.getLogger(logger.name+'.K_FE.Feed.Channel')
        self.parent = parent
        self.pol = pol
        self.set_PM_mode('W')
      
      def set_PM_mode(self, mode):
        """
        """
        self.PM_mode = mode
        
      def read_PM(self):
        """
        read power meter attached to channel
        """
        if self.parent.preamp_state == 0:
          return 1e-10
        feed = self.parent.number
        if self.parent.load.state:
          # load is in
          T_op = T_load(feed, self.pol) + 0.1*random.random()
        else:
          T_op = T_sky(feed, self.pol) + 0.5*random.random()
        self.logger.debug("read_PM: T_op = %.1f", T_op)
        nd = self.parent.parent.nd
        if nd.state:
          T_op += nd.get_temperature()
        return T_op/tsys_factor[feed][self.pol]
        
  class NoiseDiode(object):
    """
    Noise diode which injects noise power into all channels
    
    The unattenuated ND power is 384.6 K. (See program ``ND_atten_fit.py``)
    """
    def __init__(self):
      """
      """
      self.logger = logging.getLogger(logger.name+'.K_FE.NoiseDiode')
      self.max = 384.6 # K
      self.state = 0 # off
      self.atten = K_FE.NoiseDiode.Attenuator(self, atten=-9.86)
      self.get_temperature()
    
    def set_state(self, state):
      """
      """
      self.state = state
    
    def get_state(self):
      """
      """
      return self.state
    
    def get_temperature(self):
      """
      """
      self.temp = self.max*RA.gain(self.atten.atten)
      return self.temp
    
    class Attenuator(object):
      """
      PIN diode attenuator for noise diode signal
      
      With control voltage 0 V the ND power is about 39 K.
      """
      def __init__(self, parent=None, atten=0):
        """
        initialize attenuator at 0 dB
        """
        self.logger = logging.getLogger(logger.name+'.K_FE.NoiseDiode.Attenuator')
        self.atten = atten
      
      def set_atten(self, atten):
        """
        """
        self.atten = atten
        self.parent.temp = self.parent.max*RA.gain(self.atten)
      
      def get_atten(self):
        """
        """
        return self.atten
        
      def ctrl_voltage(self, ND_K):
        """
        control voltage for specify ND power in kelvin
        """
        coefs = array([  3.85013993e-18,  -6.61616152e-15,   4.62228606e-12,
                        -1.68733555e-09,   3.43138077e-07,  -3.82875899e-05,
                         2.20822016e-03,  -8.38473034e-02,   1.52678586e+00])
        return scipy.polyval(coefs,ND)
  
  # K_FE methods for Pyro clients
  def get_feed(self, feed):
    """
    Get the load position
    Args:
      feed (int): 1 or 2
    Returns:
      bool
    """
    self.logger.debug("get_feed: for feed %s", feed)
    return self.feed[feed].load.get_state()
    
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
      self.feed[feed].load = 0
    elif state.strip().lower() == 'load':
      self.feed[feed].load = 1
    self.frontend.set_feed(feed, state)

  def get_ND_state(self):
    """Return current state of Noise diode"""
    return self.nd.state

  def set_ND_state(self, state):
    """
    Set the noise diode state
    Args:
      flag (bool): Turn on or off. True is on, False is off.
    """
    if state:
      # True; turn on
      self.nd.set_state(1)
    else:
      self.nd.set_state(0)
    self.logger.debug("set_ND_state: to {}".format(self.nd.state))

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
    self.feed[feed].chan(feed, state)

  def read_PMs(self):
    """
    computes roughly 50~K on sky
    """
    number=0; readings = []
    for fnum in sorted(self.feed):
      for pol in sorted(self.feed[fnum].chan):
        number += 1
        readings.append((number, self.feed[fnum].chan[pol].read_PM()))
    self.logger.debug("read_PMs: readings: %s", readings)
    return readings
    
  def read_temp(self):
    """
    read the four front end physical temperatures
    """
    return {"load1": self.feed[1].load.temp,
            "12K":    15 + 0.01*random.random(),
            "load2": self.feed[2].load.temp,
            "70K":    80 + 0.5*random.random()}
  

class FEServer(Pyro5Server, K_FE):
    """
    Server that controls the Front End.
    """
    def __init__(self, name, FElogger=None, **kwargs):
        if not FElogger:
            FElogger = logging.getLogger(logger.name+".FEServer")
        Pyro5Server.__init__(self, obj=self, name=name, logger=FElogger, **kwargs)
        K_FE.__init__(self)
    
    @Pyro5.api.expose
    def set_WBDC(self, option):
      """
      """
      if option==12:
        # to get the feed states
        statenames = ["sky", "load"]
        response = ""
        feeds = list(self.feed.keys())
        feeds.sort()
        for feed in feeds:
          response += "feed {} is on the {}\n".format(feed, 
                                         statenames[self.feed[feed].load.state])
        self.logger.debug("set_WBDC({}) response:\n{}".format(option, response))
        return response
      elif option==13:
        self.logger.debug("set_WBDC: set feed 1 to sky")
        self.feed[1].load.set_state(state=0)
      elif option==14:
        self.logger.debug("set_WBDC: set feed 1 to load")
        self.feed[1].load.set_state(state=1)
      elif option==15:
        self.logger.debug("set_WBDC: set feed 2 to sky")
        self.feed[2].load.set_state(state=0)
      elif option==16:
        self.logger.debug("set_WBDC: set feed 2 to load")
        self.feed[2].load.set_state(state=1)
      elif option==22:
        # to get the noise diode state
        return self.nd.state        
      elif option==23:
        # to turn the noise diode on
        self.nd.set_state(1)
      elif option==24:
        # to turn the noise diode off
        self.nd.set_state(0)
      elif option==25:
        # to turn the preamp 1 on
        self.feed[1].set_preamp_bias(1)
      elif option==26:
        # to turn the preamp 1 off
        self.feed[1].set_preamp_bias(0)
      elif option==27:
        # to turn the preamp 2 on
        self.feed[2].set_preamp_bias(1)
      elif option==28:
        # to turn the preamp2 off
        self.feed[2].set_preamp_bias(0)
      elif option==390:
        # to set the power meter mode to ``W''
        self.feed[1].chan['E'].set_PM_mode('W')
      elif option==391:
        self.feed[1].chan['H'].set_PM_mode('W')
      elif option==392:
        self.feed[2].chan['E'].set_PM_mode('W')
      elif option==393:
        self.feed[2].chan['H'].set_PM_mode('W')
      elif option==400:
        # to ```dBm''.
        self.feed[1].chan['E'].set_PM_mode('dBm')
      elif option==401:
        self.feed[1].chan['H'].set_PM_mode('dBm')
      elif option==402:
        self.feed[2].chan['E'].set_PM_mode('dBm')
      elif option==403:
        self.feed[2].chan['H'].set_PM_mode('dBm')
      else:
        self.logger.error('set_WBDC: option %d not recognized', option)
        
def create_arg_parser():
    """
    """
    import argparse
    parser = argparse.ArgumentParser(description="Start Front End Pyro5 server")

    parser.add_argument('--remote_server_name', '-rsn', dest='remote_server_name',
                        action='store', 
                        default='localhost', type=str, required=False,
                        help="""Specify the name of the remote host. If you're trying to access a Pyro nameserver that
                             is running locally, then use localhost. If you supply a value other than 'localhost'
                             then make sure to give other remote login information.""")

    parser.add_argument('--remote_port', '-rp', dest='remote_port',
                        action='store', type=int, required=False, 
                        default=None,
                        help="""Specify the remote port.""")

    parser.add_argument("--ns_host", "-nsn", dest='ns_host', action='store', 
                        default='localhost',
                        help="Specify a host name for the Pyro name server. Default is localhost")

    parser.add_argument("--ns_port", "-nsp", dest='ns_port', action='store',
                        default=50000, type=int,
                        help="Specify a port number for the Pyro name server. Default is 50000.")

    parser.add_argument("--simulated", "-s", dest='simulated', action='store_true', 
                        default=False,
                        help="Specify whether or not the server is running in simulator mode.")

    parser.add_argument("--local", "-l", dest='local', action='store_true', 
                        default=True,
                        help="Specify whether or not the server is running locally or on a remote server.")

    parser.add_argument("--verbose", "-v", dest="verbose", action='store_true', 
                        default=False,
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
        import socket
        
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
            objectId="FE",
            objectPort=50000,
            local=parsed.local,
            threaded=False
        )

    return _main
    
if __name__ == "__main__":
    main(FEServer)()

