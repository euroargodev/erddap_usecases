#!/bin/env python
# -*coding: UTF-8 -*-
#
# HELP
#
# Created by gmaze on 11/03/2020
__author__ = 'gmaze@ifremer.fr'

import os
import sys
import numpy as np
import xarray as xr

@xr.register_dataset_accessor('argo')
class ArgoAccessor:
    """

        Class registered under scope ``argo`` to access :class:`xarray.Dataset` objects.

     """
    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        self._added = list() # Will record all new variables added by argo
        self._dims = list(xarray_obj.dims.keys()) # Store the initial list of dimensions


    def point2profile(self):
        """ Transform a collection of points into a collection of profiles

        """
        this = self._obj
        # Find the maximum nb of points for a single profile:
        this['counter'] = xr.DataArray(np.ones_like(this['index']), dims='index', coords={'index': this['index']})
        this['id'] = xr.DataArray(1e4 * this['PLATFORM_NUMBER'] + this['CYCLE_NUMBER'],
                                  dims='index', coords={'index': this['index']}).astype(int)
        that = this.groupby('id').sum()['counter']
        N_LEVELS = int(that.max().values)
        N_PROF = len(np.unique(this['id']))
        assert N_PROF * N_LEVELS >= len(this['index'])

        # Create a new dataset:
        PRF = []
        CYC = []
        for i in np.unique(this['id']):
            wmo = int(i / 1e4)
            cyc = -int(1e4 * wmo - i)
            PRF.append(wmo)
            CYC.append(cyc)
        PRF = np.array(PRF)
        CYC = np.array(CYC)
        empty_2var_array = xr.DataArray(np.zeros((N_PROF, N_LEVELS)) * np.NaN,
                                        dims=['N_PROF', 'N_LEVELS'],
                                        coords={'N_PROF': np.arange(0, N_PROF), 'N_LEVELS': np.arange(0, N_LEVELS)})
        new = empty_2var_array.rename('TEMP').to_dataset()
        plist = ['pres', 'temp', 'psal']
        pext = ['', '_qc', '_adjusted', '_adjusted_qc']
        for p in plist:
            for e in pext:
                vname = p.upper() + e.upper()
                if vname in this:
                    new[vname] = empty_2var_array
        new['PLATFORM_NUMBER'] = xr.DataArray(PRF, dims=['N_PROF'], coords={'N_PROF': new['N_PROF']})
        new['CYCLE_NUMBER'] = xr.DataArray(CYC, dims=['N_PROF'], coords={'N_PROF': new['N_PROF']})

        # Fill it with appropriate measurements:
        for i_prof in new['N_PROF']:
            wmo = int(new['PLATFORM_NUMBER'].sel(N_PROF=i_prof).values)
            cyc = int(new['CYCLE_NUMBER'].sel(N_PROF=i_prof).values)
            that = this.where(this['PLATFORM_NUMBER'] == wmo, drop=1).where(this['CYCLE_NUMBER'] == cyc, drop=1)
            N = len(that['index'])
            for p in plist:
                for e in pext:
                    vname = p.upper() + e.upper()
                    if vname in that:
                        new[vname].sel(N_PROF=i_prof).loc[dict(N_LEVELS=range(0, N))] = that[vname].values

        new = new[np.sort(new.data_vars)]
        return new