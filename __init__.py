"""
K_4ch - module for K_4ch front end class

This provides a superclass with code common to both WBDC versions

sub-package implements control and monitoring of the
K-band front end using a LabJack

Signals
=======
These are the signals monitored or controlled by the LabJack::

  FIO  IO   type   description
  ---  --   ----   -----------
    0   0    DO    feed 1 load control (pulsed high-low-high)
    1   1    DO    feed 2 load control (pulsed high-low-high)
    2   2    DO    amp 1 bias control (pulsed high-low-high)
    3   3    DO    amp 2 bias control (pulsed high-low-high)
    4   4    DO    phase-cal (high = True = on)
    5   5    DO    phase-cal rail (high = True = 4 MHz, low = 1 MHz)
    6   6    DI    controls LabJack TickDAC
    7   7    DI    controls LabJack TickDAC

  EIO  IO   type   description
  ---  --   ----   -----------
    0   8    DI    amp 1 bias on (high = True, low = False)
    1   9    DI    amp 2 bias on
    2  10    AIN   -12 V
    3  11    AIN   +12 V
    4  12    AIN    +5 V
    5  13    AIN    +8 V
    6  14    AIN   Lambda supply
    7  15    DO    ND control

  CIO  IO   type   description
  ---  --   ----   -----------
    0  16    DI    feed 1 in load
    1  17    DI    feed 2 in load
    2  18    DI    feed 1 on sky
    3  19    DI    feed 2 on sky
"""
import copy
import logging
import math
import Pyro
import time

from MonitorControl import Port, Beam, ComplexSignal, ObservatoryError
from MonitorControl.FrontEnds import FrontEnd
from support.pyro import get_device_server

module_logger = logging.getLogger(__name__)

feeds = ["F1", "F2"] # default names for the feeds
pols =  ["P1", "P2"]
plane = {"P1": "E", "P2": "H"}

