import requests
import json
import time
import distance
import config


def _getMaxDist(source, I):
    # Get the maximum distance between the source (lon,lat) coordinate and a point in the isochrone I. Also return the bearing of this point
    maxDist = distance.GPSCrowDist(source, I[0], 0, 0)
    furthestPoint = I[0]
    for i in range(1, len(I)):
        d = distance.GPSCrowDist(source, I[i], 0, 0)
        if d > maxDist:
            maxDist = d
            furthestPoint = I[i]
    bearing = distance.getBearing(
        source[0], source[1], furthestPoint[0], furthestPoint[1])
    return maxDist, bearing


def getIsochrone(source, dist, travelMode):
    try:
        body = {"locations": [source],  # source coords
                "range": [dist],  # range/diameter of the isochrone
                "location_type": "start",  # source is a start point, not an end point
                "range_type": "distance",  # isochrone is concerned with distance, not time
                # how smoothed should the polygon be? 1 = no smoothing; 100 = maximum smoothing
                "smoothing": 1,
                "area_units": "m",  # everything is in meters
                "units": "m"}  # everything is in meters
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
            'Authorization': config.ORSKEY,
            'Content-Type': 'application/json; charset=utf-8'
        }
        if travelMode == 1:
            s = "https://api.openrouteservice.org/v2/isochrones/driving-car"
        elif travelMode == 2:
            s = "https://api.openrouteservice.org/v2/isochrones/cycling-regular"
        else:
            s = "https://api.openrouteservice.org/v2/isochrones/foot-walking"
        start = time.time()
        call = requests.post(s, json=body, headers=headers)
        end = time.time()
        config.totalNumCalls += 1
        config.totalCallTime += end-start
        if int(call.status_code) != 200 and int(call.status_code) != 201:
            config.myQuit("Isochrone request failed. Code = " +
                          str(call.status_code) + ": " + str(call.reason))
        # If we are here, the request was successful so we can continue
        X = json.loads(call.text)
        I = X["features"][0]["geometry"]["coordinates"][0]
        x, bearing = _getMaxDist(source, I)
        # In some cases, the shrinkFactor can be larger than 1. So we return one instead
        shrinkFactor = min(x/dist, 1.0)
        return I, shrinkFactor, bearing
    except:
        config.myQuit(
            "Error occurred in getIsochrone function. Likely a temporary server-side issue. Ending.")
