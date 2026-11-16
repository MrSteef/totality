#!/usr/bin/env python3
"""Download NASA POWER August *daytime* cloud climatology and create map overlay.

Run on a network-connected machine: pip install numpy pillow requests; python build_cloud.py
This is a climatological MONTHLY DAYTIME mean, NOT an eclipse-day forecast or
probability of an unobscured sun. The input is NASA CERES-derived CLOUD_AMT_DAY.
"""
import csv
import io
import json
import math
import time
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
from PIL import Image
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
WEST, EAST, SOUTH, NORTH = -52., 68., -8., 45.
# Request in small slices so NASA doesn't have to return an enormous regional result.
TILE_DEG = 10
ENDPOINT = 'https://power.larc.nasa.gov/api/temporal/climatology/regional'
PARAM = 'CLOUD_AMT_DAY'
YEARS = (2005, 2024)


def parse_csv(payload):
    lines = payload.splitlines()
    header_i = next((i for i, l in enumerate(lines) if
                     {'LAT','LON','AUG'} <= {v.strip().upper().strip('"') for v in next(csv.reader([l]))}), None)
    if header_i is None:
        raise ValueError('NASA returned an unknown CSV format; first 600 chars: ' + payload[:600])
    reader = csv.DictReader(io.StringIO('\n'.join(lines[header_i:])))
    records = []
    for row in reader:
        row = {k.strip().upper():v for k, v in row.items() if k}
        try:
            la,lo,val = float(row['LAT']),float(row['LON']),float(row['AUG'])
            if 0 <= val <= 100:
                records.append((la, lo, val))
        except (KeyError, ValueError, TypeError):
            pass
    if not records:
        raise ValueError('No valid August cloud-cover rows in NASA response')
    return records


def download(west, east, south, north, session):
    args = dict(parameters=PARAM, community='RE', format='CSV',
                start=YEARS[0], end=YEARS[1])
    args.update({'latitude-min':south,'latitude-max':north,
                 'longitude-min':west,'longitude-max':east})
    url = ENDPOINT + '?' + urlencode(args)
    for attempt in range(4):
        try:
            res = session.get(url, timeout=100)
            res.raise_for_status()
            return parse_csv(res.text)
        except (requests.RequestException, ValueError) as exc:
            if attempt == 3:raise RuntimeError(f'Failed NASA tile {west},{south}: {exc}') from exc
            time.sleep((attempt+1)*4)


def create_raster(records):
    # NASA's underlying source has ~1-degree native resolution.  Smoothing the
    # display cannot increase the geographic precision of the original data.
    # Create a 1-degree grid, nearest-neighbor assignment to original cells,
    # with bilinear interpolation only for screen visualization.
    lons = np.arange(WEST, EAST+1, 1.,dtype=float)
    lats = np.arange(SOUTH, NORTH+1, 1.,dtype=float)
    grid = np.full((len(lats),len(lons)),np.nan, dtype=float)
    for la,lo,val in records:
        x=round(lo-WEST);y=round(la-SOUTH)
        if 0<=x<len(lons) and 0<=y<len(lats):grid[y,x]=val
    # Fill absent cells only from a nearby supplied source cell, not a fabricated value.
    yy,xx=np.indices(grid.shape)
    good=np.isfinite(grid)
    if good.sum()<100:raise RuntimeError(f'Too few valid NASA cloud grid cells ({good.sum()})')
    from scipy.ndimage import distance_transform_edt
    missing_idx=distance_transform_edt(~good,return_distances=False,return_indices=True)
    grid=np.where(good,grid,grid[tuple(missing_idx)])
    # MapLibre image sources use Mercator-aligned row positions.
    width=2160
    mn=math.log(math.tan(math.pi/4+math.radians(NORTH)/2))
    ms=math.log(math.tan(math.pi/4+math.radians(SOUTH)/2))
    height=round((mn-ms)/math.radians((EAST-WEST)/width))
    ys=mn+(np.arange(height)+0.5)*(ms-mn)/height
    image_lats=np.degrees(2*np.arctan(np.exp(ys))-math.pi/2)
    image_lons=WEST+(np.arange(width)+.5)*(EAST-WEST)/width
    x=np.clip(image_lons-WEST,0,len(lons)-1.0001)
    y=np.clip(image_lats-SOUTH,0,len(lats)-1.0001)
    xi=np.floor(x).astype(int); yi=np.floor(y).astype(int)
    dx=x-xi; dy=y-yi
    a=grid[yi[:,None],xi[None,:]]
    b=grid[yi[:,None],xi[None,:]+1]
    c=grid[yi[:,None]+1,xi[None,:]]
    d=grid[yi[:,None]+1,xi[None,:]+1]
    v=(1-dy[:,None])*((1-dx[None,:])*a+dx[None,:]*b)+dy[:,None]*((1-dx[None,:])*c+dx[None,:]*d)
    # High cloud = neutral purple/gray, low cloud = pale teal.
    stops=np.array([0,20,40,60,80,100],float)
    colors=np.array([[27,136,126],[90,185,166],[186,218,189],[239,217,158],[171,151,167],[90,81,121]],float)
    out=np.zeros((height,width,4),dtype='uint8')
    for channel in range(3):out[:,:,channel]=np.interp(v,stops,colors[:,channel]).astype('uint8')
    out[:,:,3]=190
    Image.fromarray(out,'RGBA').save(DATA/'cloud-august.png',optimize=True)
    (DATA/'cloud-grid.json').write_text(json.dumps({
        'source':'NASA POWER CERES SYN1deg CLOUD_AMT_DAY',
        'period':f'{YEARS[0]}–{YEARS[1]}',
        'month':'August',
        'statistic':'monthly daytime mean cloud fraction, percent',
        'grid':{'west':WEST,'east':EAST,'south':SOUTH,'north':NORTH,'spacingDegrees':1,
                'width':len(lons),'height':len(lats)},
        'values':np.round(grid,1).tolist()
    },separators=(',',':')))
    print(f'Generated cloud-august.png {width}x{height} and cloud-grid.json; source cells {good.sum()}')


def main():
    points={}
    session=requests.Session()
    ranges=[]
    for south in np.arange(SOUTH,NORTH,TILE_DEG):
        for west in np.arange(WEST,EAST,TILE_DEG):
            ranges.append((float(west),float(min(west+TILE_DEG,EAST)),
                           float(south),float(min(south+TILE_DEG,NORTH))))
    for i,(w,e,s,n) in enumerate(ranges,1):
        print(f'{i}/{len(ranges)} NASA POWER: ({w},{s}) to ({e},{n})', flush=True)
        for la,lo,val in download(w,e,s,n,session):
            points[(round(la,2),round(lo,2))]=val
        time.sleep(.35)
    create_raster([(la,lo,v) for (la,lo),v in points.items()])

if __name__=='__main__':main()
