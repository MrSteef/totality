// Computed from the Besselian elements for 2 Aug 2027 published by Fred Espenak / NASA GSFC.
// Reference: https://eclipse.gsfc.nasa.gov/SEbeselm/SEbeselm2001/SE2027Aug02Tbeselm.html
// Accuracy: smooth-Moon, standard astronomical prediction; not a lunar-limb/topography model.
const R = Math.PI / 180;
const poly = (coeff,t) => coeff.reduceRight((sum,c)=>sum*t+c,0);
const E = {
  x:[-0.019645,0.5447105,-0.0000444,-0.0000091],
  y:[0.160063,-0.2111569,-0.0001217,0.0000037],
  d:[17.76247,-0.010181,-0.000004],
  mu:[328.42249,15.002093],
  l2:[-0.015464,0.0000137,-0.0000128]
};
function geometry(lat, lon, t) {
  const phi = lat*R;
  const u = Math.atan(0.99664719*Math.tan(phi));
  const rs = 0.99664719*Math.sin(u), rc = Math.cos(u);
  const d = poly(E.d,t)*R, H=(poly(E.mu,t)+lon-15.002093*71.7/3600)*R;
  const xi = rc*Math.sin(H);
  const eta = rs*Math.cos(d)-rc*Math.sin(d)*Math.cos(H);
  const zeta = rs*Math.sin(d)+rc*Math.cos(d)*Math.cos(H);
  const m = Math.hypot(poly(E.x,t)-xi,poly(E.y,t)-eta);
  const l2p = poly(E.l2,t)-zeta*0.0045834;
  return {contact:m+l2p, altitude:Math.asin(Math.max(-1,Math.min(1,zeta)))/R};
}
function utFromT(t) {return 10+t-71.7/3600;}
function utcClock(t) {
  const sec=Math.round(utFromT(t)*3600);
  return `${String(Math.floor(sec/3600)%24).padStart(2,'0')}:${String(Math.floor((sec%3600)/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')} UTC`;
}
export function eclipseAt(lat,lon) {
  if (!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180) return null;
  // Correct tabulated ephemeris hour angle for ΔT (Earth rotates during TT−UT).
  // Minimize signed distance to local umbral boundary within published 7–13 TD range.
  let left=-3,right=3;
  for(let i=0;i<45;i++) {
    const a=left+(right-left)/3,b=right-(right-left)/3;
    if(geometry(lat,lon,a).contact < geometry(lat,lon,b).contact) right=b;
    else left=a;
  }
  const tMid=(left+right)/2, peak=geometry(lat,lon,tMid);
  if(peak.contact>=0 || peak.altitude<=0) return {total:false,durationSeconds:0,altitude:peak.altitude};
  const fLeft=geometry(lat,lon,-3).contact, fRight=geometry(lat,lon,3).contact;
  if(fLeft<=0||fRight<=0) return {total:false,durationSeconds:0,altitude:peak.altitude};
  function root(a,b,enter) {
    for(let i=0;i<38;i++) {
      const m=(a+b)/2, f=geometry(lat,lon,m).contact;
      if (enter ? f>0 : f<0) a=m; else b=m;
    }
    return (a+b)/2;
  }
  const c2=root(-3,tMid,true), c3=root(tMid,3,false);
  // Totality cannot be observed if the Sun is geometrically below the horizon.
  const duration=Math.max(0,(c3-c2)*3600);
  return {total:duration>0,durationSeconds:duration,c2UTC:utcClock(c2),c3UTC:utcClock(c3),altitude:peak.altitude};
}
export function formatDuration(seconds){let s=Math.round(seconds);return `${Math.floor(s/60)}m ${String(s%60).padStart(2,'0')}s`;}
