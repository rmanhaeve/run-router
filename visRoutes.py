import distance
import config
import networkx as nx
import matplotlib.pyplot as plt

rVal = [255, 0, 0, 255, 255, 0, 0, 128, 0, 0, 128, 128, 0, 128, 192, 0, 0, 192, 192, 0, 192, 64, 0, 0, 64, 64, 0,
    64, 32, 0, 0, 32, 32, 0, 32, 96, 0, 0, 96, 96, 0, 96, 160, 0, 0, 160, 160, 0, 160, 224, 0, 0, 224, 224, 0, 224]
gVal = [0, 255, 0, 255, 0, 255, 0, 0, 128, 0, 128, 0, 128, 128, 0, 192, 0, 192, 0, 192, 192, 0, 64, 0, 64, 0, 64,
    64, 0, 32, 0, 32, 0, 32, 32, 0, 96, 0, 96, 0, 96, 96, 0, 160, 0, 160, 0, 160, 160, 0, 224, 0, 224, 0, 224, 224]
bVal = [0, 0, 255, 0, 255, 255, 0, 0, 0, 128, 0, 128, 128, 128, 0, 0, 192, 0, 192, 192, 192, 0, 0, 64, 0, 64, 64,
    64, 0, 0, 32, 0, 32, 32, 32, 0, 0, 96, 0, 96, 96, 96, 0, 0, 160, 0, 160, 160, 160, 0, 0, 224, 0, 224, 224, 224]


def visualiseRGraph(R):
    #Build a NetworkX multi-digraph graph using the route set R and draw it to the screen
    G = nx.MultiDiGraph()
    for i in range(len(R)):
        for j in range(len(R[i])-1):
            G.add_node(R[i][j], pos=(R[i][j][0], R[i][j][1]))
            G.add_node(R[i][j+1], pos=(R[i][j+1][0], R[i][j+1][1]))
            G.add_edge(R[i][j], R[i][j+1])
    nx.draw_networkx(G, pos=nx.get_node_attributes(
        G, "pos"), node_size=10, with_labels=False)
    plt.show()


def visualiseSmoothGraph(smoothGraph, numToCoords, W):
    #Build a NetworkX weighted digraph graph using smoothed graph and draw it to the screen
    G = nx.DiGraph()
    for u in smoothGraph:
        G.add_node(u, pos=(numToCoords[u][0], numToCoords[u][1]))
    for u in smoothGraph:
        for v in smoothGraph[u]:
            G.add_edge(u, v, weight=W[(u, v)])
    edge_labels = dict([((u, v,), round(d['weight']))
                       for u, v, d in G.edges(data=True)])
    nx.draw_networkx(G, pos=nx.get_node_attributes(G, "pos"),
                     node_size=75, with_labels=True, font_size=8)
    nx.draw_networkx_edge_labels(G, pos=nx.get_node_attributes(
        G, "pos"), edge_labels=edge_labels, font_size=8)
    plt.show()


