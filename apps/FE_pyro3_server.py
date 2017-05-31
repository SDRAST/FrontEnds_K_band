import Pyro.core
# -*- coding: utf-8 -*-
"""
Test all functions of K-band receiver
"""

import Pyro
from Pyro.errors import NamingError
import Pyro.naming
from support.pyro import launch_server
from support.logs import init_logging

from Observatory import WBDC
from Observatory.FrontEnd import FE, sky, load, on, off
#from Observatory.WBDC import LJTickDAC
from Observatory.WBDC import Attenuator
from Observatory.minical import get_minical, process_minical
from Electronics.Interfaces.LabJack import searchForDevices
from Electronics.Interfaces.LabJack import connect_to_U3s
from Electronics.Interfaces.LabJack import get_LJ_ID
from Electronics.Interfaces.LabJack import U3name
from Electronics.Interfaces.LabJack import get_U3s_config
from Electronics.Interfaces.LabJack import report_IO_config, report_U3_config
from Electronics.Interfaces.LabJack import get_IO_states
from Electronics.Instruments.GPIB_devices import PM
from Electronics.Instruments.GPIB_devices import SG
#from Observatory.WBDC import set_band
from time import sleep, ctime, time
from datetime import datetime
try:
	from pylab import *
except:
	pass
import scipy
import numpy as NP
import u3
import re
import Math
from threading import Thread
import sys
import logging

module_logger = logging.getLogger(__name__)

