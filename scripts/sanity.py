import json,sys
for k in ['mon','sun']:
    d=json.load(open(f'data/slate_{k}.json'));P=[p for p in d['players'] if p['elig']]
    print('=====',k,d['type'],'eligible',len(P),'of',len(d['players']))
    for pos in ['QB','RB','WR','TE','DST','K']:
        a=[p for p in P if p['pos']==pos][:12 if k=='sun' else 8]
        if a: print(pos,' | '.join('%s %s $%.1fk %.1f [%.0f-%.0f]'%(p['name'],p['team'],p['sal']/1000,p['proj'],p['floor'],p['ceil']) for p in a))
    print('VALUE',' | '.join('%s $%.1fk %.1f %.2fx'%(p['name'],p['sal']/1000,p['proj'],p['val']) for p in sorted([p for p in P if p['pos']!='DST'],key=lambda p:-p['val'])[:10]))
    if d.get('cpt'): print('CPT',' | '.join('%s %.1f top%.0f%% $%.1fk'%(c['name'],c['proj'],c['top'],c['csal']/1000) for c in d['cpt'][:8]))
    for n in ['James Cook III','Josh Allen','Matthew Stafford','Kyren Williams','Tyler Higbee','Colby Parkinson','Puka Nacua','Davante Adams']:
        x=[p for p in d['players'] if p['name']==n]
        for p in x: print('  ',n,p['sal'],p['proj'],p['floor'],p['ceil'],p['elig'],p.get('why_not'),p['st'],(p.get('usage') or {}).get('ts'),(p.get('usage') or {}).get('cs'),p['edges'][:3])
    print('cascades',json.dumps(d['cascades'])[:600])
    print('inelig sample',[(p['name'],p['why_not']) for p in d['players'] if not p['elig']][:8])
