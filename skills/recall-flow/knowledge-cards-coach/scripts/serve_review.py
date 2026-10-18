"""Loopback-only static review server with validated, explicit local save."""
import argparse
from functools import partial
from http.server import HTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import secrets
import time
from common import atomic,load,locked,merge,parse,save_state,sha,state,MAX_JSON,canonical

def serve(directory,workspace,port,token,idle=7200):
    root=Path(directory).resolve();workspace=Path(workspace).resolve()
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
        def host_ok(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
        def do_GET(self):
            self.server.touched=time.monotonic()
            if not self.host_ok():self.send_error(403);return
            super().do_GET()
        def do_POST(self):
            self.server.touched=time.monotonic()
            expected=f'http://127.0.0.1:{self.server.server_port}'
            if not self.host_ok() or self.headers.get('Origin')!=expected or not secrets.compare_digest(self.headers.get('X-Review-Token',''),token):
                self.send_error(403);return
            if self.path=='/api/stop':
                self.server.stopping=True;self.reply({'ok':True});return
            if self.path!='/api/save':self.send_error(404);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=MAX_JSON:raise ValueError('request too large/empty')
                doc=parse(self.rfile.read(length))
                if doc.get('kind') not in {'backup','session'}:raise ValueError('only actual session/backup accepted')
                with locked(workspace):
                    current=state(workspace);next_state=merge(workspace,current,[doc],accept_edits=True)
                    save_state(workspace,next_state)
                    atomic(workspace/'incoming'/('web-'+sha(canonical(doc).encode())[:24]+'.json'),doc)
                self.reply({'ok':True,'session_count':len(next_state['sessions']),'attempt_count':sum(len(x['attempts']) for x in next_state['sessions'])})
            except Exception as e:self.reply({'ok':False,'error':str(e)},409)
        def reply(self,data,code=200):
            body=canonical(data).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    server=HTTPServer(('127.0.0.1',port),partial(Handler,directory=str(root)))
    server.timeout=1;server.touched=time.monotonic();server.stopping=False
    atomic(root/'server-ready.json',{'url':f'http://127.0.0.1:{server.server_port}/','pid':__import__('os').getpid(),'binding':'127.0.0.1 only','idle_seconds':idle})
    while not server.stopping and time.monotonic()-server.touched<idle:server.handle_request()
    server.server_close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True);p.add_argument('--workspace',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--token',required=True);p.add_argument('--idle',type=int,default=7200)
    a=p.parse_args();serve(a.directory,a.workspace,a.port,a.token,a.idle)
