# -*- coding: utf-8 -*-
import time
import threading
import sys
import logging
import u3

import numpy as np

from support.pyro import Pyro4Server

# from Observatory.FrontEnd import FE, sky, load, on, off
from Observatory import FrontEnd
from Observatory.WBDC import Attenuator
import Electronics.Interfaces.LabJack as LabJack

class FEServer(Pyro4Server):
    """
    Server that controls the Front End.
    """
    def __init__(self, **kwargs):

        logger = logging.getLogger(__name__+".FEServer")
        Pyro4Server.__init__(self, "FE", logger=logger, **kwargs)
        self.lj = None # labjacks
        self.frontend = None # Front End
        self.atten = {}
        # Find available devices
        available = LabJack.searchForDevices()
        # Connect to LabJacks
        if len(available) > 0:
            self.lj = self.connect_to_Labjacks(available)
            self.atten = {}
            if 3 in self.lj:
                try:
                    self.frontend = FrontEnd.FE(self.lj[3])
                except:
                    self.serverlog.error("Couldn't connect to Front end", exc_info=True)
                try:
                    self.atten[5] = Attenuator(self.lj[3], 6)
                except:
                    self.serverlog.error("Couldn't connect to Noise Diode", exc_info=True)
            else:
                self.serverlog.error("Front end and noise diode attenuator not available")

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
            self.serverlog.debug("connect_to_Labjacks: Serial:{}, local ID: {}".format(LJ, available[LJ]['localId']))
        self.lj = LabJack.connect_to_U3s()
        self.serverlog.info("connect_to_Labjacks: {} LabJacks connected".format(len(self.lj)))
        #          WBDC.init_WBDC_U3s(self.lj)
        for LJ in self.lj.keys():
            self.serverlog.debug("connect_to_Labjacks: Checking name for LabJack {}".format(LJ))
            self.lj[LJ].name = LabJack.U3name[str(self.lj[LJ].serial)]
            self.serverlog.debug("connect_to_labjack: {} {}".format(self.lj[LJ].localID, self.lj[LJ].name))
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
        self.serverlog.debug("Setting ND state to {}".format(state))
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
        self.serverlog.debug("Setting preamp bias for feed {} to {}".format(feed, state))
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

if __name__ == "__main__":
    fe_server = FEServer()
    try:
        fe_server.launch_server(remote_server_name='crux.cdscc.fltops.jpl.nasa.gov', ns_port=50000)
    except:
        fe_server.launch_server(remote_server_name='crux.cdscc.jpl.nasa.gov', ns_port=50000)

