#!/usr/bin/env python3
#
# Copyright (c) 2020 WHI LLC
#
# adjust: Adjust clock models for VLBI data correlation.
# (see http://github.com/whi-llc/adjust).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import os
import sys
import getopt
import re
import numpy as np
import time
import math
import warnings
import io
import pandas as pd

np.seterr(divide='ignore')

if len(sys.argv)==1:
    sys.exit('try '+os.path.splitext(os.path.basename(__file__))[0]+' -h')

try:
    options, remainder = getopt.getopt(
    sys.argv[1:],
    'abfhvx:z`')

except getopt.GetoptError as err:
    print('ERROR:', err)
    sys.exit(1)

if len(remainder) > 1:
    print('ERROR: only one file argument allowed.')
    sys.exit(1)

adjusted = False
broadband = False
ft_sub_8 = False
exclude = []
acc_zeros = False
#
#start
#peculiar_version='v7_2018/04/08'
#updated Ny with data r4836-r4845
peculiar_version='v8.0_weh_2018/06/24'
#
s='''
Bd  4   217.277 0.006
Ft  8   0.238   0.015
Ho  3   0.377   0.057
Ht  13  2.943   0.021
Is  9   0.507   0.012
Ke  10  2.006   0.024
Kk  8   0.459   0.012
Ma  6   0.638   0.015
Ny  21  2.308   0.010
On  5   1.866   0.024
Sh  7   9.986   0.013
Wn  6   2.330   0.009
Ww  5   1.974   0.026
Wz  12  2.630   0.000
Yg  13  2.278   0.021
Zc  3   217.047 0.012
'''
b_peculiar_version='b1.0_bec_2020/06/11'
b='''
Wf  35  1.169  0.030
Gs  35  0.602  0.005
K2  34  0.414  0.046
Mg   9  0.174  0.012
Is   7  1.255  0.011
Ws  35  1.717  0.046
Yj  34 -0.038  0.098
Oe  37  6.228  0.047
Ow  23  6.188  0.038
'''
for opt,arg in options:
    if opt == '-h':
        print('Usage: '+sys.argv[0]+' -afhvx: file')
        print('  finds average offset to apply to correlator \'Used\' clocks')
        print('  after finding average offset, use -a to print adjusted offsets')
        print('     file:')
        print('         one line per station (three fields minimum, blank delimited):')
        print('               two-letter station, case sensitive, e.g. Ht')
        print('               fmout-gps')
        print('               Used')
        print('               Additional columns ignored.')
        print('     output, unless -a specified:')
        print('         one line per station:')
        print('               station')
        print('               peculiar offset')
        print('               difference from historical')
        print('               "x" excluded or " " included')
        print('               residual to fit for Diff_mean')
        print('               Normalized residual for std')
        print('               Normalized residual for historical RMS')
        print('               station\'s historical offset')
        print('               station\'s historical RMS')
        print('               number of data points in history')
        print('        two lines: explanation')
        print('        one line: peculiar offsets version')
        print('        one line: summary')
        print('               number of stations included')
        print('               total number of stations')
        print('               average offset (Diff_mean)')
        print('               std')
        print('     output, with -a specified:')
        print('         one line per station:')
        print('               station')
        print('               Use flag')
        print('                 i=included')
        print('                 x=excluded')
        print('                 n=new')
        print('               Adjusted peculiar offset')
        print('               File name (all the same)')
        print(' ')
        print('Options:')
        print(' -a   print adjusted peculiar offsets')
        print(' -b   use broadband peculiar offsets')
        print(' -f   sub 8 us from Ft fmout for 512 Mbps')
        print(' -h   this text')
        print(' -v   print version number')
        print(' -x   stations to exclude')
        print('        list of two letter codes, colon separated, case sensitive')
        print(' -z   accept zero values')
        sys.exit(0)
    elif opt == '-a':
        adjusted = True
    elif opt == '-b':
        broadband = True
    elif opt == '-f':
        ft_sub_8 = True
    elif opt == '-v':
        sys.exit('[Version 8.2]')
    elif opt == '-x':
        exclude=arg.split(':')
    elif opt == '-z':
        acc_zeros = True

