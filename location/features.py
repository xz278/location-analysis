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
import geohash


def gyration_radius(data,
                    k=None,
                    lat_c='latitude',
                    lon_c='longitude',
                    cluster_c='cluster'):
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

    lat_c, lon_c, cluster_c: str
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
    loc_data = data[[lat_c, lon_c, cluster_c]].dropna()
    if len(loc_data) == 0:
        return np.nan

    # get location data for corresponding k
    if k is not None:
        cnt_locs = Counter(loc_data[cluster_c])
        # number of different visited locations
        num_visited_locations = len(cnt_locs)
        if k > num_visited_locations:
            return np.nan
        else:
            # k most frequent visited locations
            k_locations = cnt_locs.most_common()[:k]
            k_locations = [x[0] for x in k_locations]
            # compute gyration for the k most frequent locations
            loc_data = loc_data.loc[loc_data[cluster_c].isin(k_locations)]

    # compute mass of locations
    r_cm = motif.get_geo_center(loc_data, lat_c=lat_c, lon_c=lon_c)
    r_cm = (r_cm['latitude'], r_cm['longitude'])

    # compute gyration of radius
    cluster_cnt = Counter(loc_data[cluster_c])
    tmp = 0
    for c in cluster_cnt:
        cluster_gps = convert_geohash_to_gps(c)
        d = vincenty(r_cm, cluster_gps).m
        tmp += cluster_cnt[c] * (d ** 2)

    return math.sqrt(tmp / len(loc_data))


def num_trips(data,
              cluster_c='cluster'):
    """
    Compute the number of trips from one
    location to another.

    Parameters:
    -----------
    data: DataFrame
        location data.

    cluster_c: str
        Location cluster column.
        Default value is 'cluster'.

    Returns:
    --------
    n_trip: int
        Number of trips.
    """
    data = data.loc[~pd.isnull(data[cluster_c])]

    if len(data) == 0:
        return np.nan

    data = data.reset_index()

    # previous location
    p = data.ix[0, cluster_c]
    n_trip = 0

    for i in range(1, len(data)):

        # current location
        c = data.ix[i, cluster_c]
        if p == c:
            continue
        else:
            n_trip += 1
            p = c

    return n_trip


def max_dist_between_clusters(data,
                              cluster_c='cluster',
                              lat_c='latitude',
                              lon_c='longitude'):
    """
    Compute the maximum distance between two
    location clusters.

    Parameters:
    -----------
    data: DataFrame
        Location data.

    cluster_c: str
        Location cluster id column.

    lat_c, lon_c: str
        Latidue and longitude of the cluster
        locations.

    Returns:
    --------
    max_dist: float
        Maximum distance between two locations in meters.
    """
    data = data.loc[~pd.isnull(data[cluster_c])]

    if len(data) == 0:
        return np.nan

    locations = np.unique(data[cluster_c])
    if len(locations) == 1:
        return 0

    # get list of different gps coordinates
    locations_coord = []
    for l in locations:
        df = data.loc[data[cluster_c] == l].reset_index()
        gps = (df.ix[0, lat_c], df.ix[0, lon_c])
        locations_coord.append(gps)

    # find maximum distance
    max_dist = 0
    for i in range(len(locations) - 1):
        for j in range(i + 1, len(locations)):
            d = vincenty(locations_coord[i], locations_coord[j]).m
            if d > max_dist:
                max_dist = d

    return max_dist


def num_clusters(data, cluster_c='cluster'):
    """
    Compute the number of location clusters, which is
    the number of different places visited.

    Parameters:
    -----------
    data: DataFrame
        Location data.

    cluster_c: str
        Location cluster id.

    Returns:
    --------
    n: int
        Number of clusters.
    """
    data = data[[cluster_c]].dropna()
    if len(data) == 0:
        return 0
    else:
        n = len(np.unique(data))
        return n


def displacement(data,
                 lat_c='latitude',
                 lon_c='longitude',
                 cluster_c='cluster'):
    """
    Calculate the displacement of the location data,
    which is list of distances traveled from one location
    to another.

    Parameters:
    -----------
    data: dataframe
        Location data.

    cluster_c: str
        Column cluster ids.
        Default value is cluster.

    lat_c, lon_c: str
        Columns of latitude, and longitude.
        Default values are 'latitude', and
        'longitude' respectively.

    Returns:
    --------
    displace: list
        List of displacements in meters.
    """
    data = data.loc[~pd.isnull(data[cluster_c])]
    displace = []

    if len(data) == 1:
        return displace

    # location history
    data = data.loc[data[cluster_c] != data[cluster_c].shift()]

    # compute displacements
    prev = None
    for _, row in data.iterrows():
        if prev is None:
            prev = (row[lat_c], row[lon_c])
            continue
        curr = (row[lat_c], row[lon_c])
        d = vincenty(prev, curr).m
        displace.append(d)
        prev = curr

    return displace


