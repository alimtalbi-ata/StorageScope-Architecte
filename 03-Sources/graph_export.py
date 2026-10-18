"""Portable, escaped SVG/PNG export of visible governance graph. Abdelhalim Talbi."""
from html import escape
from pathlib import Path
from graph_layout import layout_grouped

def _geometry(model):
    if not isinstance(model,dict) or not isinstance(model.get('nodes'),list):raise ValueError('Invalid graph')
    nodes=model['nodes']
    if len(nodes)>10000:raise ValueError('Too many nodes')
    placed,w,h=layout_grouped(nodes,900,3)
    return placed,int(w),int(h)

def export_svg(model,path):
    placed,w,h=_geometry(model)
    title=escape(str(model.get('title','Décision')))
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<rect x="{w/2-130}" y="16" width="260" height="52" rx="8" fill="#dbeafe" stroke="#2563eb"/>',
           f'<text x="{w/2}" y="47" text-anchor="middle" font-family="Arial" font-size="13">{title}</text>']
    for node,x,y in placed:
        kind,identifier,state,critical=node
        lines.append(f'<path d="M {w/2} 68 V 91 H {x:.1f} V {y-24:.1f}" fill="none" stroke="#94a3b8"/>')
    for node,x,y in placed:
        kind,identifier,state,critical=node
        color='#fee2e2' if critical else '#dcfce7' if state in ('DONE','RESOLVED') else '#f1f5f9'
        lines.append(f'<rect x="{x-95:.1f}" y="{y-24:.1f}" width="190" height="48" rx="5" fill="{color}" stroke="#94a3b8"/>')
        lines.append(f'<text x="{x:.1f}" y="{y-6:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{escape(str(kind))} · {escape(str(identifier)[:22])}</text>')
        lines.append(f'<text x="{x:.1f}" y="{y+12:.1f}" text-anchor="middle" font-family="Arial" font-size="10">{escape(str(state))}</text>')
    lines.append('</svg>')
    Path(path).write_text('\n'.join(lines),encoding='utf-8')
    return path

def export_png(model,path):
    try:
        from PIL import Image,ImageDraw
    except ImportError as exc:raise RuntimeError('PNG export requires Pillow') from exc
    placed,w,h=_geometry(model)
    im=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(im)
    cx=w/2
    d.rounded_rectangle((cx-130,16,cx+130,68),radius=8,fill='#dbeafe',outline='#2563eb')
    d.text((cx-120,33),str(model.get('title','Décision'))[:36],fill='#172554')
    for node,x,y in placed:
        d.line([(cx,68),(cx,91),(x,91),(x,y-24)],fill='#94a3b8',width=2)
    for node,x,y in placed:
        kind,identifier,state,critical=node
        color='#fee2e2' if critical else '#dcfce7' if state in ('DONE','RESOLVED') else '#f1f5f9'
        d.rounded_rectangle((x-95,y-24,x+95,y+24),radius=5,fill=color,outline='#94a3b8')
        d.text((x-87,y-16),f'{kind}: {str(identifier)[:17]}',fill='#0f172a')
        d.text((x-87,y+3),str(state)[:25],fill='#475569')
    im.save(path,format='PNG')
    return path
