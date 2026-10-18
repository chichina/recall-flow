"""Real genanki APKG and identity-first UTF-8 TSV. No scheduling synchronization."""
import base64
import csv
import html
import itertools
from pathlib import Path
import time
from common import atomic,load,require,sha,write_immutable

def fixed_id(identity):return 1_000_000_000+int(sha(identity.encode())[:8],16)%1_000_000_000
def escaped(text):return html.escape(text,quote=True).replace('\n','<br>')

def export(root,pack,out,tsv_only=False):
    genanki=None
    if not tsv_only:
        try:import genanki
        except ImportError as e:raise ValueError('APKG needs genanki==0.13.1; install requirements.txt or use --tsv-only') from e
    out=Path(out).resolve(); require(not out.exists(),'Anki output already exists; choose a new directory')
    media={a['filename']:a for s in pack['sources'] for a in s['attachments']}
    used={name for card in pack['cards'] for name in card['media']}
    registry_path=Path(root)/'anki-identity.json'
    registry=load(registry_path) if registry_path.exists() else {'notes':{},'next_id':int(time.time()*1000)}
    out.mkdir(parents=True)
    media_paths=[]
    for name in sorted(used):
        item=media[name]; raw=base64.b64decode(item['data_base64'],validate=True)
        target=out/'media'/name;write_immutable(target,raw);media_paths.append(str(target))
    sources={s['source_id']:s for s in pack['sources']}
    rows={'basic':[],'cloze':[]};counts={'basic':0,'cloze':0}
    for c in pack['cards']:
        uid=pack['pack_id']+':'+c['note_id']
        front=escaped(c['front'])+''.join('<br><img src="'+name+'">' for name in c['media'])
        back=escaped(c['back'])
        citation='<br>'.join(escaped(sources[r['source_id']]['title']+' · '+r['locator']+' · 原件 '+r['source_version'][:12]+' · 提取v'+str(r['extraction_revision'])+' · '+r['excerpt']) for r in c['source_refs'])
        rows[c['type']].append([uid,front,back,citation]);counts[c['type']]+=1
    for kind,data in rows.items():
        with (out/(kind+'.tsv')).open('w',encoding='utf-8',newline='') as f:
            model='Knowledge Cards '+('Basic' if kind=='basic' else 'Cloze')+' v2'
            f.write('#separator:Tab\n#html:true\n#notetype:'+model+'\n#columns:UID\t'+('Front\tBack' if kind=='basic' else 'Text\tExtra')+'\tSource\n')
            csv.writer(f,delimiter='\t',lineterminator='\n').writerows(data)
    report={'kind':'anki_export','pack_id':pack['pack_id'],'revision':pack['revision'],'counts':counts,'media':sorted(used),'apkg':None,'note_identity':{},'scheduling':'Web records are separate; no two-way synchronization','tsv':'Import with the matching custom note type; UID is the unchanged first field for updates. APKG creates the note types.'}
    if genanki:
        basic=genanki.Model(fixed_id('kcc-v2-model-basic'),'Knowledge Cards Basic v2',fields=[{'name':x} for x in ['UID','Front','Back','Source']],templates=[{'name':'Card 1','qfmt':'{{Front}}','afmt':'{{FrontSide}}<hr id="answer">{{Back}}<hr><small>{{Source}}</small>'}],sort_field_index=0)
        cloze=genanki.Model(fixed_id('kcc-v2-model-cloze'),'Knowledge Cards Cloze v2',fields=[{'name':x} for x in ['UID','Text','Extra','Source']],templates=[{'name':'Cloze','qfmt':'{{cloze:Text}}','afmt':'{{cloze:Text}}<br>{{Extra}}<hr><small>{{Source}}</small>'}],model_type=genanki.Model.CLOZE,sort_field_index=0)
        class StableNote(genanki.Note):
            def write_to_db(self,cursor,timestamp,deck_id,id_gen):
                super().write_to_db(cursor,timestamp,deck_id,itertools.chain([self.stable_id],id_gen))
        decks={d['deck_id']:genanki.Deck(fixed_id('kcc-v2-deck:'+pack['pack_id']+':'+d['deck_id']),pack['title']+'::'+d['title']) for d in pack['decks']}
        by_uid={row[0]:row for data in rows.values() for row in data}
        for c in pack['cards']:
            uid=pack['pack_id']+':'+c['note_id']; identity=uid+':'+c['type']
            guid=genanki.guid_for('knowledge-cards-coach-v2',identity)
            if identity not in registry['notes']:
                registry['next_id']=max(registry['next_id']+1,int(time.time()*1000));registry['notes'][identity]={'id':registry['next_id'],'guid':guid}
            saved=registry['notes'][identity];require(saved['guid']==guid,'Anki identity registry conflict')
            note=StableNote(model=basic if c['type']=='basic' else cloze,fields=by_uid[uid],guid=guid)
            note.stable_id=saved['id'];decks[c['deck_id']].add_note(note)
            report['note_identity'][c['note_id']]={'note_id':saved['id'],'guid':guid,'model_id':note.model.model_id,'deck_id':decks[c['deck_id']].deck_id}
        package=genanki.Package(list(decks.values()));package.media_files=media_paths
        path=out/'knowledge-cards.apkg';package.write_to_file(str(path))
        atomic(registry_path,registry);report['apkg']=str(path);report['sha256']=sha(path.read_bytes())
    atomic(out/'export-report.json',report)
    return report
