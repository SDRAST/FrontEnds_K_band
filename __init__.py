"""
K_4ch - module for K_4ch front end class

This provides a superclass with code common to both WBDC versions
"""
import logging
import copy

from MonitorControl import Port, Beam, ComplexSignal, ObservatoryError
from MonitorControl.FrontEnds import FrontEnd

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
      inputs = K_4ch.feeds
    FrontEnd.__init__(self, name, inputs=inputs, output_names=output_names)
    self.logger.debug(" initializing K_4ch subclass %s", self)
    self.logger.info(" %s input channels: %s", self, str(self.inputs))
    self.channel = {}
    self.data['frequency'] = 22.0 # GHz
    self.data['bandwidth'] = 10. # GHz
    keys = self.inputs.keys()
    keys.sort()
    for feed in keys:
      index = keys.index(feed)
      beam_signal = copy.copy(self.inputs[feed].signal)
      beam_signal.name = name+feed
      self.channel[feed] = self.Channel(self, feed,
                                        inputs={feed: self.inputs[feed]},
                                        output_names=output_names[index],
                                        signal=beam_signal)
    self.logger.info(" %s output channel: %s", self, str(self.outputs))
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
      self.logger = logging.getLogger(parent.logger.name+".Channel")
      FrontEnd.Channel.__init__(self, parent, name, inputs=inputs,
                                  output_names=output_names, active=active)
      self.logger.debug(" initializing K_4ch channel %s", self)
      self.logger.debug(" %s inputs: %s", self, str(inputs))
      for pol in K_4ch.pols:
        index = K_4ch.pols.index(pol)
        ID = output_names[index]
        self.outputs[ID] = Port(self, ID,
                                source=inputs[name],
                                signal=ComplexSignal(signal, pol))
        #self.outputs[ID].signal.FITS['OBSFREQ'] = parent['frequency']*1e9 # Hz
        #self.outputs[ID].signal.FITS['BANDWID'] = parent['bandwidth']*1e9 # Hz
        self.outputs[ID].signal['beam'] = parent.name+name
        self.outputs[ID].signal['frequency'] = parent['frequency']*1e9 # Hz
        self.outputs[ID].signal['bandwidth'] = parent['bandwidth']*1e9 # Hz
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
