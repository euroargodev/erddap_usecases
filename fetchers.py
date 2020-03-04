#!/bin/env python
# -*coding: UTF-8 -*-
"""

High level helper methods to load Argo data from the Ifremer erddap server.

Usage (v0.1):

    from fetchers import ArgoDataFetcher

    argo_loader = ArgoDataFetcher()
or
    argo_loader = ArgoDataFetcher(cachedir='tmp', cache=True)
or
    argo_loader = ArgoDataFetcher(ds='ref')

    argo_loader.profile(6902746, 34).to_xarray()
    argo_loader.profile(6902746, np.arange(12,45)).to_xarray()
    argo_loader.profile(6902746, [1,12]).to_xarray()

    argo_loader.float(6902746).to_xarray()
    argo_loader.float([6902746, 6902747, 6902757, 6902766]).to_xarray()
    argo_loader.float([6902746, 6902747, 6902757, 6902766], CYC=1).to_xarray()

    argo_loader.region([-85,-45,10.,20.,0,1000.]).to_xarray()
    argo_loader.region([-85,-45,10.,20.,0,1000.,'2012-01','2014-12']).to_xarray()

Usage (v0.0):

    from fetchers import ArgoDataFetcher

    argo_loader = ArgoDataFetcher(cachedir='tmp')

    argo_loader.profile(6902746, 34).to_xarray()
    argo_loader.profile(6902746, np.arange(12,45)).to_xarray()
    argo_loader.profile(6902746, [1,12]).to_xarray()

    argo_loader.float(6902746).to_xarray()
    argo_loader.float([6902746, 6902747, 6902757, 6902766]).to_xarray()
    argo_loader.float([6902746, 6902747, 6902757, 6902766], CYC=1).to_xarray()

    argo_loader.region([-85,-45,10.,20.,0,1000.]).to_xarray()
    argo_loader.region([-85,-45,10.,20.,0,1000.,'2012-01','2014-12']).to_xarray()

Created by gmaze on 20/12/2019
"""
__author__ = 'gmaze@ifremer.fr'

import os
import sys
import glob
import pandas as pd
import xarray as xr
import numpy as np
from erddapy import ERDDAP
from erddapy.utilities import urlopen
from abc import ABC, abstractmethod
from pathlib import Path
import getpass

