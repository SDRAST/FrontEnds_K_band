"""
WBDC - module for Wide Band Down Converter receiver classes

There are two versions of the widband down-converter.

WBDC1 has two RF sections after the band-splitting filters, one for 22 and
24 GHz, two switch-selectable LOs and one IF section.

WBDC2 has five RF sections and five IF sections.  The sections, as well as
feed switching, polarization selection, etc. are the same.

Input Switching
---------------
The first stage of the WBDC allows the down-converter groups to be switched
between the two feeds.

Polarization Conversion
-----------------------
After the band-selecting RF filters, the linearly polarized signals from each
feed can be switched into a quadrature hybrid to be converted to cicular
polarizations.

WBDC1 Band Selection
--------------------
There are two programmable local oscillators and a switch selects between
to define the band to be down-converted.

Sideband Separation
-------------------
The down-conversion produces complex outputs (i.e. a pair of signals I and
Q).  There are switches which can direct each I/Q pair into a quadrature
hybrid to convert them to an upper and lower sideband pair.
"""
import logging
import copy

from MonitorControl import Switch, Port, IF,  ObservatoryError
from Receivers import Receiver
from support import contains, unique

class WBDC1(Receiver):
  """
  Wideband Downconverter Mod 1

  The down-converter accepts two Beam signals (each consisting of two
  polarization ComplexSignal signals).  It has two down-converters, each of
  which handles one Beam.

  WBDC1 monitor and control logic details are in spreadsheet ControlLogic
  in /usr/local/python/Observatory/Receivers/WBDC/doc.

  The class variable lists 'DC_names' and 'chl_names' will generate input port
  labels D1PA, D1PB, D2PA, D2PB in that order. With the class variable list
  'IF_names', the output port labels will be the above with either I1 or I2
  appended, in that order.
  """
  DC_names   = ["D1", "D2"]
  chl_names  = ["PA", "PB"]
  IF_names   = ["I1", "I2"]
  bands      = [22, 24]

  def __init__(self, name, inputs = None, output_names=None, active=True):
    """
    Initialize a WBDC1 object.

    @param upstream : device providing the signals
    @type  upstream : Device instance

    @param name : unique identifier
    @type  name : str

    @param active : True is the FrontEnd instance is functional
    @type  active : bool

    @param inputs : a dict with sources for different inputs
    @type  inputs : dict of str:str
    """
    #self.logger = logging.getLogger(__name__+".WBDC1")
    Receiver.__init__(self, name, active=active, inputs=inputs,
                      output_names=output_names)
    self.logger.debug("initializing %s", self)
    self.logger.info(" %s inputs: %s", self, str(self.inputs))
    self.band = self.set_band()
    self.data['bandwidth'] = 2e9 # Hz
    self.Xswitch = {}
    inkeys = inputs.keys()
    inkeys.sort()
    beams = []
    pols = []
    for key in inkeys:
      beams.append(inputs[key].signal['beam'])
      pols.append(inputs[key].signal['pol'])
    beams = unique(beams)
    beams.sort()
    pols = unique(pols)
    pols.sort()
    self.beams = beams
    self.pols  = pols
    for pol in pols:
      index = pols.index(pol)
      pol_ID = WBDC1.chl_names[index]
      pol_inputs = {}
      for key in inkeys:
        if inputs[key].signal['pol'] == pol:
          pol_inputs[key] = inputs[key]
      self.Xswitch[pol_ID] = Switch(self, "Switch "+pol_ID,
                                 inputs = pol_inputs,
                                 output_names = [WBDC1.DC_names[0]+pol_ID,
                                                 WBDC1.DC_names[1]+pol_ID],
                                 stype = "2x2")
    self.DC = {}
    dcs = WBDC1.DC_names
    dcs.sort()
    for dc in dcs:
      dc_inputs = {}
      for name in WBDC1.chl_names:
        dc_inputs[dc+name] = self.Xswitch[name].outputs[dc+name]
      self.DC[dc] = self.DownConv(self, dc, inputs = dc_inputs)
    self.logger.info(" %s outputs: %s", self, str(self.outputs))
    keys = self.outputs.keys()
    keys.sort()
    #for index in range(len(keys)):
    #  self.outputs[keys[index]].FITS['IF'] = index
    self._update_self()

  def set_band(self, band=22):
    assert contains(WBDC1.bands, band), \
      ("%s does not have band %d" % (self.name, band))
    self.data['frequency'] = band*1.e9
    self.band = band
    self._update_self()
    return self.band

  def get_band(self):
    return self.band

  def set_crossover(self, crossed=False):
    keys = self.Xswitch.keys()
    keys.sort()
    for sw in keys:
      self.Xswitch[sw].set_state(int(crossed))
      for name in self.outputs.keys():
        for prop in self.outputs[name].source.signal.keys():
          for destination in self.outputs[name].destinations:
            destination.signal[prop] = self.outputs[name].signal[prop]
    self._update_self()
    return self.get_crossover()

  def get_crossover(self):
    keys = self.Xswitch.keys()
    keys.sort()
    status = {}
    for key in keys:
      status[key] = self.Xswitch[key].get_state()
    return status

  def set_pol_mode(self,circular=False):
    for ch in self.DC.keys():
      self.DC[ch].set_pol_mode(circular)
    return self.get_pol_mode()

  def get_pol_mode(self):
    status = {}
    keys = self.DC.keys()
    keys.sort()
    for key in self.DC.keys():
      status[key] = self.DC[key].get_pol_mode()
    return status

  def set_IF_mode(self, SB_separated=False):
    for key in self.DC.keys():
      self.DC[key].set_IF_mode(SB_separated)
    if SB_separated:
      self.data['bandwidth'] = 1e9
    else:
      self.data['bandwidth'] = 2e9
    return self.get_IF_mode()

  def get_IF_mode(self):
    modes = {}
    keys = self.DC.keys()
    keys.sort()
    for key in self.DC.keys():
      modes[key] = self.DC[key].get_IF_mode()
    return modes

  def _update_self(self):
    self.logger.debug(" updating %s", self)
    keys = self.outputs.keys()
    keys.sort()
    for index in range(len(keys)):
      if self.outputs[keys[index]].signal:
        #self.outputs[keys[index]].signal.FITS['OBS-FREQ'] = self.band*1e9
        #self.outputs[keys[index]].signal.FITS['BANDWID'] = 2.e9 # Hz
        pass
    try:
      for key in self.DC.keys():
        self.DC[key]._update_self()
    except AttributeError:
      pass

  class DownConv(Receiver.DownConv):
    """
    Down-converter chain in a WBDC
    """
    def __init__(self, parent, name, inputs=None, output_names=None,
                 active=True):
      """
      """
      self.logger = logging.getLogger(parent.logger.name+".DownConv")
      self.name = name
      self.logger.debug(" initializing %s", str(self))
      Receiver.DownConv.__init__(self, parent, name, inputs=inputs,
                                output_names=output_names, active=active)
      self.logger.debug(" %s inputs: %s", str(self), str(self.inputs))
      self.parent = parent
      self.channel = {}
      self.set_pol_mode() # defaults to X,Y
      # The polarization into the DC channels depends on the state of the
      # polarization switch.  This means that it isn't necessarily the type
      # of polarization that came out of the switch, which is XY in the
      # Canberra K-band set-up.
      for chlname in WBDC1.chl_names:
        index = WBDC1.chl_names.index(chlname)
        inp = name+chlname
        pol = self.pols[index]
        self.logger.debug(" Processing pol section %s", inp)
        # the following collects the inputs with the same polarization
        pol_section_inputs = {}
        for key in self.inputs.keys():
          if self.inputs[key].signal['pol'] == pol:
            pol_section_inputs[inp] = self.inputs[key]
        # the following generates the output names
        output_names = []
        for IF in WBDC1.IF_names:
          ID = inp+IF
          output_names.append(ID)
        self.channel[inp] = self.Channel(self, inp, pol=pol,
                                            inputs=pol_section_inputs,
                                            output_names=output_names)
        for nm in output_names:
          parent.outputs[nm] = self.outputs[nm]
      self.logger.debug(" %s outputs: %s", str(self), str(self.outputs))

    def set_pol_mode(self,circular=False):
      self.circular = circular
      if self.circular:
        self.pols = ["L", "R"]
      else:
        self.pols = ["X", "Y"]
      self._update_self()

    def get_pol_mode(self):
      return self.circular

    def set_IF_mode(self, SB_separated=False):
      keys = self.channel.keys()
      keys.sort()
      for key in keys:
        self.channel[key].set_IF_mode(SB_separated)
      if SB_separated:
        self.data['bandwidth'] = 1e9
      else:
        self.data['bandwidth'] = 2e9

    def get_IF_mode(self):
      keys = self.channel.keys()
      keys.sort()
      modes = {}
      for key in keys:
        modes[key] = self.channel[key].get_IF_mode()
      return modes

    def _update_self(self):
      self.logger.debug(" Updating %s", self)
      for inp in self.inputs.keys():
        self.inputs[inp].signal = copy.copy(self.inputs[inp].source.signal)
      keys = self.channel.keys()
      keys.sort()
      for key in keys:
        index = keys.index(key)
        pol = self.pols[index]
        self.channel[key].pol = pol
        self.channel[key]._update_self()

    class Channel(Receiver.DownConv.Channel):
      """
      Channel in a down-converter section of a WBDC

      Public attributes::
        signal - signal out of the polarization section for this channel
      """
      def __init__(self, parent, name, inputs=None, output_names=None,
                   active=True, pol=None):
        self.logger = logging.getLogger(parent.logger.name+".Channel")
        self.parent = parent
        self.name = name
        self.pol = pol
        self.logger.debug(" Initializing %s", self)
        Receiver.DownConv.Channel.__init__(self, parent, name, inputs=inputs,
                                  output_names=output_names, active=active)
        self.logger.debug(" %s inputs: %s", self, str(inputs))
        source = inputs[inputs.keys()[0]]
        self.set_IF_mode()
        for name in output_names:
          IFname = name[4:7]
          index = WBDC1.IF_names.index(IFname)
          IFmode = self.IF_mode[index]
          self.outputs[name] = Port(self,name,
                                    source=source,
                                    signal=IF(source.signal, IFmode))
          self.parent.outputs[name] = self.outputs[name]
        self.logger.debug(" %s outputs: %s", self, str(self.outputs))
        self._update_self()

      def set_IF_mode(self, SB_separated=False):
        self.SB_separated = SB_separated
        if self.SB_separated:
          self.IF_mode = ["L","U"]
          self.data['bandwidth'] = 1e9
        else:
          self.IF_mode = ["I","Q"]
          self.data['bandwidth'] = 2e9
        self._update_self()
        return self.get_IF_mode()

      def get_IF_mode(self):
        return self.IF_mode

      def _update_self(self):
        self.logger.debug(" Updating %s inputs", self)
        for inp in self.inputs.keys():
          self.inputs[inp].signal = self.inputs[inp].source.signal
          self.inputs[inp].signal['pol'] = self.pol
          self.inputs[inp].signal.name = \
                                     self.inputs[inp].signal.name[:-1]+self.pol
        self.logger.debug(" Updating %s outputs", self)
        outkeys = self.outputs.keys()
        outkeys.sort()
        for key in outkeys:
          if self.outputs[key].signal:
            for prop in self.outputs[key].source.signal.keys():
              self.outputs[key].signal[prop] = \
                                          self.outputs[key].source.signal[prop]
            index = outkeys.index(key)
            self.outputs[key].signal.name = \
                       self.outputs[key].source.signal.name+self.IF_mode[index]
            self.outputs[key].signal['IF'] = self.IF_mode[index]
            #self.outputs[key].signal.FITS['if-mode'] = self.IF_mode[index]
            self.outputs[key].signal['pol'] = self.pol
            #self.outputs[key].signal.FITS['pol-mode'] = self.pol
            #self.outputs[key].signal.FITS['BEAM'] = self.outputs[key].signal['beam']
