"""Actual local CLI/Anki backend integration with synthetic data only."""
from pathlib import Path
import copy,json,sqlite3,subprocess,sys,tempfile,time,zipfile
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT/'knowledge-cards-coach';CLI=SKILL/'scripts/coach.py'
sys.path.insert(0,str(SKILL/'scripts'))
import common
from anki_export import export
OUT=ROOT.parent/'v2-test-output';OUT.mkdir(exist_ok=True)
RUN=Path(tempfile.mkdtemp(prefix='workflow-',dir=OUT));WORK=RUN/'中文 空间';results=[]

def record(name,fn):
    try:fn();results.append({'name':name,'status':'pass'})
    except Exception as e:
        import traceback
        results.append({'name':name,'status':'fail','error':str(e),'trace':traceback.format_exc()})

def cli(command,*args,workspace=WORK,ok=True):
    p=subprocess.run([sys.executable,'-X','utf8',str(CLI),command,'--workspace',str(workspace),*map(str,args)],capture_output=True,text=True,encoding='utf-8')
    if ok:
        assert p.returncode==0,p.stderr
        return json.loads(p.stdout)
    assert p.returncode!=0,'expected rejection';return p.stderr

def write(name,data):
    p=RUN/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');return p

pack=common.load(SKILL/'examples/synthetic-pack.json')
def setup():
    cli('init')
    for name in ['source.md','source.png','source.pdf']:cli('ingest','--file',SKILL/'examples'/name)
    again=cli('ingest','--file',SKILL/'examples/source.png');assert again['deduplicated']
    assert len(common.material_index(WORK)['materials'])==3
    cli('import','--file',SKILL/'examples/synthetic-pack.json')
record('text/image/PDF intake, original hash and dedup',setup)

def notes():
    r=cli('notes');p=Path(r['notes']);text=p.read_text(encoding='utf-8')
    assert '出处：' in text and pack['sources'][1]['source_version'] in text and '水蒸气冷却' in text
    p.write_text(text+'\n用户自己的补充。\n',encoding='utf-8');r=cli('notes')
    assert '用户自己的补充。' in p.read_text(encoding='utf-8') and Path(r['proposal']).is_file()
record('standalone cited Markdown and user-edit preservation',notes)

first_build=None
def build_one():
    global first_build
    first_build=cli('build-review','--no-serve','--no-open')
    p=Path(first_build['directory']);assert (p/'bundle.js').is_file() and (p/'index.html').is_file()
    assert 'synthetic-water-cycle' in (p/'bundle.js').read_text(encoding='utf-8')
record('Chinese-path independent review directory with preloaded data',build_one)

def attempt(q,day,index,response):
    grade={'status':'pending','method':'external_pending'} if q['kind']=='open' else {'status':'correct' if response==q['answer_option_id'] else 'incorrect','method':'deterministic'}
    return {'attempt_id':f'fixture-{day}-{index}','question_id':q['question_id'],'question_version':q['version'],'answered_at':f'2026-10-{day:02}T10:00:{index*10:02}Z','response':response,'confidence':5,'self_rating':'easy','elapsed_ms':12000,'question_snapshot':copy.deepcopy(q),'grade':grade}

def session(p,day,responses):
    ats=[attempt(q,day,i+1,responses[q['question_id']]) for i,q in enumerate(p['questions']) if q['question_id'] in responses]
    return {'schema_version':'2.0','kind':'session','session_id':f'fixture-session-{day}','pack_id':p['pack_id'],'pack_revision':p['revision'],'started_at':f'2026-10-{day:02}T10:00:00Z','ended_at':f'2026-10-{day:02}T10:01:00Z','attempts':ats}

