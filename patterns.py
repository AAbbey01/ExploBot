import re
#import app

google_pattern = r"(spotted)*\s*\(\s*(-?\d+\.?\d+)\s*,\s*(-?\d+\.?\d+)\s*\)"

maps_pattern =r"(spotted)*\d{2}°\d{2}'\d{2}\.\d\"[NS]\s\d{2}°\d{2}'\d{2}\.\d\"[EW]"
app_maps_pattern =r"(spotted)*\(*\d+\.\d+°\s[N],\s\d+\.\d+°\s[W]\)*"

compas_pattern = r"(spotted)*\(*\d{2}\.\d{5}°\s[N],\s\d{2}\.\d{5}°\s[W]\)*"

compas_pattern_2 = r"(spotted)*\d\d°[0-9]+′[0-9]+″\sN\s+[0-9]+°[0-9]+′[0-9]+″\s+W"

def google_to_lat_long(match):
    latitude = float(match.group(2))
    longitude = float(match.group(3))
    longitude = longitude * -1 if longitude > 0 else longitude
    return latitude, longitude

def comp_to_lat_long(match):
    lat_long = match.group(0).split(" ")
    lat = lat_long[0].split("°")
    lat_min = lat[1].split("'")
    lat_sec = lat_min[1].split("\"")
    lat_total = float(lat[0])+float(lat_min[0])/60 + float(lat_sec[0])/3600
    long = lat_long[1].split("°")
    long_min = long[1].split("'")
    long_sec = long_min[1].split("\"")
    long_total = float(long[0])+float(long_min[0])/60+float(long_sec[0])/3600
    long_total = -1 * long_total
    return lat_total, long_total

def app_to_lat_long(match):
    spl = match.group(0).split("° N,")
    lat_st = spl.pop(0)
    lat = lat_st
    lAT= float(lat)
    long_st = spl.pop(0)
    long_st = long_st[1:]
    long_st = long_st[:8]
    long = float(long_st)
    return  lAT, long

def comp_2_to_lat_long(match): 
    lat_long = match.group(0).split("N")
    lat = lat_long[0].split("°")
    lat_min = lat[1].split("′")
    lat_sec = lat_min[1].split(f"\″")
    lat_total = float(lat[0])+float(lat_min[0])/60 + float(lat_sec[0][:1])/3600
    long = lat_long[1].split("°")
    long_min = long[1].split("′")
    long_sec = long_min[1].split("\″")
    long_total = float(long[0])+float(long_min[0])/60+float(long_sec[0][:1])/3600
    long_total = -1 * long_total
    return lat_total, long_total

map_types = ["Google Maps", "Apple Maps", "Compass "]

pattern_types = [google_pattern,app_maps_pattern, compas_pattern_2]
func_types = [google_to_lat_long,app_to_lat_long,comp_2_to_lat_long]

