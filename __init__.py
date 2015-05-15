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
import logging
import copy

from MonitorControl import Port, Beam, ComplexSignal, ObservatoryError
from MonitorControl.FrontEnds import FrontEnd

module_logger = logging.getLogger(__name__)

class K_4ch(FrontEnd):
  """
  The 4-channel downconverter with four inputs for two pols and two feeds.

  The class variable lists 'feeds' and 'pols' will define output port labels::
    F1P1, F1P2, F2P1, F2P2.
  The polarization type is definitely linear but the orientations are not
  yet known.
  """
  feeds = ["F1","F2"] # default names for the feeds
  pols = ["E", "H"]

  def __init__(self, name, inputs=None, output_names=None, active=True):
    """
    Create a K_4ch instance
    
    @param name : unique identifier for this port
    @type  name : str

    @param active : True is the FrontEnd instance is functional
    @type  active : bool
    """
    if inputs == None:
      # This is for Receiver stand-alone testing
      inputs = {}
      for feed in K_4ch.feeds:
        inputs[feed] = Port(self, feed, signal=Beam(feed))
    self.name = name
    mylogger = logging.getLogger(module_logger.name+".K_4ch")
    mylogger.debug(" initializing %s", self)
    mylogger.debug(" %s input channels: %s", self, str(inputs))
    mylogger.debug(" output names: %s", output_names)
    FrontEnd.__init__(self, name, inputs=inputs, output_names=output_names)
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
      #beam_signal.name = feed
      self.channel[feed] = self.Channel(self, feed,
                                        inputs={feed: self.inputs[feed]},
                                        output_names=output_names[index],
                                        signal=beam_signal)
    self.logger.debug("%s output channels: %s", self, str(self.outputs))
    self.set_ND_off()

  def _update_self(self):
    for key in self.channel.keys():
      self.channel[key].update_self()

  class Channel(FrontEnd.Channel):
    """
    """
    def __init__(self, parent, name, inputs=None, output_names=None,
                 signal=None, active=True):
      """
      """
      mylogger = logging.getLogger(parent.logger.name+".Channel")
      self.name = name
      mylogger.debug(" initializing for %s", self)
      FrontEnd.Channel.__init__(self, parent, name, inputs=inputs,
                                  output_names=output_names, active=active)
      self.logger = mylogger
      self.logger.debug(" %s inputs: %s", self, str(inputs))
      for pol in K_4ch.pols:
        index = K_4ch.pols.index(pol)
        ID = output_names[index]
        self.outputs[ID] = Port(self, ID,
                                source=inputs[name],
                                signal=ComplexSignal(signal, name=pol, pol=pol))
        #self.outputs[ID].signal.FITS['OBSFREQ'] = parent['frequency']*1e9 # Hz
        #self.outputs[ID].signal.FITS['BANDWID'] = parent['bandwidth']*1e9 # Hz
        #self.outputs[ID].signal['beam'] = parent.name+name
        #self.outputs[ID].signal['frequency'] = parent['frequency']*1e9 # Hz
        #self.outputs[ID].signal['bandwidth'] = parent['bandwidth']*1e9 # Hz
        parent.outputs[ID] = self.outputs[ID]
      self.logger.debug(" %s outputs: %s", self, str(self.outputs))
      self.retract_load()

    def insert_load(self):
      self.load_in = True

    def retract_load(self):
      self.load_in = False

    def set_preamp_on(self):
      self.preamp_on = True

    def set_preamp_off(self):
      self.preamp_on = False

  def set_ND_on(self):
    self.ND = True

  def set_ND_off(self):
    self.ND = False

  def set_PCG_on(self):
    self.PCG = True

  def set_PCG_off(self):
    self.PCG = False

  def set_PCG_rail(self,spacing):
    if spacing == 1 or spacing == 4:
      self.PCG_rail = spacing
    else:
      raise ObservatoryError(spacing,"is not a valid PCG tone interval")