day1=session(pack,15,{'q-evaporation':'gas-to-liquid','q-condensation':'Liquid becomes gas.'})
p2=copy.deepcopy(pack);p2['revision']=2;p2['created_at']='2026-10-16T09:00:00Z';p2['cards'][0]['back']='Liquid water changes into water vapor.';p2['questions'][0]['version']=2;p2['questions'][0]['prompt']='Revised wording: evaporation changes water in which direction?'
p3=copy.deepcopy(p2);p3['revision']=3;p3['created_at']='2026-10-17T09:00:00Z';p3['cards'][0]['mnemonic']='用户保留助记';p3['cards'][0]['user_edited']=True
day2=session(p2,16,{'q-evaporation':'gas-to-liquid','q-condensation':'Cool vapor turns into liquid drops.'})
day3=session(p3,17,{'q-evaporation':'liquid-to-gas','q-condensation':'Gas water cools into liquid water.','q-energy':'moon'})

def assessment(sess,status):
    a=next(a for a in sess['attempts'] if a['question_snapshot']['kind']=='open')
    return {'schema_version':'2.0','kind':'assessment','assessment_id':'assessment-'+sess['session_id'],'created_at':sess['ended_at'].replace('10:01','11:01'),'evaluator':'synthetic-fixture','session_ids':[sess['session_id']],'results':[{'attempt_id':a['attempt_id'],'status':status,'feedback':'Synthetic semantic fixture: direction '+('matches' if status=='correct' else 'is reversed')+'; equivalent language accepted.','evidence_quote':a['response']}]}

first_export=None;second_export=None
def history():
    global first_export,second_export
    cli('import','--file',write('day1.json',day1));first_export=cli('export-anki','--out',RUN/'anki-r1')
    cli('import','--file',write('pack-r2.json',p2));cli('import','--file',write('day2.json',day2))
    cli('import','--file',write('pack-r3.json',p3));cli('import','--file',write('day3.json',day3))
    for sess,status in [(day1,'incorrect'),(day2,'correct'),(day3,'correct')]:cli('import','--file',write('assessment-'+sess['session_id']+'.json',assessment(sess,status)))
    s=common.state(WORK);assert len(s['packs'])==3 and len(s['sessions'])==3
    assert s['sessions'][0]['attempts'][0]['question_snapshot']['version']==1
    assert s['sessions'][0]['attempts'][0]['grade']['status']=='incorrect'
    before=(WORK/'state.json').read_bytes();cli('import','--file',RUN/'day1.json');assert (WORK/'state.json').read_bytes()==before
    second_export=cli('export-anki','--out',RUN/'anki-r3')
record('three days, stable attempts, archived questions and duplicate import',history)

def budgets():
    one=cli('review','--as-of','2026-10-15','--minutes','20');two=cli('review','--as-of','2026-10-16','--minutes','20');three=cli('review','--as-of','2026-10-17','--minutes','20')
    def statuses(r):return {x['concept_id']:x['status'] for x in r['summary']['concepts']}
    assert statuses(one)['evaporation']=='check'
    assert statuses(two)['evaporation']=='weak'
    assert statuses(three)['evaporation']=='recovering' and statuses(three)['condensation']=='improving' and statuses(three)['energy']=='check'
    assert all(x!='stable' for x in statuses(three).values())
    assert one['plan']['pack_revision']==1 and two['plan']['pack_revision']==2 and three['plan']['pack_revision']==3
    assert all(sum(i['minutes'] for i in r['plan']['items'])<=20 for r in [one,two,three])
    small=cli('review','--as-of','2026-10-17','--minutes','2');assert sum(i['minutes'] for i in small['plan']['items'])<=2 and small['plan']['deferred']
    assert all(i['item_id']!='q-energy' for i in small['plan']['items'])
    repeated=cli('review','--as-of','2026-10-15','--minutes','20');assert repeated['plan']==one['plan']
    assert one['summary']['attempt_count']==2 and one['summary']['excluded_future_sessions']==2
record('three-day changing signals, cutoff without future leakage, budgets and prerequisite deferral',budgets)

