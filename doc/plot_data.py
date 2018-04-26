"""
plot data from K-band front-end spreadsheet

The columns in each dataset are::
  0 frequency (Hz)
  1 S11 (dB)  - input voltage reflection coefficient
  2 S11 (deg)
  3 S12 (dB)  - reverse voltage gain
  4 S12 (deg)
  5 S21 (dB)  - forward voltage gain
  6 S21 (deg)
  7 S22 (dB)  - output voltage reflection coefficient
  8 S22 (deg)
The scattering (S) parameters for a two port network are::
  [R1]   [S11 S12][I1]
  [R2] = [S21 S22][I2]
where I is the incident power and R is the reflected power. The power-like
quantities, in dB, are::
  gain = 20 log  |S21|
               10|   |
  insertion loss = -gain
  input return loss = 20 log  |S11|
                            10|   |
  output return loss = -20 log  |S22|
                              10|   |
  reverse gain = 20 log  |S12|
                       10|   |
  reverse isolation = |reverse gain|
"""
import numpy
from pylab import *

colors = ['b', 'g', 'r', 'c']
pols = ['H1', 'H2', 'V1', 'V2']

data = numpy.genfromtxt("K-band - K2 data to Tom-1.csv", delimiter=',', skiprows=7)
Spar = {}
Spar[0] = data[:, 1:10] # LNA H1
Spar[1] = data[:,21:29] # LNA H2
Spar[2] = data[:,41:49] # LNA V1
Spar[3] = data[:,61:69] # LNA V2
Spar[4] = data[:,11:19] # LNA + Post Assembly, H1
Spar[5] = data[:,31:39] # LNA + Post Assembly, H2
Spar[6] = data[:,51:59] # LNA + Post Assembly, V1
Spar[7] = data[:,71:79] # LNA + Post Assembly, V2

figure(figsize=(16,6))
for index in range(4):
  subplot(1,2,1)
  plot(Spar[index][:,0]/1.e9, Spar[index][:,5],
            color=colors[index], label=pols[index])
  plot(Spar[index+4][:,0]/1.e9, Spar[index+4][:,5], color=colors[index])
  grid(True)
  xlabel("Frequency (GHz)")
  ylabel("$S_{21}$ (dB)")
  legend(loc="lower center")
  subplot(1,2,2)
  plot(Spar[index+4][:,0]/1e9,
       (Spar[index+4][:,5]-Spar[index][:,5]),
        color=colors[index])
  grid(True)
  xlabel("Frequency (GHz)")
  ylabel("Post Amp Gain (dB)")
show()
