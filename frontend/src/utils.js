export const number = (v, digits=0) => v == null ? '—' : new Intl.NumberFormat('en-GB', {maximumFractionDigits:digits,minimumFractionDigits:digits}).format(v);
export const signed = (v, digits=0) => v == null ? '—' : `${v>0?'+':''}${number(v,digits)}`;
export const dateLabel = (v, options={day:'numeric',month:'short',year:'numeric'}) => v ? new Intl.DateTimeFormat('en-GB',{...options,timeZone:'Europe/London'}).format(new Date(v.length===10?`${v}T12:00:00Z`:v)) : '—';
export const timeLabel = v => v ? new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/London',hour12:false}).format(new Date(v)) : '—';
export function linePath(points, key, x, y) {
  let pen=false;
  return points.map((p,i)=>{if(p[key]==null){pen=false;return '';}const cmd=pen?'L':'M';pen=true;return `${cmd}${x(i).toFixed(2)},${y(p[key]).toFixed(2)}`;}).join(' ');
}
export function query(values) {return new URLSearchParams(Object.fromEntries(Object.entries(values).filter(([,v])=>v!==undefined))).toString();}
export function shiftDate(v, delta) {const d=new Date(`${v}T12:00:00Z`);d.setUTCDate(d.getUTCDate()+delta);return d.toISOString().slice(0,10);}
