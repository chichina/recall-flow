"""Isolated headless test of our generated local website, NOT a desktop screenshot."""
from pathlib import Path
import copy,json,sys,tempfile,urllib.request,os,shutil
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT/'knowledge-cards-coach';sys.path.insert(0,str(SKILL/'scripts'))
import common
from coach import build_review
os.environ.setdefault('PLAYWRIGHT_NODEJS_PATH',shutil.which('node') or '')
from playwright.sync_api import sync_playwright,expect
OUT=ROOT.parent/'v2-test-output';OUT.mkdir(exist_ok=True);RUN=Path(tempfile.mkdtemp(prefix='web-',dir=OUT));WORK=RUN/'中文浏览器学习库';WORK.mkdir()
pack=common.load(SKILL/'examples/synthetic-pack.json')
for name in ['source.md','source.png','source.pdf']:common.ingest(WORK,SKILL/'examples'/name)
s=common.merge(WORK,common.empty(),[pack]);common.save_state(WORK,s)
build=build_review(WORK,s,pack,open_browser=False,port=0);results=[];errors=[];unexpected=[]
print('Local test server ready: '+build['url'],flush=True)
def done(name):results.append({'name':name,'status':'pass'});print(name,flush=True)

try:
 with sync_playwright() as pw:
    print('Playwright driver ready; launching isolated test Chrome',flush=True)
    browser=pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True,chromium_sandbox=True,timeout=20000)
    context=browser.new_context(viewport={'width':1366,'height':900},accept_downloads=True)
    def route(r):
        if r.request.url.startswith(build['url']) or r.request.url.startswith(('data:','blob:')):r.continue_()
        else:unexpected.append(r.request.url);r.abort()
    context.route('**/*',route)
    page=context.new_page();page.set_default_timeout(10000);page.on('pageerror',lambda e:errors.append(str(e)));page.goto(build['url'])
    expect(page.get_by_role('heading',name='今天，向理解再进一步。')).to_be_visible()
    expect(page.locator('#pack-select')).to_have_value(pack['pack_id']+'@1')
    done('automatic bundle loading without manual JSON import')
    page.get_by_role('button',name='开始练习',exact=True).click()
    page.get_by_role('radio').nth(0).check();page.get_by_label('答题信心',exact=True).select_option('5');page.get_by_role('button',name='提交回答',exact=True).click()
    expect(page.get_by_role('button',name='本题已记录',exact=True)).to_be_visible();page.reload()
    expect(page.get_by_role('button',name='本题已记录',exact=True)).to_be_visible()
    done('actual MCQ submission and refresh retain original attempt')
    page.get_by_role('button',name='下一题 →',exact=True).click();page.get_by_label('开放题回答',exact=True).fill('Cool vapor becomes liquid drops.');page.reload()
    expect(page.get_by_label('开放题回答',exact=True)).to_have_value('Cool vapor becomes liquid drops.')
    page.get_by_role('button',name='提交回答',exact=True).click()
    expect(page.locator('.result.pending')).to_be_visible()
    done('open answer remains pending, and unsubmitted text survives refresh')
    page.get_by_role('button',name='下一题 →',exact=True).click();page.get_by_role('radio').nth(1).check();page.get_by_role('button',name='提交回答',exact=True).click()
    with page.expect_response(lambda r:r.url.endswith('/api/save')) as saved:
        page.get_by_role('button',name='结束并保存本次练习',exact=True).click()
    assert saved.value.status==200,saved.value.text()
    expect(page.locator('#sync-status')).to_contain_text('本机已保存')
    data=common.state(WORK);assert len(data['sessions'])==1 and len(data['sessions'][0]['attempts'])==3
    assert data['sessions'][0]['attempts'][1]['grade']['status']=='pending' and data['sessions'][0]['attempts'][2]['grade']['status']=='incorrect'
    done('completed browser session writes validated real local file')
    page.get_by_role('button',name='导入与导出',exact=True).click()
    with page.expect_download() as download:page.get_by_role('button',name='导出本次 session',exact=True).click()
    download.value.save_as(str(RUN/'browser-session.json'))
    doc=common.load(RUN/'browser-session.json');assert len(doc['attempts'])==3
    backup=page.evaluate('JSON.parse(localStorage.getItem('+json.dumps('kcc-v2-'+common.sha(str(WORK.resolve()).encode())[:20])+')).db')
    page.get_by_label('JSON 内容',exact=True).fill(json.dumps(backup,ensure_ascii=False));page.get_by_role('button',name='校验并导入',exact=True).click()
    expect(page.locator('#toast')).to_contain_text('相同文档已存在')
    before=page.evaluate('localStorage.getItem('+json.dumps('kcc-v2-'+common.sha(str(WORK.resolve()).encode())[:20])+')')
    page.get_by_label('JSON 内容',exact=True).fill('{"schema_version":"2.0","schema_version":"2.0"}');page.get_by_role('button',name='校验并导入',exact=True).click()
    expect(page.locator('#toast')).to_contain_text('JSON')
    after=page.evaluate('localStorage.getItem('+json.dumps('kcc-v2-'+common.sha(str(WORK.resolve()).encode())[:20])+')');assert before==after
    done('portable session export, idempotent import and unsafe JSON preserve storage')
    page.get_by_role('button',name='知识卡片',exact=True).click();page.locator('.flashcard').focus();page.keyboard.press('Space');expect(page.locator('.card-bottom')).to_contain_text('答案面');page.keyboard.press('ArrowRight');expect(page.locator('.flashcard')).to_contain_text('2 / 3')
    done('keyboard flip and navigation')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),page.evaluate('({scroll:document.documentElement.scrollWidth,viewport:innerWidth})')
    page.screenshot(path=str(RUN/'mobile-review.png'),full_page=True);done('390px mobile layout without horizontal overflow (test browser only)')
    page.set_viewport_size({'width':1366,'height':900});page.get_by_role('button',name='导入与导出',exact=True).click()
    hostile=copy.deepcopy(pack);hostile['revision']=2;hostile['created_at']='2026-10-18T00:00:00Z';hostile['cards'][0]['front']='<img src=x onerror="window.__testXSS=1">'
    page.get_by_label('JSON 内容',exact=True).fill(json.dumps(hostile,ensure_ascii=False));page.get_by_role('button',name='校验并导入',exact=True).click();page.locator('#pack-select').select_option(pack['pack_id']+'@2');page.get_by_role('button',name='知识卡片',exact=True).click()
    expect(page.locator('.card-content')).to_contain_text('<img src=x')
    assert page.locator('.card-content img').count()==0 and page.evaluate('window.__testXSS') is None
    done('source/card HTML is escaped and not executed')
    assert not errors,errors
    assert not unexpected,unexpected
    done('no page JavaScript errors or external network requests')
    browser.close()
except Exception as e:
    import traceback
    results.append({'name':'browser integration','status':'fail','error':str(e),'trace':traceback.format_exc()})
finally:
    runtime=common.load(Path(build['directory'])/'review-runtime.json');url=runtime['url']
    try:urllib.request.urlopen(urllib.request.Request(url+'api/stop',data=b'',headers={'Origin':url.rstrip('/'),'X-Review-Token':runtime['token']},method='POST'),timeout=3).read()
    except Exception:pass
report={'scope':'Synthetic answers entered by automated isolated test browser; no actual human study or desktop control claimed','directory':str(RUN),'workspace':str(WORK),'build':build,'tests':results,'page_errors':errors,'external_requests':unexpected}
(RUN/'web-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'latest-web.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(any(x['status']=='fail' for x in results))