if broadband:
    df=pd.read_csv(io.StringIO(b),sep='\s+',index_col=0,names=['Station','n','offset','rms'])
else:
    df=pd.read_csv(io.StringIO(s),sep='\s+',index_col=0,names=['Station','n','offset','rms'])
#
indf=pd.read_csv(remainder[0],sep='\s+',index_col=0,names=['Station','gps','used'],usecols=[0,1,2])
print('Input File '+remainder[0]) 
#
diff={}
use=np.array([])
list=list(indf.index)
for index in list:
    try:
        gps=float(indf['gps'][index])
        if index == 'Ft' and ft_sub_8:
#            indf['gps'][index]=float(indf['gps'][index])-8
            gps=gps-8
            print(' -8 us added to fmout value for Ft')
#
        try:
            used=float(indf['used'][index])
        except:
            print('{:<7}'.format(index)," Can't decode Used")
            continue
    except:
        print('{:<7}'.format(index)," Can't decode fmout")
        continue
    if used == 0 and not acc_zeros:
        print('{:<7}'.format(index)," Used value is zero")
        continue
    if gps == 0 and not acc_zeros:
        print('{:<7}'.format(index)," fmout value is zero")
        continue
    pec=used-gps
    try:
        diff[index]=df['offset'][index]-pec
    except KeyError:
        print('{:<7}'.format(index), " No historical peculiar offset")
        continue
    if index in exclude:
        continue
    else:
        use=np.append(use,diff[index])
avg=np.mean(use)
rms=np.std(use)
if not adjusted:
    print('Station Peculiar   Diff  X Residual     NR     NRH  Historical     RMS  count')
else:
    print('Station X fmout Adjusted Input')
#
for index in list:
    try:
        gps=float(indf['gps'][index])
        if index == 'Ft' and ft_sub_8:
            gps=gps-8
        try:
            used=float(indf['used'][index])
        except:
            continue
    except:
        continue
    if used == 0 and not acc_zeros:
        continue
    if gps == 0 and not acc_zeros:
        continue
    pec=used-gps
# 
    if index in exclude:
        no='x'
    elif adjusted:
        no='i'
    else:
        no=' '
    try:
        df['offset'][index]
    except KeyError:
        if not adjusted:
            continue
        else:
            no='n'
#
    print('{:<2}'.format(index), end=' ')
    if not adjusted:
        print('{:13.4f}'.format(pec), end=' ')
        print('{:7.4f}'.format(diff[index]), end=' ')
    print('{:.1}'.format(no), end=' ')
    if not adjusted:
        print('{:7.4f}'.format(diff[index]-avg), end=' ')
        if rms < 0.000095:
            print('{:7.1f}'.format(np.nan), end=' ')
        else:
            print('{:7.1f}'.format((diff[index]-avg)/rms), end=' ')
        print('{:7.1f}'.format((diff[index]-avg)/df['rms'][index]), end=' ')
        print('{:10.4f}'.format(df['offset'][index]), end=' ')
        print('{:9.4f}'.format(df['rms'][index]), end=' ')
        print('{:5.0f}'.format(df['n'][index]))
    else:
        if len(use) != 0:
            print('{:9.4f}'.format(gps), end=' ')
            print('{:8.4f}'.format(pec+avg), end=' ')
        else:
            print('{:9.4f}'.format(gps), end=' ')
            print('{:8.4f}'.format(pec), end=' ')
        print('{:<12}'.format(remainder[0]))
if not adjusted:
    print('Diff: amount to add to Used to agree with historical peculiar offsets')
    print('X: deleted flag, Residual: Diff-Diff_mean, NR=Residual/std, NRH=Residual/RMS')
    if broadband:
        print('Using broadband historical peculiar offsets:',b_peculiar_version)
    else:
        print('Using S/X historical peculiar offsets:',peculiar_version)
    print('{:d}/{:d}'.format(len(use),len(diff.keys())), end=' ')
    print('   Diff_mean ','{:7.4f}'.format(avg), end=' ')
    print('   std ','{:7.4f}'.format(rms))

