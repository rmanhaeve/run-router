def dominates(newCost, oldCost):
    # Returns true if the newCost vector is seen to dominate the oldCost vector.
    # Assumes all costs are minimisation functions
    betterInOne = False
    for i in range(len(newCost)):
        if newCost[i] < oldCost[i]:
            betterInOne = True
        elif newCost[i] > oldCost[i]:
            return False
    return betterInOne


def worseThan(newCost, oldCost):
    # Returns true if the newCost vector is worse than the the oldCost vector
    # Assumes all costs are minimisation functions
    for i in range(len(newCost)):
        if newCost[i] < oldCost[i]:
            return False
    return True
