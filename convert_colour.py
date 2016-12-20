import math

def rgb_to_xy(r, g, b):
    #RGB between 0.0 and 1.0
    r /= 255.0
    g /= 255.0
    b /= 255.0
    
    #Gamma correction
    if r > 0.04045:
        r = ((r+0.055)/(1.055))**2.4
    else:
        r = r/12.92
    
    if g > 0.04045:
        g = ((g+0.055)/(1.055))**2.4
    else:
        g = g/12.92
    
    if b > 0.04045:
        b = ((b+0.055)/(1.055))**2.4
    else:
        b = b/12.92
    
    #Conversion
    x = r*41.24+g*35.76+b*18.05
    y = r*21.26+g*71.52+b*7.22
    z = r*1.93+g*11.92+b*95.05
    
    x = x / (x + y + z)
    y = y / (x + y + z)
    
    bright = int(round(y*255))
    
    return x, y, bright
