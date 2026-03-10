import visRoutes
import polygons
import isochrone
import getRoutes
import optimisation
import config
import random
import time
import argparse


def getRegressionCoefficients(XVals, YVals):
    assert len(XVals) == len(
        YVals), "Error: Input lists in getRegressionCoefficients must be the same size"
    assert len(
        XVals) >= 1, "Error: Input lists in getRegressionCoefficients must be non-empty"
    n = len(XVals)
    # mean of x and y vector
    sumY = sum(YVals)
    sumX = sum(XVals)
    sumX2 = 0
    sumXY = 0
    for i in range(len(XVals)):
        sumX2 += XVals[i]**2
        sumXY += XVals[i]*YVals[i]
    # Calculate the intercept a and slope b
    a = (sumY * sumX2 - sumX * sumXY) / (n * sumX2 - sumX**2)
    b = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX**2)
    return a, b


def getInitialEstimatedWPs(source, k, initialBearing, n, I, maxLen):
    # Generates up to maxLen n-point ellipses whose points are all within the isochrone I
    polygonList = []
    for reduction in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]:
        for aspectRatio in [1, 1/2, 2, 1/3, 3, 1/4, 4, 1/5, 5, 1/6, 6, 1/7, 7, 1/8, 8, 1/9, 9, 1/10, 10]:
            for angle in [0, 90, 180, 270, 30, 120, 210, 300, 60, 150, 240, 330]:
                bearing = (initialBearing + angle) % 360
                coords = polygons.getEllipseGPSCoords(
                    source, reduction*k, bearing, aspectRatio, n)
                if polygons.allCoordsInsideIsochrone(coords, I):
                    polygonList.append(
                        {"estimatedWPs": coords, "estimatedWPsPerimeter": reduction*k, "degreeBearing": bearing})
                    if len(polygonList) >= maxLen:
                        return polygonList
    return polygonList


