#!/bin/env python
# -*coding: UTF-8 -*-
#
# Test data data_fetchers
#
# Created by gmaze on 09/03/2020

import os
import sys
import numpy as np
import xarray as xr
import unittest
from unittest import TestCase
from argopy import DataFetcher as ArgoDataFetcher

class DataFetcherTest(TestCase):
    """ Test main API facade for all available fetching backends """

    def setUp(self):
        # Determine the list of data fetchers to test:
        self.backends = list()
        try:
            from erddapy import ERDDAP
            self.backends.append('erddap')
        except ModuleNotFoundError:
            pass

        #todo Determine the list of output format to test
        # what else beyond .to_xarray() ?

        # Define API access point options
        self.args = {}
        self.args['float'] = [[1901393], [1901393, 6902746]]
        self.args['profile'] = [[6902746, 34],[6902746, np.arange(12, 16)], [6902746, [1, 12]]]
        self.args['region'] = [[-80, -75, 10., 15., 0, 10.], [-80, -75, 10., 15., 0, 10., '2012-01', '2013-12']]


    def test_float(self):
        for bk in self.backends:
            for arg in self.args['float']:
                ds = ArgoDataFetcher(backend=bk).float(arg).to_xarray()
                assert isinstance(ds, xr.Dataset) == True

    def test_profile(self):
        for bk in self.backends:
            for arg in self.args['profile']:
                ds = ArgoDataFetcher(backend=bk).profile(*arg).to_xarray()
                assert isinstance(ds, xr.Dataset) == True

    def test_region(self):
        for bk in self.backends:
            for arg in self.args['region']:
                ds = ArgoDataFetcher(backend=bk).region(arg).to_xarray()
                assert isinstance(ds, xr.Dataset) == True


if __name__ == '__main__':
    unittest.main()