class ArgoDataFetcher(object):
    """ Fetch and process Argo data.

        Can return data selected from:
        - one or more float(s), defined by WMOs
        - one or more profile(s), defined for one WMO and one or more CYCLE NUMBER
        - a space/time rectangular domain, defined by lat/lon/pres/time range

        Can return data from the regular Argo dataset ('phy': temperature, salinity) and the Argo referenced
        dataset used in DMQC ('ref': temperature, salinity).

        This is the main API facade.
        Specify here all options to fetchers

    """

    def __init__(self, mode='standard', backend='erddap', ds='phy', **fetcher_kwargs):
        # Init sub-methods:
        self.fetcher = None
        self.fetcher_options = {**{'ds':ds}, **fetcher_kwargs}
        self.postproccessor = self.__empty_processor

        # Facade options:
        self.mode = mode # User mode determining the level of post-processing required
        self.dataset_id = ds # Database to use
        self.backend = backend # fetchers to use
        if self.backend != 'erddap':
            raise ValueError("Invalid backend, only 'erddap' available at this point")

    def __repr__(self):
        if self.fetcher:
            summary = [self.fetcher.__repr__()]
            summary.append("User mode: %s" % self.mode)
        else:
            summary = ["<datafetcher 'Not initialised'>"]
            summary.append("User mode: %s" % self.mode)
        return "\n".join(summary)


    def __empty_processor(self, xds):
        """ Do nothing to a dataset """
        return xds

    def float(self, wmo):
        """ Load data from a float, given one or more WMOs """
        self.fetcher = ErddapArgoDataFetcher_wmo(WMO=wmo, **self.fetcher_options)

        if self.dataset_id == 'phy' and self.mode == 'standard':
            def postprocessing(xds):
                xds = self.fetcher.filter_data_mode(xds)
                xds = self.fetcher.filter_qc(xds)
                return xds
            self.postproccessor = postprocessing
        return self

    def profile(self, wmo, cyc):
        """ Load data from a profile, given one ormore WMOs and CYCLE_NUMBER """
        self.fetcher = ErddapArgoDataFetcher_wmo(WMO=wmo, CYC=cyc, **self.fetcher_options)

        if self.dataset_id == 'phy' and self.mode == 'standard':
            def postprocessing(xds):
                xds = self.fetcher.filter_data_mode(xds)
                xds = self.fetcher.filter_qc(xds)
                return xds
            self.postproccessor = postprocessing

        return self

    def region(self, box):
        """ Load data for a rectangular region, given latitude, longitude, pressure and possibly time bounds """
        self.fetcher = ErddapArgoDataFetcher_box(box=box, **self.fetcher_options)

        if self.dataset_id == 'phy' and self.mode == 'standard':
            def postprocessing(xds):
                xds = self.fetcher.filter_data_mode(xds)
                xds = self.fetcher.filter_qc(xds)
                return xds
            self.postproccessor = postprocessing

        return self

    def deployments(self, box):
        """ Retrieve deployment locations in a specific space/time region """
        self.fetcher = ErddapArgoDataFetcher_box_deployments(box=box, **self.fetcher_options)

        if self.dataset_id == 'phy' and self.mode == 'standard':
            def postprocessing(xds):
                xds = self.fetcher.filter_data_mode(xds)
                xds = self.fetcher.filter_qc(xds)
                return xds
            self.postproccessor = postprocessing

        return self

        pass

    def to_xarray(self, **kwargs):
        """ Fetch and post-process data, return xarray.DataSet """
        xds = self.fetcher.to_xarray(**kwargs)
        xds = self.postproccessor(xds)
        return xds