class K_4ch(FrontEnd):
  """
  The 4-channel downconverter with four inputs for two pols and two feeds.

  The class variable lists 'feeds' and 'pols' will define output port labels::
    F1P1, F1P2, F2P1, F2P2.
  The polarization type is definitely linear but the orientations are not
  yet known.
  
  Attributes
  ==========
  Pulic::
    channel  - electronics associated with a feed
    data     - dict of properties like bandwidth and center frequency
    hardware - remote hardware server
    logger   - logging.Logger object
    name     - text identifier
    outputs  - Port objects
  
  Notes
  =====
  This version uses the legacy FE_Pyro_server, which needs to be replaced with
  something more capable.
  """  
  def __init__(self, name, inputs=None, output_names=[['F1P1','F1P2'],
                                                      ['F2P1','F2P2']],
               active=True, hardware = False):
    """
    Create a K_4ch instance
    
    @param name : unique identifier for this port
    @type  name : str

    @param active : True is the FrontEnd instance is functional
    @type  active : bool
    """
    self.name = name
    mylogger = logging.getLogger(module_logger.name+".K_4ch")
    mylogger.debug(" initializing %s", self)
    self.logger = mylogger # needed for defining inputs
    if inputs == None:
      # This is for Receiver stand-alone testing
      inputs = {}
      for feed in feeds:
        inputs[feed] = Port(self, feed, signal=Beam(feed))
    mylogger.debug(" %s input channels: %s", self, str(inputs))
    mylogger.debug(" output names: %s", output_names)
    # the next redefines self.logger
    FrontEnd.__init__(self, name, inputs=inputs, output_names=output_names)
    if hardware:
      self.hardware = get_device_server("FE_server-krx43", pyro_ns="crux")
      timeout = 10
      while timeout:
        try:
          self.set_ND_off()
        except Pyro.errors.ProtocolError, details:
          mylogger.info("__init__: %s (%f sec left)",
                       details,timeout)
          if str(details) == "connection failed":
            timeout -= 0.5
            time.sleep(0.5)
        else:
          # command succeeded
          timeout = 0.        
    else:
      self.hardware = hardware # that is, False
    # restore logger name
    self.logger = mylogger
    self.channel = {}
    # These are receiver properties as well as signal properties
    self.data['frequency'] = 22.0 # GHz
    self.data['bandwidth'] = 10.  # GHz
    keys = self.inputs.keys()
    keys.sort()
    for feed in keys:
      index = keys.index(feed)
      beam_signal = Beam(feed)
      for prop in self.data.keys():
        beam_signal.data[prop] = self.data[prop]
      self.channel[feed] = self.Channel(self, feed,
                                        inputs={feed: self.inputs[feed]},
                                        output_names=output_names[index],
                                        signal=beam_signal)
      self.channel[feed].retract_load()
      for key in self.channel[feed].outputs.keys():
        pol = key[-2:]
        self.channel[feed].outputs[key].signal['pol'] = plane[pol]
    self.logger.debug("%s output channels: %s\n", self, str(self.outputs))
    self.set_ND_off()
    self.update()

  def update(self):
    """
    Updates the states
    """
    self.feed_states()
    self.get_ND_state()
  
  def feed_states(self):
    """
    Report the waveguide load state
    """
    if self.hardware:
      response = self.hardware.set_WBDC(12)
      lines = response.split('\n')
      for line in lines[1:2]:
        parts = line.split()
        name = "KF"+parts[1]
        if parts[3] == "sky":
          self.channel[name].load_in = False
        else:
          self.channel[name].load_in = True
    return self.channel["F1"].load_in, self.channel["F2"].load_in
      
  def set_ND_on(self):
    if self.hardware:
      response = self.hardware.set_WBDC(23)
    else:
      response = "on"
    self.ND = True
    return response

  def set_ND_off(self):
    if self.hardware:
      response = self.hardware.set_WBDC(24)
    else:
      response = "off"
    self.ND = False
    return response

  def get_ND_state(self):
    """
    """
    if self.hardware:
      self.ND = self.hardware.set_WBDC(22)
    return self.ND
  
  def set_ND_temp(self, value):
    """
    """
    return "hardware not yet available"
      
  def set_PCG_on(self):
    self.PCG = True
    return "hardware not yet available"

  def set_PCG_off(self):
    self.PCG = False
    return "hardware not yet available"

  def set_PCG_rail(self,spacing):
    if spacing == 1 or spacing == 4:
      self.PCG_rail = spacing
    else:
      raise ObservatoryError(spacing,"is not a valid PCG tone interval")
    return "hardware not available"

  def read_PMs(self):
    """
    """
    return self.hardware.read_pms()
    
  def read_temps(self):
    """
    """
    return self.hardware.read_temp()
  
  def Tsys_vacuum(self, beam=1, pol="R", mode=None, elevation=90):
    """
    """
    return 36/math.sin(math.pi*elevation/180) # K

  class Channel(FrontEnd.Channel):
    """
    Electronics associated with a feed
    
    Attributes
    ==========
    Public::
      load_in - True if load is inserted
      logger  - logging.Logger instance
      number  - numerical feed index: 0 or 1
      outputs - Port objects, identical with parent port objects
      parent  - front-end to which this belongs
    """
    def __init__(self, parent, name, inputs=None, output_names=None,
                 signal=None, active=True):
      """
      """
      mylogger = logging.getLogger(parent.logger.name+".Channel")
      self.name = name
      self.number = int(name[-1])-1
      self.parent = parent
      self.hardware = self.parent.hardware
      mylogger.debug(" initializing for %s", self)
      FrontEnd.Channel.__init__(self, parent, name, inputs=inputs,
                                  output_names=output_names, active=active)
      self.logger = mylogger
      self.logger.debug(" %s inputs: %s", self, str(inputs))
      self.PM = {}
      for pol in pols:
        index = pols.index(pol)
        ID = output_names[index]
        self.outputs[ID] = Port(self, ID,
                                source=inputs[name],
                                signal=ComplexSignal(signal, name=pol,
                                pol=pol))
        self.parent.outputs[ID] = self.outputs[ID]
        self.PM[pol] = K_4ch.Channel.PowerMeter(self, pol)
      self.logger.debug(" %s outputs: %s", self, str(self.outputs))
      self.retract_load()

    def insert_load(self):
      if self.hardware:
        self.hardware.set_WBDC(14+2*self.number)
      self.load_in = True

    def retract_load(self):
      if self.hardware:
        self.hardware.set_WBDC(13+2*self.number)
      self.load_in = False

    def set_preamp_on(self):
      if self.hardware:
        response = self.hardware.set_WBDC(25+2*self.number)
      else:
        response = "on"
      self.preamp_on = True
      return response

    def set_preamp_off(self):
      if self.hardware:
        response = self.hardware.set_WBDC(26+2*self.number)
      else:
        response = "off"
      self.preamp_on = False
      return response
      
    class PowerMeter:
      """
      Client to power meter on remote server
      
      Each front end channel has two power meters, for P1 and P2 respectively
      """
      def __init__(self, parent, pol):
        """
        """
        self.parent = parent
        self.hardware = self.parent.hardware
        if pol.upper() == "P1" or pol.upper() == "E" or pol == 1:
          self.pol = 0
          self.name = "F"+str(self.parent.number+1)+"P1"
        elif pol.upper() == "P2" or pol.upper() == "H" or pol == 2:
          self.name = "F"+str(self.parent.number+1)+"P2"
          self.pol = 1
        else:
          raise RuntimeError, "invalid polarization code"
        self.number = 1 + self.parent.number*2 + self.pol
      
      def set_mode(self, mode):
        """
        """
        if mode.upper() == "W":
          response = self.hardware.set_WBDC(390+self.number)
        elif mode.lower() == "dbm":
          response = self.hardware.set_WBDC(400+self.number)
        return response
        
          