def main():
    # Define the command line interface, read in the variables from the command line interface, and do some bounds checks
    parser = argparse.ArgumentParser(
        description="Fixed-length route generator using OpenRouteService API (R. Lewis, Cardiff University, 2023)",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-s",      nargs=2, type=float,
                        help="start lon-lat coordinates \n\tdefault = -3.719126 51.486733", default=[-3.719126, 51.486733])
    parser.add_argument("-k",      type=int,
                        help="desired length in meters \n\tdefault = 5000", default=5000)
    parser.add_argument("-a",      nargs=2, type=int,
                        help="algorithm choice and associated parameter x.\n\t1 x = Isochrone-polygon (IP) method with multiple routes per call (for x calls);\n\t2 x = IP method. Generate x polygons and get each route via a separate call;\n\t3 x = OpenRouteService round_trip function (execute for x seeds/calls)\n\t4 x = Do IP method and then do x-1 further rounds of linear regression learning\n\tdefault = 1 1", default=[1, 1])
    parser.add_argument("-t",      type=int,
                        help="travel mode:\n\t1 = driving-car\n\t2 = cycling-regular\n\t3 = foot-walking\n\tdefault = 1", choices={1, 2, 3}, default=1)
    parser.add_argument("-n",      type=int,
                        help="number of points on each polygon (min = 3)\n\tdefault = 3", default=3)
    parser.add_argument("-o",      type=int,
                        help="optimisation option for stage 2\n\t0 = no optimisation\n\t1 = local search using BFS\n\t2 = local search using RFS\n\t3 = Johnson's algorithm\n\tdefault = 0", choices={0, 1, 2, 3}, default=0)
    parser.add_argument("-seed",   type=int,
                        help="random seed used with local search procedure\n\tdefault = 1", default=1)
    parser.add_argument("-name",   type=str,
                        help="name of the output .html files.\n\tdefault = out", default="out")
    parser.add_argument("-r",      action="store_true",
                        help="remove out-and-backs")
    parser.add_argument("-v",      action="store_true",
                        help="show NetworkX visualisations of smoothed graph (requires user interaction)")
    args = vars(parser.parse_args())
    with open("log.txt", "a") as f:
        f.write(str(args) + ", ")
    s = args["s"]
    place = args["name"]
    k = args["k"]
    n = args["n"]
    travelMode = args["t"]
    removeBackAndForths = args["r"]
    LSOption = args["o"]
    doVis = args["v"]
    algChoice = args["a"][0]
    algIterations = args["a"][1]
    random.seed(args["seed"])
    if s[0] < -180.0 or s[0] > 180 or s[1] < -180.0 or s[1] > 180:
        config.myQuit("Invalid GPS coordinates for the source vertex")
    if algChoice < 1 or algChoice > 4 or algIterations < 1:
        config.myQuit("Invalid values specified for -a")
    if k <= 0 or k > 250000:
        config.myQuit("Specified k-value out of bounds")
    if n <= 2 or n > config.MAXWP - 1:
        config.myQuit("Specified n-value out of bounds")

    # If we are here, the input commands are valid. So, start the clock
    start = time.time()

    # weight, surface and green hold values for each observed edge; height holds a value for each observed vertex
    weight = dict()
    surface = dict()
    green = dict()
    height = dict()

    # Generate an isochrone from the source with "radius" k/2 meters
    I, initShrinkFactor, initBearing = isochrone.getIsochrone(
        s, k/2, travelMode)
    print("Input parameters   =", args)
    print("Value for k'       =", int(k * initShrinkFactor))
    print("Initial Bearing    =", initBearing)

    solList = []
    if algChoice == 1:

        # Generate a set of n-point ellipses whose points are totally within the isochrone
        polygonsPerCall = (config.MAXWP - 1) // n
        polygonList = getInitialEstimatedWPs(
            s, k*initShrinkFactor, initBearing, n, I, algIterations * polygonsPerCall)
        if len(polygonList) <= 0:
            visRoutes.makeVisualisationOfSource(
                s, travelMode, k, outFile=place, isochrone=I)
            config.myQuit(
                "No polygons could be fitted into the isochrone. Check " + place + ".html for details.")
        print("Num polygons made  =", len(polygonList), "\n")

        # Calculate several routes per call (using several polygons each time)
        i = 0
        for j in range(algIterations):
            print("Calculating routes", i, "to", min(i+polygonsPerCall, len(polygonList))-1, "using isochrone method")
            subList = polygonList[i:min(i+polygonsPerCall, len(polygonList))]
            sols = getRoutes.getRoutes(subList, removeBackAndForths, weight, surface, green, height, False, travelMode)
            solList.extend(sols)
            i += polygonsPerCall
            if i >= len(polygonList):
                break

        # Make a visualisation of the solutions.
        visRoutes.makeVisualisationFromCoords(s, [el['routeVertices'] for el in solList], k, travelMode, I, weight, height, surface, place, polygons=[
                                              el['estimatedWPs'] for el in solList], WPPolygons=[el['actualWPs'] for el in solList], green=green)
        print("Solutions written to html file:", place)

    elif algChoice == 2:

        # Generate the set of n-point, ellipses whose points are totally within the isochrone
        polygonList = getInitialEstimatedWPs(
            s, k*initShrinkFactor, initBearing, n, I, algIterations)
        if len(polygonList) <= 0:
            visRoutes.makeVisualisationOfSource(
                s, travelMode, k, outFile=place, isochrone=I)
            config.myQuit(
                "No polygons could be fitted into the isochrone. Check " + place + ".html for details.")
        print("Num polygons made  =", len(polygonList), "\n")

        # Produce the routes using a single call for each individual polygon
        for i in range(min(algIterations, len(polygonList))):
            print("Calculating route", i, "using isochrone method")
            sols = getRoutes.getRoutes(
                [polygonList[i]], removeBackAndForths, weight, surface, green, height, True, travelMode)
            solList.extend(sols)

        # Make a visualisation of the solutions.
        visRoutes.makeVisualisationFromCoords(s, [el['routeVertices'] for el in solList], k, travelMode, I, weight, height, surface, place, polygons=[
                                              el['estimatedWPs'] for el in solList], WPPolygons=[el['actualWPs'] for el in solList], green=green)
        print("Solutions written to html file:", place)

    elif algChoice == 3:

        # Use the round_trip function in openrouteservice to get several routes
        solList = getRoutes.round_trip(
            s, k, n, travelMode, removeBackAndForths, algIterations, weight, surface, green, height)

        # Make a visualisation of the solutions.
        visRoutes.makeVisualisationFromCoords(
            s, [el['routeVertices'] for el in solList], k, travelMode, I, weight, height, surface, place, green=green)
        print("Solutions written to html file:", place)

    else:

        # Generate a set of n-point ellipses whose points are totally within the isochrone and calculate the routes and actual waypoints of these
        polygonsPerCall = (config.MAXWP - 1) // n
        polygonList = getInitialEstimatedWPs(
            s, k*initShrinkFactor, initBearing, n, I, polygonsPerCall)
        if len(polygonList) <= 0:
            visRoutes.makeVisualisationOfSource(
                s, travelMode, k, outFile=place, isochrone=I)
            config.myQuit(
                "No polygons could be fitted into the isochrone. Check " + place + ".html for details.")
        print("Num polygons made  =", len(polygonList), "\n")
        print("0 ) Calculating", len(polygonList),
              " routes using isochrone method")
        sols = getRoutes.getRoutes(
            polygonList, removeBackAndForths, weight, surface, green, height, False, travelMode)

        # Set up the initial regression models for each polygon in "sols"
        XVals = [[] for i in range(len(sols))]
        YVals = [[] for i in range(len(sols))]
        coefficients = [[] for i in range(len(sols))]
        actualWPs = [[] for i in range(len(sols))]
        for j in range(len(sols)):
            XVals[j].append(0.0)
            YVals[j].append(0.0)
            XVals[j].append(sols[j]["actualWPsPerimeter"])
            YVals[j].append(sols[j]["routeLength"])
            actualWPs[j].append(sols[j]["actualWPs"])
            a, b = getRegressionCoefficients(XVals[j], YVals[j])
            coefficients[j] = [a, b]

        # All observed solutions are added to solList
        solList.extend(sols)

        # Now do "learning" via linear regression for the specified number of iterations. In each iteration, a new set of
        # solutions called "sols" is created (via one call) and the regression models are updated
        for i in range(1, algIterations):
            polygonList = []
            for j in range(len(actualWPs)):
                newPerimeter = (k - coefficients[j][0]) / coefficients[j][1]
                x = random.randrange(len(actualWPs[j]))
                P = polygons.getRescaledPolygon(
                    actualWPs[j][x], newPerimeter, n)
                newPolygon = {
                    "estimatedWPs": P, "estimatedWPsPerimeter": newPerimeter,  "degreeBearing": None}
                polygonList.append(newPolygon)
            print(i, ") Calculating", len(polygonList),
                  " new routes using isochrone method with linear regression model")
            sols = getRoutes.getRoutes(
                polygonList, removeBackAndForths, weight, surface, green, height, False, travelMode)
            for j in range(len(sols)):
                XVals[j].append(sols[j]["actualWPsPerimeter"])
                YVals[j].append(sols[j]["routeLength"])
                actualWPs[j].append(sols[j]["actualWPs"])
                a, b = getRegressionCoefficients(XVals[j], YVals[j])
                coefficients[j] = [a, b]
            solList.extend(sols)

        # Make a visualisation of all the the solutions.
        visRoutes.makeVisualisationFromCoords(s, [el['routeVertices'] for el in solList], k, travelMode, I, weight, height, surface, place, polygons=[
                                              el['estimatedWPs'] for el in solList], WPPolygons=[el['actualWPs'] for el in solList], green=green)
        print("Solutions written to html file:", place)

    # Output the costs of all solutions produced so far to the screen
    L = []
    for i in range(len(solList)):
        L.append([round(abs(k-solList[i]["routeLength"])),
                 solList[i]["overlapPercent"]])
    print("Cost of these solutions =")
    print(L)

    # Form the archive set of mutually nondominating solutions and, if selected, optimise it
    archive, archiveCosts = optimisation.optimise(
        solList, k, weight, height, surface, green, travelMode, LSOption, doVis=doVis)
    visRoutes.makeVisualisationFromCoords(
        s, archive, k, travelMode, I, weight, height, surface, place + "Front", green=green)
    print("\nSolutions written to html file:", place + "Front")

    # Stop the clock and output the run time end time
    runTime = time.time() - start
    with open("log.txt", "a") as f:
        f.write(str(archiveCosts) + "\t" + str(runTime) + "\t" + str(runTime -
                config.totalCallTime) + "\t" + str(config.totalNumCalls) + "\n")
    print("\nTotal runtime          =", runTime, "s.")
    print("Runtime without calls  =", runTime-config.totalCallTime, "s.")
    print("Number of calls        =", config.totalNumCalls)


if __name__ == "__main__":
    main()