class ErddapArgoDataFetcher(ABC):
    """ Manage access to Argo data through Ifremer ERDDAP

        ERDDAP transaction are managed with the erddapy library

        __author__: gmaze@ifremer.fr
    """

    ###
    # Methods to be customised for a specific request
    ###
    @abstractmethod
    def init(self):
        """ Initialisation for a specific fetcher """
        pass

    @abstractmethod
    def define_constraints(self):
        """ Define erddapy constraints """
        pass

    @abstractmethod
    def cname(self):
        """ Return a unique string defining the request """
        pass

    ###
    # Methods that must not changed
    ###
    def __init__(self, ds='phy', cache=False, cachedir=None, **kwargs):
        """ Instantiate an ERDDAP Argo data loader

            Parameters
            ----------
            db: 'phy' or 'ref'
            cache : False
            cachedir : None
        """
        self.cache = cache
        self.cachedir = cachedir or os.environ.get('CACHE_ARGO')
        if self.cache:
            Path(self.cachedir).mkdir(parents=True, exist_ok=True)

        self.definition = 'Ifremer erddap Argo data fetcher'
        self.dataset_id = ds
        self.init(**kwargs)
        self._init_erddapy()

    def __repr__(self):
        if hasattr(self, '_definition'):
            summary = [ "<datafetcher '%s'>" % self.definition ]
        else:
            summary = [ "<datafetcher '%s'>" % 'Ifremer erddap Argo data fetcher' ]
        summary.append( "Domain: %s" % self.cname(cache=0) )
        return '\n'.join(summary)

    def _format(self, x, typ):
        """ string formating helper """
        if typ=='lon':
            if x < 0:
                x = 360. + x
            return ("%05d") % (x * 100.)
        if typ=='lat':
            return ("%05d") % (x * 100.)
        if typ=='prs':
            return ("%05d") % (np.abs(x)*10.)
        if typ=='tim':
            return pd.to_datetime(x).strftime('%Y%m%d')
        return str(x)

    def _add_history(self, this, txt):
        if 'history' in this.attrs:
            this.attrs['history'] += "; %s" % txt
        else:
            this.attrs['history'] = txt
        return this

    def _cast_types(self, this):
        """ Make sure variables are of the appropriate types

            This is hard coded, but should be retrieved from an API somewhere
        """
        def cast_this(da, type):
            da.values = da.values.astype(type)
            return da

        for v in this.data_vars:
            if "QC" in v:
                try:
                    if this[v].dtype == 'O': # object
                        this[v] = cast_this(this[v], str)
                    if this[v].dtype == '<U1': # string
                        ii = this[v] == ' ' # This should not happen, but still ! That's real world
                        this[v].loc[dict(index=ii)] = '0'
                    this[v] = cast_this(this[v], int)
                except:
                    print("%s type %s cannot be casted correctly" % (v, this[v].dtype) )
                    raise

            if v == 'PLATFORM_NUMBER' and this['PLATFORM_NUMBER'].dtype == 'float64':  # Object
                this['PLATFORM_NUMBER'] = cast_this(this['PLATFORM_NUMBER'], int)

            if v == 'DATA_MODE' and this['DATA_MODE'].dtype == 'O':  # Object
                this['DATA_MODE'] = cast_this(this['DATA_MODE'], str)
            if v == 'DIRECTION' and this['DIRECTION'].dtype == 'O':  # Object
                this['DIRECTION'] = cast_this(this['DIRECTION'], str)
        return this

    def _add_attributes(self, this):
        """ Add variables attributes not return by erddap requests

            This is hard coded, but should be retrieved from an API somewhere
        """
        for v in this.data_vars:
            if 'TEMP' in v and '_QC' not in v:
                this[v].attrs = {'long_name': 'SEA TEMPERATURE IN SITU ITS-90 SCALE',
                              'units': 'degree_Celsius',
                              'valid_min': -2.,
                              'valid_max': 40.,
                              'resolution': 0.001}
                if 'ERROR' in v:
                    this[v].attrs['long_name'] = 'ERROR IN %s' % this[v].attrs['long_name']

        for v in this.data_vars:
            if 'PSAL' in v and '_QC' not in v:
                this[v].attrs = {'long_name': 'PRACTICAL SALINITY',
                              'units': 'psu',
                              'valid_min': 0.,
                              'valid_max': 43.,
                              'resolution': 0.001}
                if 'ERROR' in v:
                    this[v].attrs['long_name'] = 'ERROR IN %s' % this[v].attrs['long_name']

        for v in this.data_vars:
            if 'PRES' in v and '_QC' not in v:
                this[v].attrs = {'long_name': 'Sea Pressure',
                              'units': 'decibar',
                              'valid_min': 0.,
                              'valid_max': 12000.,
                              'resolution': 0.1}
                if 'ERROR' in v:
                    this[v].attrs['long_name'] = 'ERROR IN %s' % this[v].attrs['long_name']

        for v in this.data_vars:
            if '_QC' in v:
                attrs = {'long_name': "Global quality flag of %s profile" % v,
                         'convention': "Argo reference table 2a"};
                this[v].attrs = attrs

        if 'CYCLE_NUMBER' in this.data_vars:
            this['CYCLE_NUMBER'].attrs = {'long_name': 'Float cycle number',
                             'convention': '0..N, 0 : launch cycle (if exists), 1 : first complete cycle'}

        if 'DATA_MODE' in this.data_vars:
            this['DATA_MODE'].attrs = {'long_name': 'Delayed mode or real time data',
                             'convention': 'R : real time; D : delayed mode; A : real time with adjustment'}

        if 'DIRECTION' in this.data_vars:
            this['DIRECTION'].attrs = {'long_name': 'Direction of the station profiles',
                             'convention': 'A: ascending profiles, D: descending profiles'}

        if 'PLATFORM_NUMBER' in this.data_vars:
            this['PLATFORM_NUMBER'].attrs = {'long_name': 'Float unique identifier',
                             'convention': 'WMO float identifier : A9IIIII'}

        return this

    def _init_erddapy(self):
        # Init erddapy
        self.erddap = ERDDAP(
            server='http://www.ifremer.fr/erddap',
            protocol='tabledap'
        )
        self.erddap.response = 'csv'

        if self.dataset_id=='phy':
            self.erddap.dataset_id = 'ArgoFloats'
        elif self.dataset_id=='ref':
            self.erddap.dataset_id = 'argo_reference'
        else:
            raise ValueError("Invalid database short name for Ifremer erddap (use: 'phy' or 'ref')")
        return self


    def _minimal_vlist(self):
        """ Return the minimal list of variables to retrieve measurements for """
        vlist = list()
        if self.dataset_id == 'phy':
            plist = ['data_mode', 'latitude', 'longitude',
                     'position_qc', 'time', 'time_qc',
                     'direction', 'platform_number', 'cycle_number']
            [vlist.append(p) for p in plist]
            plist = ['pres', 'temp', 'psal']
            [vlist.append(p) for p in plist]
            [vlist.append(p + '_qc') for p in plist]
            [vlist.append(p + '_adjusted') for p in plist]
            [vlist.append(p + '_adjusted_qc') for p in plist]
            [vlist.append(p + '_adjusted_error') for p in plist]

        elif self.dataset_id == 'ref':
            plist = ['latitude', 'longitude', 'time',
                     'platform_number', 'cycle_number']
            [vlist.append(p) for p in plist]
            plist = ['pres', 'temp', 'psal', 'ptmp']
            [vlist.append(p) for p in plist]
        return vlist

    @property
    def url(self):
        """ Return the URL used to download data """

        # Define constraint to select this box of data:
        self.define_constraints()  # This will affect self.erddap.constraints

        # Define the list of variables to retrieve
        self.erddap.variables = self._minimal_vlist()

        # Get download URL:
        url = self.erddap.get_download_url(response='csv') + '&distinct()&orderBy("time,pres")'
        return url

    @property
    def cachepath(self):
        """ Return path to cache file for this request """
        src = self.cachedir
        file = ("TSargo_%s.nc") % (self.cname(cache=True))
        fcache = os.path.join(src, file)
        return fcache

    def to_xarray(self):
        """ Load Argo data and return a xarray.DataSet """

        # Try to load cached file if requested:
        if self.cache and os.path.exists(self.cachepath):
            ds = xr.open_dataset(self.cachepath)
            ds = self._cast_types(ds) # Cast data types
            return ds
        # No cache found or requested, so we compute:

        # Download data: get a csv, open it as pandas dataframe, convert it to xarrat dataset
        df = pd.read_csv(urlopen(self.url), parse_dates=True, skiprows=[1])
        ds = xr.Dataset.from_dataframe(df)
        df['time'] = pd.to_datetime(df['time'])
        ds['time'].values = ds['time'].astype(np.datetime64)

        # Post-process the xarray.DataSet:

        # Set coordinates:
        coords = ('latitude', 'longitude', 'time')
        # Convert all coordinate variable names to upper case
        for v in ds.data_vars:
            if v not in coords:
                ds = ds.rename({v: v.upper()})
        ds = ds.set_coords(coords)

        # Cast data types and add variable attributes (not available in the csv download):
        ds = self._cast_types(ds)
        ds = self._add_attributes(ds)

        # More convention:
        #         ds = ds.rename({'pres': 'pressure'})

        # Add useful attributes to the dataset:
        if self.dataset_id == 'phy':
            ds.attrs['DATA_ID'] = 'ARGO'
        elif self.dataset_id == 'ref':
            ds.attrs['DATA_ID'] = 'ARGO_Reference'
        ds.attrs['DOI'] = 'http://doi.org/10.17882/42182'
        ds.attrs['Downloaded_from'] = self.erddap.server
        ds.attrs['Downloaded_by'] = getpass.getuser()
        ds.attrs['Download_date'] = pd.to_datetime('now').strftime('%Y/%m/%d')
        ds.attrs['Download_url'] = self.url
        ds.attrs['Download_constraints'] = self.cname()
        ds = ds[np.sort(ds.data_vars)]

        # Possibly save in cache for later re-use
        if self.cache:
            ds.attrs['cache'] = self.cachepath
            ds.to_netcdf(self.cachepath)

        #
        return ds

    def filter_data_mode(self, ds, keep_error=True):
        """ Filter variables according to their data mode

            For data mode 'R' and 'A': keep 'PRES', 'TEMP' and 'PSAL'
            For data mode 'D': keep 'PRES_ADJUSTED', 'TEMP_ADJUSTED' and 'PSAL_ADJUSTED'

            this applies to <PARAM> and <PARAM_QC>
        """
        plist = ['pres', 'temp', 'psal']

        # Filter data according to data_mode:
        argo_r = ds.where(ds['DATA_MODE'] == 'R', drop=True)
        for v in plist:
            vname = v.upper() + '_ADJUSTED'
            if vname in argo_r:
                argo_r = argo_r.drop(vname)
            vname = v.upper() + '_ADJUSTED_QC'
            if vname in argo_r:
                argo_r = argo_r.drop(vname)
            vname = v.upper() + '_ADJUSTED_ERROR'
            if vname in argo_r:
                argo_r = argo_r.drop(vname)

        argo_a = ds.where(ds['DATA_MODE'] == 'A', drop=True)
        for v in plist:
            vname = v.upper()
            if vname in argo_a:
                argo_a = argo_a.drop(vname)
            vname = v.upper() + '_QC'
            if vname in argo_a:
                argo_a = argo_a.drop(vname)

        # argo_d = ds.where(ds['DATA_MODE'] == 'D', drop=True)
        # for v in plist:
        #     vname = v.upper()
        #     if vname in argo_d:
        #         argo_d = argo_d.drop(vname)
        #     vname = v.upper() + '_QC'
        #     if vname in argo_d:
        #         argo_d = argo_d.drop(vname)


        argo_d = ds.where(ds['DATA_MODE'] == 'D', drop=True)

        # Fill in the adjusted field with the non-adjusted wherever it is NaN
        # with this, we are sure to have values even for bad QC data in delayed mode
        ii = argo_d.where(np.isnan(argo_d['PRES_ADJUSTED']), drop=1)['index']
        argo_d['PRES_ADJUSTED'].loc[dict(index=ii)] = argo_d['PRES'].loc[dict(index=ii)]

        ii = argo_d.where(np.isnan(argo_d['TEMP_ADJUSTED']), drop=1)['index']
        argo_d['TEMP_ADJUSTED'].loc[dict(index=ii)] = argo_d['TEMP'].loc[dict(index=ii)]

        ii = argo_d.where(np.isnan(argo_d['PSAL_ADJUSTED']), drop=1)['index']
        argo_d['PSAL_ADJUSTED'].loc[dict(index=ii)] = argo_d['PSAL'].loc[dict(index=ii)]

        for v in plist:
            vname = v.upper()
            if vname in argo_d:
                argo_d = argo_d.drop(vname)
            vname = v.upper() + '_QC'
            if vname in argo_d:
                argo_d = argo_d.drop(vname)

        # Then create new arrays with the appropriate variables:
        PRES = xr.merge(
            (argo_r['PRES'], argo_a['PRES_ADJUSTED'].rename('PRES'), argo_d['PRES_ADJUSTED'].rename('PRES')))
        PRES_QC = xr.merge((argo_r['PRES_QC'], argo_a['PRES_ADJUSTED_QC'].rename('PRES_QC'),
                            argo_d['PRES_ADJUSTED_QC'].rename('PRES_QC')))
        if keep_error:
            PRES_ERROR = xr.merge((argo_a['PRES_ADJUSTED_ERROR'].rename('PRES_ERROR'),
                                   argo_d['PRES_ADJUSTED_ERROR'].rename('PRES_ERROR')))
            PRES = xr.merge((PRES, PRES_QC, PRES_ERROR))
        else:
            PRES = xr.merge((PRES, PRES_QC))

        TEMP = xr.merge(
            (argo_r['TEMP'], argo_a['TEMP_ADJUSTED'].rename('TEMP'), argo_d['TEMP_ADJUSTED'].rename('TEMP')))
        TEMP_QC = xr.merge((argo_r['TEMP_QC'], argo_a['TEMP_ADJUSTED_QC'].rename('TEMP_QC'),
                            argo_d['TEMP_ADJUSTED_QC'].rename('TEMP_QC')))
        if keep_error:
            TEMP_ERROR = xr.merge((argo_a['TEMP_ADJUSTED_ERROR'].rename('TEMP_ERROR'),
                                   argo_d['TEMP_ADJUSTED_ERROR'].rename('TEMP_ERROR')))
            TEMP = xr.merge((TEMP, TEMP_QC, TEMP_ERROR))
        else:
            TEMP = xr.merge((TEMP, TEMP_QC))

        PSAL = xr.merge(
            (argo_r['PSAL'], argo_a['PSAL_ADJUSTED'].rename('PSAL'), argo_d['PSAL_ADJUSTED'].rename('PSAL')))
        PSAL_QC = xr.merge((argo_r['PSAL_QC'], argo_a['PSAL_ADJUSTED_QC'].rename('PSAL_QC'),
                            argo_d['PSAL_ADJUSTED_QC'].rename('PSAL_QC')))
        if keep_error:
            PSAL_ERROR = xr.merge((argo_a['PSAL_ADJUSTED_ERROR'].rename('PSAL_ERROR'),
                                   argo_d['PSAL_ADJUSTED_ERROR'].rename('PSAL_ERROR')))
            PSAL = xr.merge((PSAL, PSAL_QC, PSAL_ERROR))
        else:
            PSAL = xr.merge((PSAL, PSAL_QC))

        final = xr.merge((TEMP, PSAL, PRES))
        plist = ['position_qc', 'time', 'time_qc', 'data_mode',
                 'direction', 'platform_number', 'cycle_number']
        for p in plist:
            vname = p.upper()
            if vname in ds:
                final = xr.merge((final, ds[vname]))
        for v in final.data_vars:
            if "QC" in v:
                final[v] = final[v].astype(int)
        final.attrs = ds.attrs
        final = self._add_history(final, 'Variables selected according to DATA_MODE')
        final = final[np.sort(final.data_vars)]
        # Cast data types and add attributes:
        final = self._cast_types(final)
        final = self._add_attributes(final)
        return final

    def filter_qc(self, this, QC_list=[1, 2], drop=True, mode='all', mask=False):
        """ Filter data set according to QC values

            Mask the dataset for points where 'all' or 'any' of the QC fields has a value in the list of
            integer QC flags.

            This method can return the filtered dataset or the filter mask.
        """
        if mode not in ['all', 'any']:
            raise ValueError("Mode must 'all' or 'any'")

        # Extract QC fields:
        QC_fields = []
        for v in this.data_vars:
            if "QC" in v:
                QC_fields.append(v)
        QC_fields = this[QC_fields]
        for v in QC_fields.data_vars:
            QC_fields[v] = QC_fields[v].astype(int)

        # Now apply filter
        this_mask = xr.DataArray(np.zeros_like(QC_fields['index']), dims=['index'],
                                 coords={'index': QC_fields['index']})
        for v in QC_fields.data_vars:
            for qc in QC_list:
                this_mask += QC_fields[v] == qc
        if mode == 'all':
            this_mask = this_mask == len(QC_fields)  # all
        else:
            this_mask = this_mask >= 1  # any

        if not mask:
            this = this.where(this_mask, drop=drop)
            for v in this.data_vars:
                if "QC" in v:
                    this[v] = this[v].astype(int)
            this = self._add_history(this, 'Variables selected according to QC')
            this = self._cast_types(this)
            this = self._add_attributes(this)
            return this
        else:
            return this_mask

