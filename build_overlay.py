#!/usr/bin/env python3
"""Generate high-resolution, Web-Mercator-aligned 2027 eclipse totality overlay.

Every PNG pixel is evaluated at its geographic position using the same NASA
Besselian elements as eclipse.mjs. Web Mercator rows are ESSENTIAL because
MapLibre's image source maps the image linearly in projected map coordinates.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
# Keep rectangle broad enough to contain the whole 2027 totality corridor.
WEST, EAST, SOUTH, NORTH = -52.0, 68.0, -8.0, 45.0
PIXELS_PER_DEGREE = 18  # 0.0357° horizontally (~4 km at equator)
WIDTH = round((EAST-WEST)*PIXELS_PER_DEGREE)
RAD = np.pi/180
MERC_N = math.log(math.tan(math.pi/4 + NORTH*RAD/2))
MERC_S = math.log(math.tan(math.pi/4 + SOUTH*RAD/2))
HEIGHT = round((MERC_N-MERC_S)/(RAD/PIXELS_PER_DEGREE))
BATCH_ROWS = 48  # bound peak RAM usage for the full-resolution image

P = {
    'x':(-.019645,.5447105,-.0000444,-.0000091),
    'y':(.160063,-.2111569,-.0001217,.0000037),
    'd':(17.76247,-.010181,-.000004),
    'mu':(328.42249,15.002093),
    'l2':(-.015464,.0000137,-.0000128),
}
COLORS = np.array([[255,215,95],[255,166,66],[247,100,73],
                   [221,63,105],[172,48,131],[91,31,126],[51,24,101]],float)
STOPS = np.array([0,60,120,180,240,300,383.2])

def polynomial(coeff,t):
    out=np.zeros_like(t,dtype=np.float64)
    for c in reversed(coeff): out=out*t+c
    return out

def duration_for_grid(lat,lon):
    u=np.arctan(.99664719*np.tan(lat*RAD))
    rs=.99664719*np.sin(u)
    rc=np.cos(u)
    def contact(t):
        d=polynomial(P['d'],t)*RAD
        h=(polynomial(P['mu'],t)+lon-15.002093*71.7/3600)*RAD
        xi=rc*np.sin(h)
        eta=rs*np.cos(d)-rc*np.sin(d)*np.cos(h)
        zeta=rs*np.sin(d)+rc*np.cos(d)*np.cos(h)
        m=np.hypot(polynomial(P['x'],t)-xi,polynomial(P['y'],t)-eta)
        l2=polynomial(P['l2'],t)-zeta*.0045834
        return m+l2,zeta
    lo=np.full(lat.shape,-3.,float)
    hi=np.full(lat.shape,3.,float)
    for _ in range(25):
        a=lo+(hi-lo)/3; b=hi-(hi-lo)/3
        fa,_=contact(a); fb,_=contact(b)
        take=fa<fb
        hi=np.where(take,b,hi)
        lo=np.where(take,lo,a)
    middle=(lo+hi)/2
    fmin,z=contact(middle)
    mask=(fmin<0)&(z>0)
    start_lo=np.full(lat.shape,-3.)
    start_hi=middle.copy()
    end_lo=middle.copy()
    end_hi=np.full(lat.shape,3.)
    for _ in range(20):
        mid=(start_lo+start_hi)/2
        f,_=contact(mid)
        start_lo=np.where(f>0,mid,start_lo)
        start_hi=np.where(f>0,start_hi,mid)
        mid=(end_lo+end_hi)/2
        f,_=contact(mid)
        end_hi=np.where(f>0,mid,end_hi)
        end_lo=np.where(f>0,end_lo,mid)
    duration=np.maximum(0,(end_lo+end_hi-start_lo-start_hi)*1800)
    return np.where(mask,duration,0)

def pixel_location(lat,lon):
    merc=math.log(math.tan(math.pi/4+lat*RAD/2))
    y=(MERC_N-merc)/(MERC_N-MERC_S)*HEIGHT-.5
    x=(lon-WEST)/(EAST-WEST)*WIDTH-.5
    return round(y),round(x)

def main():
    lon=WEST+(np.arange(WIDTH)+.5)*(EAST-WEST)/WIDTH
    canvas=np.zeros((HEIGHT,WIDTH,4),dtype=np.uint8)
    maxima=(0,None,None)
    for row in range(0,HEIGHT,BATCH_ROWS):
        end=min(HEIGHT,row+BATCH_ROWS)
        yy=MERC_N+(np.arange(row,end)+.5)*(MERC_S-MERC_N)/HEIGHT
        lat=(2*np.arctan(np.exp(yy))-np.pi/2)/RAD
        latgrid,longrid=np.broadcast_arrays(lat[:,None],lon[None,:])
        seconds=duration_for_grid(latgrid,longrid)
        for i in range(3): canvas[row:end,:,i]=np.interp(seconds,STOPS,COLORS[:,i]).astype('uint8')
        # Pixels outside totality are fully transparent, including the color channels.
        canvas[row:end,:,3]=np.where(seconds>0,230,0).astype('uint8')
        canvas[row:end,:,:3]=np.where((seconds>0)[:,:,None],canvas[row:end,:,:3],0)
        idx=np.unravel_index(seconds.argmax(),seconds.shape)
        if seconds[idx]>maxima[0]: maxima=(float(seconds[idx]),float(latgrid[idx]),float(longrid[idx]))
    output=ROOT/'data'/'duration.png'
    output.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(canvas,'RGBA').save(output,optimize=True)
    print(f'Web Mercator PNG {WIDTH}x{HEIGHT} saved to {output} ({output.stat().st_size/1024:.0f} KiB)')
    print(f'Maximum predicted totality: {maxima[0]:.1f}s near {maxima[1]:.4f}N {maxima[2]:.4f}E')
    for name,la,ln in [('Luxor',25.6872,32.6396),('Cairo',30.0444,31.2357),('Tarifa',36.013,-5.605),('Madrid',40.4168,-3.7038),('Jeddah',21.5433,39.1728)]:
        y,x=pixel_location(la,ln)
        # Independently evaluate at real coordinates, not a sample from a color.
        precise=duration_for_grid(np.array([[la]]),np.array([[ln]]))[0,0]
        print(f'{name:8} {precise:6.1f}s  PNG pixel ({x},{y}), RGBA={canvas[y,x].tolist()}')
    # Regression guard: Cairo must NOT show the colored overlay. Luxor MUST.
    ly,lx=pixel_location(25.6872,32.6396)
    cy,cx=pixel_location(30.0444,31.2357)
    assert canvas[ly,lx,3]>0 and canvas[cy,cx,3]==0, 'Overlay alignment regression'

if __name__=='__main__':main()