def safety():
    before=(WORK/'state.json').read_bytes()
    low=copy.deepcopy(p3);low['revision']=4;low['sources'][1]['confidence']=.3
    cli('import','--file',write('unclear-image.json',low),ok=False)
    modified=copy.deepcopy(p3);modified['revision']=4;modified['cards'][0]['mnemonic']='AI silently overwrites user';modified['cards'][0].pop('user_edited')
    cli('import','--file',write('overwrites-user.json',modified),ok=False)
    forged=copy.deepcopy(day1);forged['session_id']='forged';forged['attempts'][0]['grade']['status']='correct'
    cli('import','--file',write('forged-grade.json',forged),ok=False)
    for i,raw in enumerate(['{"kind":"backup","kind":"session"}','{"__proto__":{}}','{"x":NaN}']):
        p=RUN/f'bad-{i}.json';p.write_text(raw,encoding='utf-8');cli('import','--file',p,ok=False)
    assert (WORK/'state.json').read_bytes()==before
record('unclear OCR, forged scores, malformed JSON and silent overwrite safely rejected',safety)

def build_two():
    second=cli('build-review','--no-serve','--no-open')
    assert second['template_sha256']==first_build['template_sha256']
    assert second['bundle_sha256']!=first_build['bundle_sha256'] and second['directory']!=first_build['directory']
record('fixed templates byte-identical while data and independent directory change',build_two)

def structures():
    assert first_export['note_identity']==second_export['note_identity']
    for report in [first_export,second_export]:
        with zipfile.ZipFile(report['apkg']) as z:
            assert 'collection.anki2' in z.namelist() and 'media' in z.namelist() and z.testzip() is None
            media=json.loads(z.read('media'));assert list(media.values())==report['media'] and all('/' not in x for x in media.values())
            db=RUN/('sqlite-'+str(report['revision'])+'.sqlite');db.write_bytes(z.read('collection.anki2'))
            with sqlite3.connect(db) as con:
                assert con.execute('select count(*) from notes').fetchone()[0]==3
                assert len({x[0] for x in con.execute('select mid from notes')})==2
                assert any('<img src="condensation-' in x[0] for x in con.execute('select flds from notes'))
        assert (Path(report['apkg']).parent/'basic.tsv').read_text(encoding='utf-8').startswith('#separator:Tab')
record('genuine APKG SQLite/media, Basic+Cloze, stable note IDs/GUIDs/models/decks and TSV',structures)

def actual_import():
    from anki.collection import Collection
    from anki.import_export_pb2 import ImportAnkiPackageRequest,ImportAnkiPackageOptions,ImportAnkiPackageUpdateCondition
    folder=RUN/'Anki隔离配置';folder.mkdir();col=Collection(str(folder/'collection.anki2'))
    try:
        options=ImportAnkiPackageOptions(with_scheduling=False,with_deck_configs=False,update_notes=ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS,update_notetypes=ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS)
        col.import_anki_package(ImportAnkiPackageRequest(package_path=first_export['apkg'],options=options));assert col.note_count()==3
        col.import_anki_package(ImportAnkiPackageRequest(package_path=first_export['apkg'],options=options));assert col.note_count()==3
        col.import_anki_package(ImportAnkiPackageRequest(package_path=second_export['apkg'],options=options));assert col.note_count()==3
        fields=col.db.list('select flds from notes');assert any('Liquid water changes into water vapor.' in x for x in fields)
        (RUN/'anki-import-evidence.json').write_text(json.dumps({'backend':'Anki Python 26.9.3 real Rust importer; isolated collection, no desktop install','note_counts':[3,3,3],'updated_answer_observed':True,'collection':str(folder)},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:col.close()
record('actual isolated Anki backend import, repeated import and answer update without duplicates',actual_import)

def backups():
    file=RUN/'backup.json';cli('backup','--out',file);fresh=RUN/'中文恢复';cli('restore','--file',file,workspace=fresh)
    assert common.canonical(common.state(fresh))==common.canonical(common.state(WORK))
    assert common.load(fresh/'anki-identity.json')==common.load(WORK/'anki-identity.json')
record('backup/restore retains sources, records, versions and Anki identity',backups)

report={'scope':'Synthetic local CLI integration; image visually checked separately; actual backend import is distinct from desktop GUI import','directory':str(RUN),'tests':results}
(RUN/'workflow-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'latest-workflow.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(any(x['status']=='fail' for x in results))