class ErddapArgoDataFetcher_box(ErddapArgoDataFetcher):
    """ Manage access to Argo data through Ifremer ERDDAP for: an ocean rectangle

        __author__: gmaze@ifremer.fr
    """

    def init(self, box=[-65,-55,37,38,0,300,'1900-01-01','2100-12-31']):
        """ Create Argo data loader

            Parameters
            ----------
            box : list(float, float, float, float, float, float, str, str)
                The box domain to load all Argo data for:
                box = [lon_min, lon_max, lat_min, lat_max, pres_min, pres_max, datim_min, datim_max]
        """
        if len(box) == 6:
            # Use all time line:
            box.append('1900-01-01')
            box.append('2100-12-31')
        elif len(box) != 8:
            raise ValueError('Box must 6 or 8 length')
        self.BOX = box

        if self.dataset_id=='phy':
            self.definition = 'Ifremer erddap Argo data fetcher for a space/time region'
        elif self.dataset_id=='ref':
            self.definition = 'Ifremer erddap Argo REFERENCE data fetcher for a space/time region'

        return self

    def define_constraints(self):
        """ Define request constraints """
        self.erddap.constraints = {'longitude>=': self.BOX[0]}
        self.erddap.constraints.update({'longitude<=': self.BOX[1]})
        self.erddap.constraints.update({'latitude>=': self.BOX[2]})
        self.erddap.constraints.update({'latitude<=': self.BOX[3]})
        self.erddap.constraints.update({'pres>=': self.BOX[4]})
        self.erddap.constraints.update({'pres<=': self.BOX[5]})
        self.erddap.constraints.update({'time>=': self.BOX[6]})
        self.erddap.constraints.update({'time<=': self.BOX[7]})
        return None

    def cname(self, cache=False):
        """ Return a unique string defining the constraints """
        BOX = self.BOX
        if cache:
            boxname = ("%s_%s_%s_%s_%s_%s_%s_%s") % (self._format(BOX[0], 'lon'), self._format(BOX[1], 'lon'),
                                                     self._format(BOX[2], 'lat'), self._format(BOX[3], 'lat'),
                                                     self._format(BOX[4], 'prs'), self._format(BOX[5], 'prs'),
                                                     self._format(BOX[6], 'tim'), self._format(BOX[7], 'tim'))
        else:
            boxname = ("[x=%0.2f/%0.2f; y=%0.2f/%0.2f; z=%0.1f/%0.1f; t=%s/%s]") % \
                      (BOX[0],BOX[1],BOX[2],BOX[3],BOX[4],BOX[5],
                       self._format(BOX[6], 'tim'), self._format(BOX[7], 'tim'))

        boxname = self.dataset_id + "_" + boxname
        return boxname

