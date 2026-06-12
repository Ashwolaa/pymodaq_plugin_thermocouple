#%%
import pandas as pd
import matplotlib.pyplot as plt
import os
path = r'C:\Users\expfemto\Documents\Python\pythermocouple-main'
filename = os.path.join(path,'20260306_temp_vacuum')
df = pd.read_csv(f"{filename}",encoding = "ISO-8859-1")
df['time'] = pd.to_datetime(df['Time (s)'], unit='ms')
plt.figure()
plt.plot(df['time'], df["Temperature 3 (°C)"], label="inside")
plt.plot(df['time'], df["Temperature 4 (°C)"], label="outside")
plt.legend()
plt.show()

# %%
import numpy as np
import matplotlib.pyplot as plt
def n(n0, wavelength, k):
    return n0 + k/wavelength**2

def deg_to_rad(angle):
    return angle/180*np.pi

def rad_to_deg(angle):
    return angle*180/np.pi

def deviation_angle(i,n,phi):
    """i: incident angle (radian)
     phi: prism apex (radian)
       n: refractive index
    """
    offset = np.arcsin(
        n*np.sin(phi-np.arcsin(np.sin(i)/n))
        )
    return i - phi + offset

n_355 = 1.432 # 355 nm
n_118 = 1.7626 # 118 nm

n_355 = 1.3870 # 355 nm
n_118 = 1.64 # 118 nm

phi = deg_to_rad(29.33) # 3.4/3.9 ~ 29.33

i = np.arange(90)

d_118 =deviation_angle(np.deg2rad(i),n_118,phi)
d_355 =deviation_angle(np.deg2rad(i),n_355,phi)

plt.figure()
plt.plot(i,rad_to_deg(d_118),label="118 nm")
plt.plot(i,rad_to_deg(d_355),label="355 nm")
plt.xlabel("Incidence angle (degrees)")
plt.ylabel("Deviation angle (degrees)")
plt.grid(True)
plt.legend()
plt.title(f"n_355={n_355}, n_118={n_118}, phi={phi}")
plt.hlines(27.334,i[0],i[-1])
plt.show()


# %%
