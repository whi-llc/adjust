#!/usr/bin/env python3
'''
Copyright (c) 2020 WHI LLC

adjust: Adjust clock models for VLBI data correlation.
(see http://github.com/whi-llc/adjust).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import os, argparse
import numpy as np
import pandas as pd

np.seterr(divide='ignore')
path_to_script = os.path.dirname(os.path.abspath(__file__))
default_offset_file = os.path.join(
    path_to_script, 'data/sx_po.dat'
)

adjusted = False
ft_sub_8 = False
exclude = []
acc_zeros = False

args = argparse.ArgumentParser(
    prog='adjust', 
    description=('finds average offset to apply to correlator \'Used\' '
    'clocks after finding average offset, use -a to print adjusted offsets')
)
args.add_argument(
    'clocks', help='file with station clocks in correlator report format'
)
args.add_argument(
    '-a', '--adjust', action='store_true', 
    help='print adjusted peculiar offsets'
)
args.add_argument(
    '-p', '--peculiar-offsets', help='file with peculiar offsets'
)
args.add_argument(
    '-f', '--ft', action='store_true',
    help='sub 8 us from Ft fmout for 512 Mbps'
)
args.add_argument(
    '-x', '--exclude', nargs='+',
    help='list of two-letter stations to exclude'
)
args.add_argument(
    '-z', '--use-zeroes', action='store_true',
    help='accept zero values'
)
args.set_defaults(
    adjust=False,
    peculiar_offsets=default_offset_file,
    ft=False,
    exclude=[],
    use_zeroes=False
)
a = args.parse_args()

adjust = a.adjust
ft_sub_8 = a.ft
exclude = a.exclude
acc_zeros = a.use_zeroes

df=pd.read_csv(a.peculiar_offsets,sep='\s+',index_col=0,names=['Station','n','offset','rms'], comment='#')

#
indf=pd.read_csv(a.clocks,sep='\s+',index_col=0,names=['Station','gps','used'],usecols=[0,1,2], comment='#')
print('Input File ' + a.clocks)
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
    if index.lower() in [x.lower() for x in exclude]:
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
    if index.lower() in [x.lower() for x in exclude]:
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
    print('Using historical peculiar offsets from: ', a.peculiar_offsets)
    print('{:d}/{:d}'.format(len(use),len(diff.keys())), end=' ')
    print('   Diff_mean ','{:7.4f}'.format(avg), end=' ')
    print('   std ','{:7.4f}'.format(rms))