class ErddapArgoDataFetcher_wmo(ErddapArgoDataFetcher):
    """ Manage access to Argo data through Ifremer ERDDAP for: a list of WMOs

        __author__: gmaze@ifremer.fr
    """

    def init(self, WMO=[6902746, 6902757, 6902766], CYC=None):
        """ Create Argo data loader for WMOs

            Parameters
            ----------
            WMO : list(int)
                The list of WMOs to load all Argo data for.
            CYC : int, np.array(int), list(int)
                The cycle numbers to load.
        """
        if isinstance(WMO, int):
            WMO = [WMO] # Make sure we deal with a list
        if isinstance(CYC, int):
            CYC = np.array((CYC,), dtype='int') # Make sure we deal with an array of integers
        if isinstance(CYC, list):
            CYC = np.array(CYC, dtype='int') # Make sure we deal with an array of integers
        self.WMO = WMO
        self.CYC = CYC

        if self.dataset_id=='phy':
            self.definition = 'Ifremer erddap Argo data fetcher for floats'
        elif self.dataset_id=='ref':
            self.definition = 'Ifremer erddap Argo REFERENCE data fetcher for floats'
        return self

    def define_constraints(self):
        """ Define erddap constraints """
        self.erddap.constraints = {'platform_number=~': "|".join(["%i"%i for i in self.WMO])}
        if isinstance(self.CYC, (np.ndarray)):
            self.erddap.constraints.update({'cycle_number=~': "|".join(["%i"%i for i in self.CYC])})
        return self

    def cname(self, cache=False):
        """ Return a unique string defining the constraints """
        if len(self.WMO) > 1:
            if cache:
                listname = ["WMO%i" % i for i in self.WMO]
                if isinstance(self.CYC, (np.ndarray)):
                    [listname.append("CYC%0.4d" % i) for i in self.CYC]
                listname = "_".join(listname)
            else:
                listname = ["WMO%i" % i for i in self.WMO]
                if isinstance(self.CYC, (np.ndarray)):
                    [listname.append("CYC%0.4d" % i) for i in self.CYC]
                listname = ";".join(listname)
        else:
            listname = "WMO%i" % self.WMO[0]
            if isinstance(self.CYC, (np.ndarray)):
                listname = [listname]
                [listname.append("CYC%0.4d" % i) for i in self.CYC]
                listname = "_".join(listname)
        listname = self.dataset_id + "_" + listname
        return listname


