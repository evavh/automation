import math

def rgb_to_xy(r, g, b):
    #RGB between 0.0 and 1.0
    r /= 255.0
    g /= 255.0
    b /= 255.0
    
    #Gamma correction
    if r > 0.04045:
        r = ((r+0.055)/(1.0+0.055))**2.4
    else:
        r = r/12.92
    
    if g > 0.04045:
        g = ((g+0.055)/(1.0+0.055))**2.4
    else:
        g = g/12.92
    
    if b > 0.04045:
        b = ((b+0.055)/(1.0+0.055))**2.4
    else:
        b = b/12.92
    
    #Conversion
    x = r*0.664511+g*0.154324+b*0.162028
    y = r*0.283881+g*0.668433+b*0.047685
    Z = r*0.000088+g*0.072310+b*0.986039
    
    x = x / (x + y + Z)
    y = y / (x + y + Z)
    
    bright = int(round(y*255))
    
    return x, y, bright
