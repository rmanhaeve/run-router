import sys

# ***********************
# Global constant that specifies the user key for openrouteservice. Please replace this by your own key
ORSKEY = "5b3ce3597851110001cf6248e01b10cd3a444e1eb14a509d3d20aa75"

# Global constant that gives the maximum number of requests permitted in a single call to openrouteservice directions.
MAXWP = 50

# Global variable for recording total time consumed by API calls
totalCallTime = 0

# Global variable for recording total number of API calls made
totalNumCalls = 0


def myQuit(s):
    # Global function for quitting and outputting some information to a log file (followed by a newline)
    print(s)
    with open("log.txt", "a") as f:
        f.write(s + "\n")
    sys.exit(1)
