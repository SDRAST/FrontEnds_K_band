"""
K_4ch - module for K_4ch front end class

This provides a superclass with code common to both WBDC versions
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
  pols = ["X", "Y"]

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
    mylogger.info(" %s input channels: %s", self, str(inputs))
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
    self.logger.info("%s output channels: %s", self, str(self.outputs))
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
