import math

def rgb_to_xy(R, G, B):
    #RGB between 0.0 and 1.0
    R /= 255.0
    G /= 255.0
    B /= 255.0
    
    #Gamma correction
    if R > 0.04045:
        R = ((R+0.055)/(1.0+0.055))**2.4
    else:
        R = R/12.92
    
    if G > 0.04045:
        G = ((G+0.055)/(1.0+0.055))**2.4
    else:
        G = G/12.92
    
    if B > 0.04045:
        B = ((B+0.055)/(1.0+0.055))**2.4
    else:
        B = B/12.92
    
    #Conversion
    X = R*0.664511+G*0.154324+B*0.162028
    Y = R*0.283881+G*0.668433+B*0.047685
    Z = R*0.000088+G*0.072310+B*0.986039
    
    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)
    
    brightness = int(round(Y*255))
    
    return (x, y, brightness)

def xy_to_rgb(x, y, brightness):
    z = 1.0 - x - y
    Y = brightness
    X = (Y / y) * x
    Z = (Y / y) * z
    
    #Conversion
    R =  X * 1.656492 - Y * 0.354851 - Z * 0.255038
    G = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
    B =  X * 0.051713 - Y * 0.121364 + Z * 1.011530
    
    #Reverse gamma correction
    if R <= 0.0031308:
        R = 12.92 * R
    else:
        R = (1.0 + 0.055) * R**(1.0 / 2.4) - 0.055
    
    if G <= 0.0031308:
        G = 12.92 * G
    else:
        G = (1.0 + 0.055) * G**(1.0 / 2.4) - 0.055
    
    if B <= 0.0031308:
        B = 12.92 * B
    else:
        B = (1.0 + 0.055) * B**(1.0 / 2.4) - 0.055
    
    R *= 255.0
    G *= 255.0
    B *= 255.0
    
    return (R, G, B)

def temp_to_rgb(temperature):
    
    temperature /= 100
    
    if temperature <= 66:
        R = 255
    else:
        R = temperature - 60
        R = 329.698727446 * (R**-0.1332047592)
        if R < 0:
            R = 0
        if R > 255:
            R= 255
    
    if temperature <= 66:
        G = temperature
        G = 99.4708025861 * math.log(G) - 161.1195681661
        if G < 0:
            G = 0
        if G > 255:
            G = 255
    else:
        G = temperature - 60
        G = 288.1221695283 * (G**-0.0755148492)
        if G < 0:
            G = 0
        if G > 255:
            G = 255
    
    if temperature >= 66:
        B = 255
    else:
        if temperature <= 19:
            B = 0
        else:
            B = temperature - 10
            B = 138.5177312231 * math.log(B) - 305.0447927307
            if B < 0:
                B = 0
            if B > 255:
                B = 255 
    
    return (R, G, B)

def rgb_to_temp(R, G, B):
    if R > B:
        if G > R:
            return None
        else:
            G = G / R * 255
            B = B / R * 255
            R = 255
    elif B > R:
        if G > B:
            return None
        else:
            G = G / B * 255
            R = R / B * 255
            B = 255
    else:
        if G > R:
            return None
        else:
            G = G / R * 255
            R = 255
            B = 255
    
    if R != 255: #above 6600 red is useful
        return int(round(((R/329.698727446)**(1.0/-0.1332047592) + 60)*100))
    elif B != 255: #under 6600 we use green
        return int(round(math.exp(((G+161.1195681661)/99.4708025861))*100))
    else: #if R and B are both 255, we are at 6600
        return 6600
