# -*- coding: utf-8 -*-
"""
    Module for location features.
"""

import numpy as np
import pandas as pd
from location import motif
from geopy.distance import vincenty
import math
from collections import Counter
import pytz
import datetime


def gyrationradius(data,
                   k=None,
                   lat='latitude',
                   lon='longitude',
                   cluster='cluster'):
    """
    Compute the total or k-th radius of gyration.
    The radius of gyration is used to characterize the typical
    distance travelled by an individual.

    This follows the work of Pappalardo et al.
    (see http://www.nature.com/articles/ncomms9166)

    Parameters:
    -----------
    data: DataFrame
        Location data.

    k: int
        k-th radius of gyration.
        Default is None, in this case return total radius of gyration.
        k-th radius of gyration is the radius gyration compuated up to
        the k-th most frequent visited locations.

    lat, lon, cluster: str
        Columns of latitude, longitude, and
        cluster ids. The default valuesa are
        'latitude', 'longitude', and 'cluster'
        respectively.

    Returns:
    --------
    float
        Radius of gyration in meters.
        Return np.nan is k is greater than the number of different
        visited locations.
    """
    loc_data = data[[lat, lon, cluster]].dropna()
    if len(loc_data) <= 0:
        return np.nan

    # get location data for corresponding k
    if k is not None:
        cnt_locs = Counter(loc_data[cluster])
        # number of different visited locations
        num_visited_locations = len(cnt_locs)
        if k > num_visited_locations:
            return np.nan
        else:
            # k most frequent visited locations
            k_locations = cnt_locs.most_common()[:k]
            k_locations = [x[0] for x in k_locations]
            # compute gyration for the k most frequent locations
            loc_data = loc_data.loc[loc_data[cluster].isin(k_locations)]

    # compute mass of locations
    r_cm = motif.get_geo_center(loc_data, lat_c=lat, lon_c=lon)
    r_cm = (r_cm['latitude'], r_cm['longitude'])

    # compute gyration of radius
    temp_sum = 0
    for _, r in loc_data.iterrows():
        p = (r[lat], r[lon])
        d = vincenty(p, r_cm).m
        temp_sum += d ** 2

    return math.sqrt(temp_sum / len(loc_data))
