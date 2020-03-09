#!/bin/env python
# -*coding: UTF-8 -*-
#
# Test data fetchers
#
# Created by gmaze on 09/03/2020

import os
import sys
import numpy as np
import xarray as xr
from argopy.fetchers import ArgoDataFetcher
import unittest
from unittest import TestCase

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

    def test_float(self):
        args = [[1901393], [1901393, 6902746]] # Could be any wmo
        for bk in self.backends:
            for arg in args:
                ds = ArgoDataFetcher(backend=bk).float(arg).to_xarray()
                assert isinstance(ds, xr.Dataset) == True

    def test_profile(self):
        args = [[6902746, 34],[6902746, np.arange(12, 16)], [6902746, [1, 12]]]
        for bk in self.backends:
            for arg in args:
                ds = ArgoDataFetcher(backend=bk).profile(*arg).to_xarray()
                assert isinstance(ds, xr.Dataset) == True

    def test_region(self):
        args = [[-80, -75, 10., 15., 0, 10.], [-80, -75, 10., 15., 0, 10., '2012-01', '2013-12']]
        for bk in self.backends:
            for arg in args:
                ds = ArgoDataFetcher(backend=bk).region(arg).to_xarray()
                assert isinstance(ds, xr.Dataset) == True


if __name__ == '__main__':
    unittest.main()