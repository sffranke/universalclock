def getoi():
    t = get_local_time()
    hour = t[3]
    print(hour)
    if 6 <= hour < 12:
        return "BOM DIA!"
    elif 12 <= hour < 18:
        return "BOA TARDE!"
    else:
        return "BOA NOITE"
