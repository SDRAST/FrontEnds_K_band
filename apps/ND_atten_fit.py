# -*- coding: utf-8 -*-
"""
These data are from the calibration log for Fri Apr  8 16:03:55 2011

Add ctrl_voltage as a method to ND.  ND should probably be raised to a class
"""
import numpy as NP
from pylab import *
import scipy

def ctrl_voltage(ND):
  coefs = array([  3.85013993e-18,  -6.61616152e-15,   4.62228606e-12,
        -1.68733555e-09,   3.43138077e-07,  -3.82875899e-05,
         2.20822016e-03,  -8.38473034e-02,   1.52678586e+00])
  return scipy.polyval(coefs,ND)

data = NP.array([
[-6.00,  -28.716],
[-5.75,  -28.732],
[-5.50,  -28.757],
[-5.25,  -28.797],
[-5.00,  -28.851],
[-4.75,  -28.928],
[-4.50,  -29.035],
[-4.25,  -29.179],
[-4.00,  -29.355],
[-3.75,  -29.555],
[-3.50,  -29.775],
[-3.25,  -29.992],
[-3.00,  -30.189],
[-2.75,  -30.378],
[-2.50,  -30.548],
[-2.25,  -30.691],
[-2.00,  -30.822],
[-1.75,  -30.926],
[-1.50,  -31.028],
[-1.25,  -31.109],
[-1.00,  -31.206],
[-0.75,  -31.296],
[-0.50,  -31.388],
[-0.25,  -31.498],
[ 0.00,  -31.612],
[ 0.25,  -31.747],
[ 0.50,  -31.880],
[ 0.75,  -31.995],
[ 1.00,  -32.078],
[ 1.25,  -32.116],
[ 1.50,  -32.136],
[ 1.75,  -32.144]])

ctrlV = data[:,0]
pwr_dB = data[:,1]
pwr_W = pow(10.,pwr_dB/10)
min_pwr = pwr_W.min()
max_pwr = pwr_W.max()
gain = 320/min_pwr # noise diode essentially off
TsysMax = gain*max_pwr # assuming the system was linear, which it was
print("Tsys with full ND =",TsysMax)
NDmax = TsysMax-320
print("Tnd(max) =",NDmax)
ND =gain*pwr_W - 320

plot(ND,ctrlV)
ylabel("Control Voltage (V)")
xlabel("Noise Diode (K)")
grid()

coefs = scipy.polyfit(ND,ctrlV, 8)
print(coefs)

vctrl_voltage = NP.vectorize(ctrl_voltage)
x = arange(0,350,10)
plot(x,vctrl_voltage(x),'ro')

show()