class FE_server(Pyro.core.ObjBase, Thread):
        def __init__(self):
          Thread.__init__(self)
          Pyro.core.ObjBase.__init__(self)
          self.logger = logging.getLogger(module_logger.name+".FE_server")
          #Search for available devices
          available = searchForDevices()
          #Connect to LabJacks
          if len(available) > 0:
            self.lj = self.connect_to_Labjacks(available)
            self.atten = {}
          if self.lj.has_key(3):
            self.atten[5] = Attenuator(self.lj[3],6)
          else:
            self.logger.error("Noise diode attenuator not available")
          #Define Power meters
          self.pm = {}
          self.pm_name = {}
          try:
            self.pm[1] = PM('pm1','437B')
            self.pm_name[1] = "Feed 1 Pol 1"
          except:              
            self.logger.error("Could not initialize PM 1")
          try:
            self.pm[2] = PM('pm2','437B')
            self.pm_name[2] = "Feed 1 Pol 2"
          except:
            self.logger.error("Could not initialize PM 2")
          try:
            self.pm[3] = PM('pm3','437B')
            self.pm_name[3] = "Feed 2 Pol 1"
          except:
            self.logger.error("Could not initialize PM 3")
            pass
          try:
            self.pm[4] = PM('pm4','437B')
            self.pm_name[4] = "Feed 2 Pol 2"
          except:
            self.logger.error("Could not initialize PM 4")
        
        def set_WBDC(self, opt):
            """
            """
            self.logger.debug("set_WBDC: called with option %d", opt)
            if opt == 12:
              try:
                text = self.FElj.check_feeds()
              except Exception, details:
                self.logger.error("set_WBDC: failed because: %s", details)
                text = "False"
              self.logger.debug("set_WBDC: opt 12 returns %s", text)
              return (text)
            elif opt == 13:
              self.logger.debug("set_WBDC: set feed 1 to sky")
              self.FElj.set_feed(1,sky)
              return False
            elif opt == 14:
              self.logger.debug("set_WBDC: set feed 1 to load")
              self.FElj.set_feed(1,load)
              return True
            elif opt == 15:
              self.logger.debug("set_WBDC: set feed 2 to sky")
              self.FElj.set_feed(2,sky)
              return False
            elif opt == 16:
              self.logger.debug("set_WBDC: set feed 2 to load")
              self.FElj.set_feed(2,load)
              return True
            elif opt == 18:
              self.Yfactors, text = self.FElj.Y_factors(self.pm)
              text = ("Y-factors at " + ctime(time())+"\n") + (str(self.Yfactors)+"\n")
              return text
            elif opt == 20: # does not seem to work
              return "Feed 1 state changed at " + ctime(time())+"\n"
              self.FElj.LJ.pulse_bit(0)
            elif opt == 21: # does not seem to work
              return "Feed 2 state changed at " + ctime(time())+"\n"
              self.FElj.LJ.pulse_bit(1)
            elif opt == 22:
              if self.FElj.ND_state():
                text = "off"      
                return (text)        
                #conn.send(text)
              else:
                text = "on"      
                return (text)        
                #conn.send(text)
            elif opt == 23:
              self.FElj.set_ND(on)
              text = "Noise diode turned on at " + ctime(time())
              return (text)
            elif opt == 24:
              self.FElj.set_ND(off)
              text = "Noise diode turned off at " + ctime(time())
              return (text)
            elif opt == 25:
              self.FElj.preamp_bias(1,True)
              text = "Preamp 1 bias turned on at " + ctime(time())
              return (text)
            elif opt == 26:
              self.FElj.preamp_bias(1,False)
              text = "Preamp 1 bias turned off at " + ctime(time())
              return (text)
            elif opt == 27:
              self.FElj.preamp_bias(2,True)
              text = "Preamp 2 bias turned on at " + ctime(time())
              return (text)
            elif opt == 28:
              self.FElj.preamp_bias(2,False)
              text = "Preamp 2 bias turned off at " + ctime(time())
              return( text)
            elif opt == 29:
              self.logger.debug("set_WBDC: doing minical")
              all_gains, all_Tlinear, all_Tquadratic, all_Tnd, all_NonLin, all_x, all_readings = [], [], [], [], [], [], []
              self.logger.info("Minical data at %s", ctime(time()))
              #log.write("Minical data at " + ctime(time()) + "\n")
              cal_data = get_minical.minical_data(self.FElj, self.pm, diag=True)
              temps = self.FElj.get_temps()
              cal_data[1]['Tload'] = temps['load1']
              cal_data[2]['Tload'] = temps['load1']
              cal_data[3]['Tload'] = temps['load2']
              cal_data[4]['Tload'] = temps['load2']
              for key in cal_data.keys():
                for name in cal_data[key].keys():
                  text = "Ch."+ str(key) + " " + name + ": " + str(cal_data[key][name])
                  all_readings.append(text)
              Tlna = 25
              Tf = 1
              Fghz = 22
              TcorrNDcoupling = 0
              for key in cal_data.keys():
                [gains, Tlinear, Tquadratic, Tnd, NonLin] = \
                  process_minical(cal_data[key], Tlna, Tf, Fghz, TcorrNDcoupling)
                self.logger.info("set_WBDC: Feed %d",key)
                self.logger.info("set_WBDC: Gains: %s", str(gains))
                self.logger.info("set_WBDC: Linear Ts: %s", str(Tlinear))
                self.logger.info("set_WBDC: Corrected Ts: %s", str(Tquadratic))
                self.logger.info("set_WBDC: Noise diode T: %s", str(Tnd))
                self.logger.info("set_WBDC: Non-linearity: %s", str(NonLin))
                # report the results
                x = [cal_data[key]['sky'],
                     cal_data[key]['sky+ND'],
                     cal_data[key]['load'],
                     cal_data[key]['load+ND']]
                all_gains.append(gains)
                all_Tlinear.append(Tlinear)
                all_Tquadratic.append(Tquadratic)
                all_Tnd.append(Tnd)
                all_NonLin.append(NonLin)
                all_x.append(x)
              return all_gains, all_Tlinear, all_Tquadratic, all_Tnd, all_NonLin, all_x, all_readings

            elif opt == 31:
              if self.lj.has_key(3):
                text =  str(self.FElj.get_temps())
                self.logger.info("Front end temperatures at %s\n%s",
                                 ctime(time()), text)
                return(text)
              else:
                self.logger.error("set_WBDC: Cannot read front end temperatures without front end control")
            
            elif opt == 32:
              self.logger.info("Load/LN2 calibration at %s", ctime(time()))
              temps = self.FElj.get_temps()
              Tln2 = 77
              self.logger.info("Assumed LN2 temperatures: %"+str(Tln2)+"\n")
              Trec = {}
              for key in self.Yfactors.keys():
                if key < 3:
                  Tload = temps['load1']
                else:
                  Tload = temps['load2']
                R = pow(10., self.Yfactors[key]/10.)
                Trec[key] = (Tload - R*Tln2)/(R - 1)
              text = "Trec: "+str(Trec)
              self.logger.debug("set_WBDC: %s", text)
              return text
            elif opt == 33:
              self.FElj.LJ.getFeedback(u3.BitStateWrite(IONumber = 5, State = 0))
            elif opt == 34:
              self.FElj.LJ.getFeedback(u3.BitStateWrite(IONumber = 5, State = 1))
            elif opt == 35:
              self.FElj.LJ.getFeedback(self.FElj.LJ.getFeedback(u3.DAC0_16(255*256)))
            elif opt == 36:
              self.FElj.LJ.getFeedback(self.FElj.LJ.getFeedback(u3.DAC0_16(0)))
            elif opt == 391:
              self.pm[1].set_mode("W")
              return "PM1 mode set to W"

            elif opt == 392:
              self.pm[2].set_mode("W")
              return "PM2 mode set to W"

            elif opt == 393:
              self.pm[3].set_mode("W")
              return "PM1 mode set to W"

            elif opt == 394:
              self.pm[4].set_mode("W")
              return "PM4 mode set to W"

            elif opt == 401:
              self.pm[1].set_mode("dBm")
              return "PM1 mode set to dBm"

            elif opt == 402:
              self.pm[2].set_mode("dBm")
              return "PM2 mode set to dBm"

            elif opt == 403:
              self.pm[3].set_mode("dBm")
              return "PM3 mode set to dBm"

            elif opt == 404:
              self.pm[4].set_mode("dBm")
              return "PM4 mode set to dBm"
            else:
              self.logger.error("set_WBDC: option %d not implemented", opt)
              
        def siggen_controls(self, opt, freq, amp):
            try:
              self.sg = SG('SGen_8673g')
            except:
              self.logger.error("siggen_controls: Could not initialize Signal Generator")
            #54 - Reset Signal Generator
            if opt == 1:
              self.sg.init()
              return "SigGen initialized"
        
            #55 - Read Signal Generator Status
            elif opt == 2:
              self.logger.warning("siggen_controls: option 2 is not fully implemented yet.. ")
              text = str(self.sg.get_status())
              return text
              #sleep(5)
            
            #56 - Turn Signal Generator Off
            elif opt == 3:
              try:
                self.sg.power_off()
                return "Completed"
              except:
                return "Rejected"
        
            #57 - Turn Signal Generator On
            elif opt == 4:
              try:
                self.sg.power_on()
                self.sg.set_freq(freq)
                self.sg.set_ampl(amp)
                return "Completed"
              except:
                return "Rejected"
 
        def connect_to_Labjacks(self, available):