def wait_time(data,
              cluster_c='cluster',
              time_c='index'):
    """
    Calculate the waiting time between
    displacements, which is the amount of
    time spent at each location.

    Location data has to be evenly sampled.
    Time spent at each recorded entry of location
    is approximated by one typical time interval in
    the evenly sampled data.

    Time is measured in seconds.

    Parameters:
    -----------
    data: dataframe
        Location data.

    cluster_c: str
        Cluster id column.
        Defaults to 'cluster'.

    time_c: str
        Time column.
        Defaults to 'index', in which
        case the index is a timeindex series.

    Returns:
    --------
    waittime: list
        List of waiting time in minute.

    cluster_wt: dict
        Waiting time for each location cluster.
        {cluster_id: waiting time}
    """
    data = data.copy()
    cluster_col = data[cluster_c].values
    if time_c == 'index':
        time_col = data.index
    else:
        time_col = data[time_c]
    data = pd.DataFrame()
    data['time'] = time_col
    data[cluster_c] = cluster_col
    waittime = []
    if len(data) <= 1:
        return waittime, {}

    # compute approximate time spent at each recorded entry
    data['td'] = ((data[['time']].shift(-1) - data[['time']]) +
                  (data[['time']] - data[['time']].shift())) / 2
    data.ix[0, 'td'] = (data.ix[1, 'time'] - data.ix[0, 'time']) / 2
    l = len(data)
    data.ix[l-1, 'td'] = (data.ix[l - 1, 'time'] -
                          data.ix[l - 2, 'time']) / 2

    # skip leading empty entries
    i = 0
    while i < len(data) and pd.isnull(data.ix[i, cluster_c]):
        i += 1
    curr_c = [i]

    # merge waiting time if two or more consecutive
    # locations belong to the same location cluster
    for p in range(i + 1, l):
        curr_cluster = data.ix[p, cluster_c]
        if pd.isnull(curr_cluster):
            if len(curr_c) == 0:
                continue
            wt = data.loc[data.index.isin(curr_c), 'td'].sum()
            waittime.append(wt.seconds)
            curr_c = []
        else:
            if len(curr_c) == 0:
                curr_c.append(p)
            elif data.ix[curr_c[-1], cluster_c] != curr_cluster:
                wt = data.loc[data.index.isin(curr_c), 'td'].sum()
                waittime.append(wt.seconds)
                curr_c = [p]
            else:
                curr_c.append(p)

    # handle the last row
    if len(curr_c) > 0:
        wt = data.loc[data.index.isin(curr_c), 'td'].sum()
        waittime.append(wt.seconds)

    # compute the time spent at each location
    cluster_wt = {}
    grouped = data.groupby(cluster_c)
    for i, g in grouped:
        cluster_wt[i] = g['td'].sum().seconds

    return waittime, cluster_wt


def entropy(data,
            cluster_c='cluster',
            time_c='index',
            wait_time_v=None):
    """
    Calculate entropy, a measure of
    the variability in the time that
    participants spend in the different
    locations recorded.

    Entropy is computed as the cumulative products
    of proportion and the log of the proportion of
    time spent at each location.

    Normalized entropy is also calculated as a
    variant of the entropy fieature scaled to be in
    the range [0, 1].

    This value calcuated by dividing the original
    entropy by the number of different locations.
    【Palmius et al, 2016]

    Parameters:
    -----------
    data: dataframe
        Location data.

    cluster_c: str
        Location cluster column name.

    time_c: str
        Timestamp column name.

    wait_time_v: tuple
        Values returned by wait_time().

    Returns:
    --------
    tuple of (ent, nent)
        A tuple contains entropy and normalized entropy.
    """
    # compute entropy
    if len(data) == 0:
        ent = np.nan
    else:
        if time_c == 'index':
            time_col = data.index
        else:
            time_col = data[time_c]

        total_time = (max(time_col) - min(time_col)).seconds

        # compute waitting time is not provided
        if wait_time_v is None:
            wt, cwt = wait_time(data, cluster_c, time_c)
        else:
            wt, cwt = wait_time_v

        if len(wt) == 0:
            ent = np.nan
        else:
            ent = 0
            for k in cwt:
                p = cwt[k] / total_time
                ent -= p * math.log(p)

    # compute normalized entropy
    if np.isnan(ent):
        nent = np.nan
    else:
        unique_loc = np.unique(data[cluster_c].dropna())
        n = len(unique_loc)

        # if the number of clusters is one,
        # the log value would be 0 and thus
        # can't be used as the denominator
        if n == 1:
            nent = np.nan
        else:
            nent = ent / math.log(n)

    return ent, nent


