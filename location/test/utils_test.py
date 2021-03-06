# -*- coding: utf-8 -*-
"""
    location.test.utils_test
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Unit testing motif module

    :copyright: (c) 2016 by Saeed Abdullah.

"""

import numpy as np
import pandas as pd

from location import utils
import pytest
from pytest import approx


def test_compute_gyration():
    # test data
    data_stay_region = ['dr5xfdt',
                        'dr5xfdt',
                        'dr5xfdt',
                        'dr5rw5u',
                        'dr5rw5u',
                        'dr5rw5u',
                        'dr5rw5u',
                        'dr5rw5u',
                        'dr5rw5u',
                        'dr5rw5u']
    df = pd.DataFrame()
    df['stay_region'] = data_stay_region

    # expected result
    expected = 7935.926632803189

    # tolerance = 0.01 meter
    assert utils.compute_gyration(df) == pytest.approx(expected, 0.01)

    # check when k is larger the number of different visited locations
    assert np.isnan(utils.compute_gyration(df, k=5))

    # add the last gps point for five more times
    add_df = pd.DataFrame()
    add_df['stay_region'] = ['dr5rw5u'] * 5
    df = pd.concat([df, add_df.copy()])

    expected = 6927.0444113855365
    assert utils.compute_gyration(df) == pytest.approx(expected, 0.01)

    # test the k-th radius of gyration
    add_df = pd.DataFrame()
    add_df['stay_region'] = ['dr5xg5g'] * 2
    df = pd.concat([df, add_df.copy()])
    assert utils.compute_gyration(df, k=2) == pytest.approx(expected, 0.01)


def test_compute_regularity():
    df = pd.DataFrame()
    timestamp = pd.Timestamp('2016-12-5 00:30:00')
    df['time'] = pd.date_range(timestamp, periods=2, freq='7d')
    df.loc[2, 'time'] = pd.Timestamp('2016-12-6 1:30:00')
    df['stay_region'] = ['dr5rw5u', 'dr5xg5g', 'dr5xg5g']
    df = df.set_index('time')

    reg = utils.compute_regularity(df)

    reg_computed1 = reg.loc[(reg.index.get_level_values('weekday') == 0) &
                            (reg.index.get_level_values('hour') == 0),
                            'regularity']

    assert reg_computed1.iloc[0] == pytest.approx(0.5)

    reg_computed2 = reg.loc[(reg.index.get_level_values('weekday') == 1) &
                            (reg.index.get_level_values('hour') == 1),
                            'regularity']

    assert reg_computed2.iloc[0] == pytest.approx(1)