#          global WBDCdigLJ, WBDCattLJ, FElj
          for LJ in available.keys():
            self.logger.debug("connect_to_Labjacks: Serial:%s, local ID: %s",
                              LJ,available[LJ]['localId'])
          self.lj = connect_to_U3s()
          self.logger.info("connect_to_Labjacks: %d LabJacks connected", len(self.lj))
#          WBDC.init_WBDC_U3s(self.lj)
          for LJ in self.lj.keys():
            self.logger.debug("connect_to_Labjacks: Checking name for LabJack %s",LJ)
            self.lj[LJ].name = U3name[str(self.lj[LJ].serial)]
            self.logger.debug("connect_to_labjack: %s %s",
                              self.lj[LJ].localID, self.lj[LJ].name)
          if self.lj.has_key(3):
            self.FElj = FE(self.lj[3])
          else:
            self.logger.warning("connect_to_Labjacks: Front end LabJack is not available")
          return self.lj
        
        def init_pms(self):
          for key in self.pm.keys():
            self.pm.init()
          
        def read_pms(self):
          sys.stdout.flush()
          self.pm_readings = []
          for key in self.pm.keys():
            #Get readings every 1 sec.
            try:
              readings = NP.mean(NP.array(self.pm[key].get_readings(1)[0]))
            except Exception, details:
              self.logger.error("read_pms: failed: %s", details)
            try:
              self.pm_readings.append( (key, ctime(time()), readings) )
            except Exception, details:
              self.logger.error("read_pms: appending failed: %s", details)
          #print self.pm_readings
          return self.pm_readings
        
        def calculate_Tsys(self):
          """
          1. read ND temp in K
          2. Tsys = Tbg + Tsky + Tspill + Tloss + Tcal + Trx , 
          """
          pass
        
        def read_temp(self):
          """
          Read rx temperatures
          """
          temp_dict =  self.FElj.get_temps()
          return temp_dict
                  
        def running(self):
          """
     Report if the manager is running.  A return value of False should
     not be possible.
          """
          if self.run:
            return True
          else:
           return False

        def halt(self):
          """
     Command to halt the manager
          """
          self.logger.info("halt: Halting")
          self.run = False
          
def main():
   from socket import gethostname 
   __name__ = 'FE_server-'+gethostname()
   
   logging.basicConfig(level=logging.DEBUG)
   mylogger = logging.getLogger()
   mylogger = init_logging(mylogger,
                           loglevel=logging.INFO, 
                           consolevel=logging.DEBUG,
                           logname="/usr/local/logs/"+__name__+".log")
   
   locator = Pyro.naming.NameServerLocator()
   try:
     ns = locator.getNS(host='crux.cdscc.fltops.jpl.nasa.gov')
   except NamingError,details:
     mylogger.error(
       """Pyro nameserver task not found.
          Is the terminal at least 85 chars wide?
       If pyro-ns is not running. Do 'pyro-ns &'""")
     raise RuntimeError("Pyro naming error")
   m = FE_server()
   mylogger.debug(" FE_server instantiated")
   launch_server("crux", __name__, m)
   try:
     ns = locator.getNS(host='crux.cdscc.jpl.nasa.gov')
   except NamingError:
     mylogger.error(
       """Pyro nameserver task notfound. Is the terminal at least 85
chars wide?
       If pyro-ns is not running. Do 'pyro-ns &'""")
     raise RuntimeError("No Pyro nameserver")
   try:
     ns.unregister(__name__)
   except NamingError:
     mylogger.debug("%s was already unregistered", __name__)
   mylogger.info("%s finished", __name__)
   
if __name__=="__main__":
    main()