def loc_var(data,
            lat_c='latitude',
            lon_c='longitude',
            cluster_c='cluster'):
    """
    Location variance, an indication of
    how much the individual is moving
    between different locations based on
    the sum of statistical variances in
    the latitdue and longitude.
    【Palmius et al, 2016]

    Parameters:
    -----------
    data: dataframe
        Location data.

    lat_c, lon_c, cluster_c: str
        Latitude, longitude, and cluster
        columns. Default values are 'latitude',
        'longitude', and 'cluster' respectively.

    Returns:
    --------
    lv: float
        Location variance.
    """
    data = data.loc[~pd.isnull(data[cluster_c])]
    if len(data) != 0:
        lat_v = np.var(data[lat_c])
        lon_v = np.var(data[lon_c])
        if abs(lat_v + lon_v) < 0.000000001:
            lv = np.nan
        else:
            lv = math.log(lat_v + lon_v)
    else:
        lv = np.nan
    return lv


def home_stay(data,
              home_loc,
              cluster_c='cluster',
              time_c='index',
              wait_time_v=None):
    """
    Compute the time spent at home location.
    Time is in seconds.

    Parameters:
    -----------
    data: DataFrame
        Location data.

    home_loc: str or int
        Home location cluster.

    cluster_col: str
        Location cluster column.
        Default value is 'cluster'.

    time_col: str
        Timestamp column.
        Default value is 'index'.

    wait_time_v: tuple
        Returned values from wait_time().

    Returns:
    --------
    hs: float
        Time spent at home location.
    """
    if home_loc not in data[cluster_c].values:
        hs = np.nan
    else:

        # compute waitting time if not provided
        if wait_time_v is None:
            wt, cwt = wait_time(data,
                                cluster_c=cluster_c,
                                time_c=time_c)
        else:
            wt, cwt = wait_time_v

        if len(wt) == 0:
            hs = np.nan
        else:
            hs = cwt[home_loc]

    return hs


def trans_time(data,
               cluster_c='cluster',
               time_c='index',
               wait_time_v=None):
    """
    Calculate the total time spent in travelling
    in seconds. This calculated by substracting the waitting
    time from the total time.

    Parameters:
    -----------
    data: dataframe
        Location data.

    cluster_c: str
        Cluster id column.
        Defaults to 'cluster'.

    time_c: str
        Time column.
        Defaults to 'index', in which
        case the index is a timeindex series.

    wait_time_v: tuple
        Returned values from wait_time().

    Returns:
    --------
    tt: float
        Transition time.
    """
    # compute waitting time if not provided
    if wait_time_v is None:
        wt, cwt = wait_time(data,
                            cluster_c=cluster_c,
                            time_c=time_c)
    else:
        wt, cwt = wait_time_v

    if len(wt) == 0:
        tt = np.nan
    else:
        if time_c == 'index':
            time_col = data.index
        else:
            time_col = data[time_c]

        # compute total time and subtract waitting time
        # from it
        total_time = (max(time_col) - min(time_col)).seconds
        tt = total_time - sum(wt)

    return tt


def total_dist(data,
               cluster_c='cluster',
               lat_c='latitude',
               lon_c='longitude',
               dispmnt=None):
    """
    The sum of travel distance in meters.
    This value computed by taking the sum
    of all the values returned by displacement()
    since the total distance is the sum of
    all displacements/individual travel distance.

    Parameters:
    -----------
    data: DataFrame
        Location data.

    cluster_c: str
        Location cluster id column.

    lat_c, lon_c: str
        Latidue and longitude of the cluster
        locations.

    dispmnt: list
        List of displacements returned by displacement().

    Returns:
    --------
    td: float
        Total distance.
    """
    if dispmnt is None:
        dispmnt = displacement(data=data,
                               lat_c=lat_c,
                               lon_c=lon_c,
                               cluster_c=cluster_c)

    td = sum(dispmnt)
    return td


def convert_geohash_to_gps(geohash_str):
    """
    Convert geohash value to gps value.

    Parameters:
    -----------
    geohash_str: str
        Geohash string.

    Returns:
    --------
    gps: tuple of floats
        GPS values.
        (latitude, longitude)
    """
    lat, lon = geohash.decode(geohash_str)
    return lat, lon


def convert_and_append_geohash(data,
                               cluster_c='cluster',
                               lat_c='latitude',
                               lon_c='longitude'):
    """
    Convert geohash to gps and append
    to the dataframe as new columns.

    Parameters:
    -----------
    data: DataFrame
        Location data

    cluster_c: str
        Location cluster column.

    Returns:
    --------
    data: DataFrame
        Location data with converted geohash value.
    """
    for idx, row in data.iterrows():
        if pd.isnull(row[cluster_c]):
            continue
        lat, lon = convert_geohash_to_gps(row[cluster_c])
        data.loc[idx, lat_c] = lat
        data.loc[idx, lon_c] = lon
    return data