def makeVisualisationOfSource(source: [],
                              travelMode: int,
                              desiredLength: int,
                              outFile: str = "Output",
                              isochrone=None):
    #This procedure plots the source to an an interactive html visualisation using BingMaps. The program also
    #plots the isochrone if specified
    with open(outFile + ".html", "w") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <style> #solMap {width: 100%; height: 700px;} </style>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map;
        function GetSolMap(){

            map = L.map('solMap');
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors'}).addTo(map);

            // Set up variables and define icons to use
            var schIcon = L.icon({iconUrl: "https://www.rhydlewis.eu/icons/schNode.png", iconAnchor: [8, 8]});
            var allLocations = new Array();
            var pin, A, pgon;

        """)
        f.write("\t// Add the start point\n")
        f.write("\t\t\tpin = L.marker([" + str(source[1]) + ", " + str(source[0]) + "], {icon: schIcon}).addTo(map).bindPopup(\"<b>Starting Point</b>\");\n") 
        f.write("\t\t\tallLocations.push([" + str(source[1]) + ", " + str(source[0]) + "]);\n");
        if isochrone is not None:
            f.write("\n\t\t\t//Set up isochrone\n")
            route = [[wp[1], wp[0]] for wp in isochrone]
            f.write("\t\t\tA" + " = " + str(route) + ";\n")
            f.write("\t\t\tL.polygon(A, { fillColor: \"rgb(169,169,169)\", fillOpacity: 0.75, color:\"black\", weight: 1}).addTo(map);\n")
            f.write("\t\t\tfor (let coord of A) allLocations.push(coord);\n")
        f.write("""
            //Zoom the map to fit the polyline
            map.fitBounds(L.polyline(allLocations).getBounds());
                        
            //Add a click event to the map to display lat-long coords
            map.on('click', function (e) { document.getElementById("textBox").value = `${e.latlng.lat}, ${e.latlng.lng}` });    
        }
        """)
        f.write("\t</script>\n\n")
        #Output elevation and surface profiles of each route
        f.write("<title>\n")
        if travelMode == 1:
            x = " (driving-car)"
        elif travelMode == 2:
            x = " (cycling-regular)"
        else:
            x = " (foot-walking)"
        f.write(outFile + "\n")
        f.write("</title>\n")
        f.write("</head>\n\n")
        f.write("<body onload = \"GetSolMap();\">\n")
        f.write("<h2>" + outFile + x + ". Desired Length = " + str(desiredLength) + " m.</h2>\n")
        f.write("<div id = \'solMap\' style = \"position:relative; width:90vw; height:80vh;\"></div><br>\n")
        f.write("<b>Click the map to display the Lat / Long coordinates.</b> <input id = \'textBox\' type = \"text\" style = \"width:300px;\"/>\n")
        f.write("<hr>\n")
        f.write("\n\n</body>\n")
        f.write("\n\n</html>\n")


def makeVisualisationFromCoords(source, routes, desiredLength, travelMode, isochrone, weight, height, surface, outFile, polygons=None, green=None, WPPolygons=None):
    #Each element of R is a list of (x,y) coordinates defining a route on a map. This procedure puts them into into an
    #interactive html visualisation using the Leaflet javascript library. The program also outputs the surface and heights along the route using Google Charts.
    #Polygons, wayPointPolygons, and isochrones are optional. Each element of these is a list of (x,y) coordinates that defines a polygon.
    #Here is a list of surface types
    #0 Unknown, 1 Paved, 2 Unpaved, 3 Asphalt, 4 Concrete, 5 Cobblestone, 6 Metal,
    #7 Wood, 8 Compacted Gravel, 9 Fine Gravel, 10 Gravel, 11 Dirt, 12 Ground, 13 Ice,
    #14 Paving Stones, 15 Sand, 16 Woodchips, 17 Grass, 18 Grass Paver
    #These are divided into paved (grey), unpaved (green), and yellow (unknown)
    #First determine the min and max height for use with the chart scales
    allHeights = height.values()
    minHeight = min(allHeights)
    maxHeight = max(minHeight + 10, max(allHeights))
    amountClimbed = []
    amountPaved = []
    overlapPercent = []
    #Distances stores the cumulative distances along each route
    distances = [[0] for i in range(len(routes))]
    with open(outFile + ".html", "w") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <style> #solMap {width: 100%; height: 700px;} </style>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://www.gstatic.com/charts/loader.js"></script>
    <script>
        // Global variables (used for interactivity)
        var curvyPLines, allPolygons, allWPPolygons, allIsochrones, map;
        function GetSolMap(){

            //Assign values/types to global variables
            curvyPLines = new Array();
            allPolygons = new Array();
            allWPPolygons = new Array();
            allIsochrones = new Array();
            map = L.map('solMap');

            // Show the map
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors'}).addTo(map);

            // Set up variables and define icons to use
            var schIcon = L.icon({iconUrl: "https://www.rhydlewis.eu/icons/schNode.png", iconAnchor: [8, 8]});
            var allLocations = new Array();
            var pin, pLine, pgon, A;

        """)
        f.write("\t// Add the start point\n")
        f.write("\t\t\tpin = L.marker([" + str(source[1]) + ", " + str(source[0]) + "], {icon: schIcon}).addTo(map).bindPopup(\"<b>Starting Point</b><br>Your route starts here.\");\n") 
        f.write("\t\t\tallLocations.push([" + str(source[1]) + ", " + str(source[0]) + "]);\n");

        for i in range(len(routes)):
            for j in range(1, len(routes[i])):
                distances[i].append(distances[i][-1] + weight[(routes[i][j-1], routes[i][j])])
            f.write("\n\t\t\t//Set up polyline for Route " + str(i) + "\n")
            route = [[wp[1], wp[0]] for wp in routes[i]]
            f.write("\t\t\tA" + " = " + str(route) + ";\n")
            f.write("\t\t\tpLine = L.polyline(A, { color: \"rgb(" + str(rVal[i % len(rVal)]) + "," + str(gVal[i % len(gVal)]) + "," + str(bVal[i % len(bVal)]) + ")\", weight: 3}).bindPopup(\"<b>Route " + str(i+1) + "</b><br>Length = " + str(round(distances[i][-1])) + " m\");\n")
            f.write("\t\t\tcurvyPLines.push(pLine);\n") 
            f.write("\t\t\tfor (let coord of A) allLocations.push(coord);\n")
            
        if polygons is not None:
            for i in range(len(polygons)):
                f.write("\n\t\t\t//Set up polygon " + str(i) + "\n")
                route = [[wp[1], wp[0]] for wp in polygons[i]]
                f.write("\t\t\tA" + " = " + str(route) + ";\n")
                f.write("\t\t\tpgon = L.polygon(A, { color: \"rgb(" + str(rVal[i % len(rVal)]) + "," + str(gVal[i % len(gVal)]) + "," + str(bVal[i % len(bVal)]) + ")\", opacity: 0.3, weight: 0});\n")
                f.write("\t\t\tallPolygons.push(pgon);\n")
                f.write("\t\t\tfor (let coord of A) allLocations.push(coord);\n")
        
        if WPPolygons is not None:
            for i in range(len(WPPolygons)):
                f.write("\n\t\t\t//Set up waypointpolygon " + str(i) + "\n")
                route = [[wp[1], wp[0]] for wp in WPPolygons[i]]
                f.write("\t\t\tA" + " = " + str(route) + ";\n")
                f.write("\t\t\tpgon = L.polygon(A, { color: \"rgb(" + str(rVal[i % len(rVal)]) + "," + str(gVal[i % len(gVal)]) + "," + str(bVal[i % len(bVal)]) + ")\", opacity: 0.5, weight: 1});\n")
                f.write("\t\t\tallWPPolygons.push(pgon);\n")
                f.write("\t\t\tfor (let coord of A) allLocations.push(coord);\n")
        
        f.write("\n\t\t\t//Set up isochrone\n")
        route = [[wp[1], wp[0]] for wp in isochrone]
        f.write("\t\t\tA" + " = " + str(route) + ";\n")
        f.write("\t\t\tpgon = L.polygon(A, { color: \"rgb(169,169,169)\", opacity: 0.75, weight: 0});\n")
        f.write("\t\t\tallIsochrones.push(pgon);\n")
        f.write("\t\t\tfor (let coord of A) allLocations.push(coord);\n")
        
        f.write("""
            //Zoom the map to fit the polyline
            map.fitBounds(L.polyline(allLocations).getBounds());
            
            //Display all routes on opening
            for (let pLine of curvyPLines) pLine.addTo(map);
            
            //Add a click event to the map to display lat-long coords
            map.on('click', function (e) { document.getElementById("textBox").value = `${e.latlng.lat}, ${e.latlng.lng}` });    
        }
        """)
        
        f.write("function checkAllRoutes() {\n")
        for i in range(len(routes)):
            f.write("\t\t\tdocument.getElementById(\"myCheckRoute" + str(i+1) + "\").checked = true;\n")
        f.write("\t\t\trefreshRoutes();\n")
        f.write("\t\t}\n")
        f.write("\t\tfunction invertSelectionRoutes() {\n")
        for i in range(len(routes)):
            f.write("\t\t\tif(document.getElementById(\"myCheckRoute" + str(i+1) + "\").checked == true) document.getElementById(\"myCheckRoute" + str(i+1) + "\").checked = false; else document.getElementById(\"myCheckRoute" + str(i+1) + "\").checked = true;\n")
        f.write("\t\t\trefreshRoutes();\n")
        f.write("\t\t}\n")
        f.write("\t\tfunction refreshRoutes() {\n")
        for i in range(len(routes)):
            f.write("\t\t\tif (document.getElementById(\"myCheckRoute" + str(i+1) + "\").checked == true) curvyPLines[" + str(i) + "].addTo(map); else map.removeLayer(curvyPLines[" + str(i) + "]);\n")
        f.write("\t\t}\n")
        
        if polygons is not None:
            f.write("\t\tfunction checkAllPolygons() {\n")
            for i in range(len(polygons)):
                f.write("\t\t\tdocument.getElementById(\"myCheckPolygon" + str(i+1) + "\").checked = true;\n")
            f.write("\t\t\trefreshPolygons();\n")
            f.write("\t\t}\n")
            f.write("\t\tfunction invertSelectionPolygons() {\n")
            for i in range(len(polygons)):
                f.write("\t\t\tif(document.getElementById(\"myCheckPolygon" + str(i+1) + "\").checked == true) document.getElementById(\"myCheckPolygon" + str(i+1) + "\").checked = false; else document.getElementById(\"myCheckPolygon" + str(i+1) + "\").checked = true;\n")
            f.write("\t\t\trefreshPolygons();\n")
            f.write("\t\t}\n")
            f.write("\t\tfunction refreshPolygons() {\n")
            for i in range(len(polygons)):
                f.write("\t\t\tif(document.getElementById(\"myCheckPolygon" + str(i+1) + "\").checked == true) allPolygons[" + str(i) + "].addTo(map); else map.removeLayer(allPolygons[" + str(i) + "]);\n")
            f.write("\t\t}\n")
        if WPPolygons is not None:
            f.write("\t\tfunction checkAllWPPolygons() {\n")
            for i in range(len(WPPolygons)):
                f.write("\t\t\tdocument.getElementById(\"myCheckWPPolygon" + str(i+1) + "\").checked = true;\n")
            f.write("\t\t\trefreshWPPolygons();\n")
            f.write("\t\t}\n")
            f.write("\t\tfunction invertSelectionWPPolygons() {\n")
            for i in range(len(WPPolygons)):
                f.write("\t\t\tif(document.getElementById(\"myCheckWPPolygon" + str(i+1) + "\").checked == true) document.getElementById(\"myCheckWPPolygon" + str(i+1) + "\").checked = false; else document.getElementById(\"myCheckWPPolygon" + str(i+1) + "\").checked = true;\n")
            f.write("\t\t\trefreshWPPolygons();\n")
            f.write("\t\t}\n")
            f.write("\t\tfunction refreshWPPolygons() {\n")
            for i in range(len(WPPolygons)):
                f.write("\t\t\tif(document.getElementById(\"myCheckWPPolygon" + str(i+1) + "\").checked == true) allWPPolygons[" + str(i) + "].addTo(map); else map.removeLayer(allWPPolygons[" + str(i) + "]);\n")
            f.write("\t\t}\n")
        f.write("\t\tfunction refreshIsochrone() {\n")
        f.write("\t\t\tif(document.getElementById(\"myCheckIsochrone\").checked == true) allIsochrones[0].addTo(map); else map.removeLayer(allIsochrones[0]);\n")
        f.write("\t\t}\n")
        f.write("\t</script>\n\n")
        #Output elevation and surface profiles of each route
        f.write("\t<script>\n")
        f.write("\t\tgoogle.charts.load('current', {'packages':['corechart']});\n")
        for i in range(len(routes)):
            #Calculate amount climbed in route i and percentage offroad
            climbed = 0
            pavedDist = 0
            for j in range(len(routes[i])-1):
                if height[routes[i][j]] < height[routes[i][j+1]]:
                    climbed += height[routes[i][j+1]] - height[routes[i][j]]
                edgesurface = surface[(routes[i][j], routes[i][j+1])]
                if edgesurface == 1 or edgesurface == 3 or edgesurface == 4 or edgesurface == 5 or edgesurface == 6 or edgesurface == 14 or edgesurface == 18:
                    pavedDist += weight[(routes[i][j], routes[i][j+1])]
            amountClimbed.append(climbed)
            amountPaved.append(pavedDist)
            #Calculate overlap percentage of route
            totalOverlapLen = distance.getOverlapDistOrigGraph(routes[i], weight)
            totalLen = distance.GPSCrowPathDist(routes[i], weight)
            overlapPercent.append((totalOverlapLen / totalLen) * 100)
            f.write("\t\tgoogle.charts.setOnLoadCallback(drawChart" + str(i) + ");\n")
            f.write("\t\tfunction drawChart" + str(i) + "() {\n")
            f.write("\t\t\tvar data = google.visualization.arrayToDataTable(")
            L = [["m", "Height", "Surface"]]
            L.append([distances[i][0], height[routes[i][0]], 1])
            for j in range(1, len(routes[i])):
                L.append([distances[i][j], height[routes[i][j]],
                         surface[(routes[i][j-1], routes[i][j])]])
            f.write("\t" + str(L) + ");\n")
            f.write("\t\t\tvar options = {title: \'Route Profile (Grey = Paved; Green = Unpaved; Yellow = Unknown)\', legend: 'none', lineWidth: 10, enableInteractivity: false,backgroundColor: {fill: 'transparent'}, curveType: 'function', hAxis: {title:'Distance (m)'},vAxis: {minValue: " + str(minHeight) + ", maxValue: " + str(maxHeight) + ",title: 'Height'}};\n")
            f.write("\t\t\tvar dataView = new google.visualization.DataView(data);\n")
            f.write("\t\t\tdataView.setColumns([0,{calc: function(data, row) {return data.getValue(row, 1);},type: 'number'},{calc: function(data, row) {var surface =data.getValue(row, 2); if (surface == 1 || surface == 3 || surface == 4 || surface == 5 || surface == 6 || surface == 14 || surface ==  18) return '#808080'; else if (surface == 0) return '#FFFF00'; else return '#7CFC00';}, type: 'string', role: 'style'}]);\n")
            f.write("\t\t\tvar chart" + str(i) + " = new google.visualization.LineChart(document.getElementById(\'curve_chart" + str(i) + "\'));\n")
            f.write("\t\t\tchart" + str(i) + ".draw(dataView, options);\n")
            f.write("\t\t}\n")
        f.write("\t</script>\n")
        if green is not None and travelMode == 3:
            #Also output information on the greenness of a route
            f.write("\t<script>\n")
            f.write("\t\tgoogle.charts.load('current', {'packages':['corechart']});\n")
            for i in range(len(routes)):
                f.write("\t\tgoogle.charts.setOnLoadCallback(drawGreenChart" + str(i) + ");\n")
                f.write("\t\tfunction drawGreenChart" + str(i) + "() {\n")
                f.write("\t\t\tvar data = google.visualization.arrayToDataTable(")
                L = [["m", "Null", "Green"]]
                L.append([distances[i][0], 1, 5])
                for j in range(1, len(routes[i])):
                    L.append([distances[i][j], 1, green[(routes[i][j-1], routes[i][j])]])
                f.write("\t" + str(L) + ");\n")
                f.write("\t\t\tvar options = {title: 'Greenery Profile (Green = Maximum green space; Grey = Minimum green space). Warning: Only seems to work for Germany', legend: 'none', lineWidth: 120, enableInteractivity: false, backgroundColor: {fill: 'transparent'}, curveType: 'function', hAxis: {title:'Distance (m)'}, vAxis: { textPosition: 'none' }};\n")
                f.write("\t\t\tvar dataView = new google.visualization.DataView(data);\n")
                f.write("\t\t\tdataView.setColumns([0,{calc: function(data, row) {return data.getValue(row, 1);},type: 'number'},{calc: function(data, row) {var Green =data.getValue(row, 2); if (Green == 10) return '#00ff00'; else if (Green == 9) return '#3af22a'; else if (Green == 8) return '#50e53c'; else if (Green == 7) return '#5ed949'; else if (Green == 6) return '#69cc54'; else if (Green == 5) return '#70bf5d'; else if (Green == 4) return '#76b366'; else if (Green == 3) return '#7aa66d'; else if (Green == 2) return '#7d9974'; else if (Green == 1) return '#7f8d7a'; else return '#808080';}, type: 'string', role: 'style'}]);\n")
                f.write("\t\t\tvar greenchart" + str(i) + " = new google.visualization.LineChart(document.getElementById('green_curve_chart" + str(i) + "'));\n")
                f.write("\t\t\tgreenchart" + str(i) + ".draw(dataView, options);\n")
                f.write("\t\t}\n")
            f.write("\t</script>\n")
        f.write("<title>\n")
        if travelMode == 1:
            x = " (driving-car)"
        elif travelMode == 2:
            x = " (cycling-regular)"
        else:
            x = " (foot-walking)"
        f.write(outFile + "\n")
        f.write("</title>\n")
        f.write("</head>\n\n")
        f.write("<body onload = \"GetSolMap();\">\n")
        f.write("<h2>" + outFile + x + ". Desired Length = " + str(desiredLength) + " m.</h2>\n")
        f.write("<div id = \'solMap\' style = \"position:relative; width:90vw; height:80vh;\"></div><br>\n")
        f.write("<b>Click the map to display the Lat / Long coordinates.</b> <input id = \'textBox\' type = \"text\" style = \"width:300px;\">")
        if len(routes) != 0:
            f.write("<br><b>Show Routes:</b>\n")
            for i in range(len(routes)):
                f.write(str(i+1) + "<input type = \"checkbox\" id = \"myCheckRoute" + str(i+1) + "\" onclick = \"refreshRoutes()\" checked=\"checked\">\n")
            f.write(" | <button onclick = \"checkAllRoutes()\">Select All</button>\n")
            f.write("<button onclick = \"invertSelectionRoutes()\">Invert Selection</button>\n")
        if polygons is not None:
            f.write("<br><b>Show Polygs: </b>")
            for i in range(len(polygons)):
                f.write(str(i+1) + "<input type = \"checkbox\" id = \"myCheckPolygon" + str(i+1) + "\" onclick = \"refreshPolygons()\">\n")
            f.write(" | <button onclick = \"checkAllPolygons()\">Select All</button>\n")
            f.write(
                "<button onclick = \"invertSelectionPolygons()\">Invert Selection</button>\n")
        if WPPolygons is not None:
            f.write("<br><b>Show WayPs: </b>")
            for i in range(len(WPPolygons)):
                f.write(str(i+1) + "<input type = \"checkbox\" id = \"myCheckWPPolygon" + str(i+1) + "\" onclick = \"refreshWPPolygons()\">\n")
            f.write(" | <button onclick = \"checkAllWPPolygons()\">Select All</button>\n")
            f.write(
                "<button onclick = \"invertSelectionWPPolygons()\">Invert Selection</button>\n")
        f.write("<br><b>Show Isochr: </b>")
        f.write(" <input type = \"checkbox\" id = \"myCheckIsochrone\" onclick = \"refreshIsochrone()\">\n")
        f.write("<hr>\n")
        for i in range(len(routes)):
            f.write("\n<h2>Route " + str(i+1) + " (Length = " + str(round(distances[i][-1])) + " m; Overlap = " + str(round(overlapPercent[i])) + "%; Amount climbed = " + str(round(amountClimbed[i])) + " m; Amount known to be paved = " + str(round(amountPaved[i])) + " m).</h2>\n")
            f.write("<div id=\"curve_chart" + str(i) + \
                    "\" style=\"width:90vw; height:40vh\"></div>\n")
            if green is not None and travelMode == 3:
                f.write("<div id=\"green_curve_chart" + str(i) + "\" style=\"width:90vw; height:40vh\"></div>\n")
            f.write("<hr>\n")
        f.write("\n</body>\n")
        f.write("</html>\n")