class ErddapArgoDataFetcher_box_deployments(ErddapArgoDataFetcher):
    """ Manage access to Argo data through Ifremer ERDDAP for: an ocean rectangle and 1st cycles only

        __author__: gmaze@ifremer.fr
    """

    def init(self, box=[-65,-55,37,38,0,300,'1900-01-01','2100-12-31']):
        """ Create Argo data loader

            Parameters
            ----------
            box : list(float, float, float, float, float, float, str, str)
                The box domain to load all Argo data for:
                box = [lon_min, lon_max, lat_min, lat_max, pres_min, pres_max, datim_min, datim_max]
        """
        if len(box) == 6:
            # Use all time line:
            box.append('1900-01-01')
            box.append('2100-12-31')
        elif len(box) != 8:
            raise ValueError('Box must 6 or 8 length')
        self.BOX = box

        if self.dataset_id=='phy':
            self.definition = 'Ifremer erddap Argo data fetcher for deployments in a space/time region'
        elif self.dataset_id=='ref':
            self.definition = 'Ifremer erddap Argo REFERENCE data fetcher for deployments in a space/time region'

        return self

    def define_constraints(self):
        """ Define request constraints """
        self.erddap.constraints = {'longitude>=': self.BOX[0]}
        self.erddap.constraints.update({'longitude<=': self.BOX[1]})
        self.erddap.constraints.update({'latitude>=': self.BOX[2]})
        self.erddap.constraints.update({'latitude<=': self.BOX[3]})
        self.erddap.constraints.update({'pres>=': self.BOX[4]})
        self.erddap.constraints.update({'pres<=': self.BOX[5]})
        self.erddap.constraints.update({'time>=': self.BOX[6]})
        self.erddap.constraints.update({'time<=': self.BOX[7]})
        self.erddap.constraints.update({'cycle_number=~': "1"})
        return None

    def cname(self, cache=False):
        """ Return a unique string defining the constraints """
        BOX = self.BOX
        if cache:
            boxname = ("%s_%s_%s_%s_%s_%s_%s_%s_cyc001") % (self._format(BOX[0], 'lon'), self._format(BOX[1], 'lon'),
                                                     self._format(BOX[2], 'lat'), self._format(BOX[3], 'lat'),
                                                     self._format(BOX[4], 'prs'), self._format(BOX[5], 'prs'),
                                                     self._format(BOX[6], 'tim'), self._format(BOX[7], 'tim'))
        else:
            boxname = ("[x=%0.2f/%0.2f; y=%0.2f/%0.2f; z=%0.1f/%0.1f; t=%s/%s]; CYC=1") % \
                      (BOX[0],BOX[1],BOX[2],BOX[3],BOX[4],BOX[5],
                       self._format(BOX[6], 'tim'), self._format(BOX[7], 'tim'))

        boxname = self.dataset_id + "_" + boxname
        return boxname
