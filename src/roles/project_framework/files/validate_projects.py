#!/usr/bin/env python3
"""Opt-in disposable, dummy-harness project lifecycle checks; never provider calls."""
import importlib.util,json,os,pathlib,selectors,shutil,socket,sqlite3,struct,subprocess,sys,time,uuid,pwd,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
ACCOUNT_HOME=ROOT.parent
TEAM=ACCOUNT_HOME/'bin/team'
UNIT_DIR=pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir)/'.config/systemd/user'
NAMES=['offline-a-'+uuid.uuid4().hex[:8],'offline-b-'+uuid.uuid4().hex[:8]]
ENV=os.environ.copy();ENV['XDG_RUNTIME_DIR']='/run/user/'+str(os.getuid());ENV['DBUS_SESSION_BUS_ADDRESS']='unix:path='+ENV['XDG_RUNTIME_DIR']+'/bus'
def run(args,**kw):return subprocess.run([str(a) for a in args],env=ENV,check=True,**kw)
def rpc(name,obj):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(5);s.connect(str(ACCOUNT_HOME/'projects'/name/'broker.sock'));payload=json.dumps(obj).encode();s.sendall(struct.pack('!I',len(payload))+payload)
  def read(n):
   b=b''
   while len(b)<n:
    part=s.recv(n-len(b))
    if not part:raise EOFError()
    b+=part
   return b
  return json.loads(read(struct.unpack('!I',read(4))[0]))
def wait_state(name,running):
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  result=subprocess.run(['podman','ps','--all','--format','{{.Names}} {{.State}}'],env=ENV,capture_output=True,text=True,check=True)
  found=[line for line in result.stdout.splitlines() if line.startswith('acp-'+name+'-')]
  if len(found)==8 and all((' running' in line)==running for line in found):return
  time.sleep(.2)
 raise AssertionError('Eight project containers did not reach expected state')
def main():
 baseline=subprocess.check_output(['podman','ps','--format','{{.Names}}'],env=ENV,text=True)
 made=[];dropins=[];watcher=None;sandbox=None
 try:
  for name in NAMES:
   run([TEAM,'create-project',name],stdout=subprocess.DEVNULL);made.append(name)
   path=ACCOUNT_HOME/'projects'/name
   with sqlite3.connect(path/'db.sqlite') as db:
    assert db.execute('select count(*) from agents where removed_at IS NULL').fetchone()[0]==4
    assert db.execute('select count(*) from messages').fetchone()[0]==0
   assert (path/'assistant-prompt.md').is_file()
   for role in ['orchestrator','builder','investigator','challenger','summarizer']:
    workspace=path/'profiles'/role/'workspace';text=next(workspace.glob('*.md')).read_text();assert '# Project: '+name in text;assert '# Role: observer' not in text
   refused=subprocess.run([TEAM,'create-project',name],env=ENV,capture_output=True,text=True);assert refused.returncode!=0
   # Model-free substitution only on these freshly created test instances.
   fixture=path/'fixture-launch.py'
   fixture.write_text('''import importlib.util,pathlib,os,subprocess
root=pathlib.Path(__file__).resolve().parents[2]/"agent-connector"
spec=importlib.util.spec_from_file_location("fixture_core",root/"routing/connector-team.py")
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.apply_prompts()
for role in c.ALL:
 c.start_container(role)
 subprocess.run(["podman","exec",c.container(role),"tmux","respawn-pane","-k","-t","native:agent","cat"],check=True)
 (c.PROFILES/role/"launched").touch()
''')
   for unit,override in [
    ('broker','[Service]\nExecStartPre=\nExecStartPre=/usr/bin/true\n'),
    ('containers','[Service]\nExecStart=\nExecStart=/usr/bin/python3 '+str(fixture)+'\n')]:
    d=UNIT_DIR/('assistant-connector-'+unit+'@'+name+'.service.d');d.mkdir(mode=0o700);(d/'offline-fixture.conf').write_text(override);dropins.append(d)
  # Missing-auth check runs in an isolated home; no real credentials are copied.
  sandbox=pathlib.Path(tempfile.mkdtemp(prefix='ac-auth-',dir='/tmp'))
  (sandbox/'agent-connector/routing').mkdir(parents=True)
  shutil.copy2(ROOT/'routing/connector-team.py',sandbox/'agent-connector/routing/connector-team.py')
  shutil.copy2(ROOT/'routing/project-team.py',sandbox/'agent-connector/routing/project-team.py')
  shutil.copy2(ROOT/'routing/environment-config.py',sandbox/'agent-connector/routing/environment-config.py')
  (sandbox/'conf').mkdir(mode=0o700)
  for helper in ['install-paths.py','project-names.py']:
   shutil.copy2(ROOT/'routing'/helper,sandbox/'agent-connector/routing'/helper)
  (sandbox/'conf/environment.conf').write_text(json.dumps({'version':1,'profiles':{v+'-'+a:{'enabled':True} for v in ['claude','gemini','codex','mistral'] for a in ['work','priv']}}))
  p=sandbox/'projects/sample';(p/'profiles').mkdir(parents=True);(p/'initialized').touch()
  for role in ['orchestrator','builder','investigator','challenger','summarizer','observer','private-connector','corporate-connector']:
   q=p/'profiles'/role;q.mkdir();shutil.copy2(ROOT/'profiles'/role/'profile.json',q/'profile.json')
  result=subprocess.run(['python3',sandbox/'agent-connector/routing/project-team.py','start','sample'],env=ENV,capture_output=True,text=True)
  assert result.returncode!=0 and 'Authentication required before starting ANY' in result.stderr
  run(['systemctl','--user','daemon-reload'])
  for name in NAMES:
   run(['systemctl','--user','start','assistant-connector@'+name+'.target']);wait_state(name,True)
  a,b=NAMES
  # Shared artifacts are writable by workers; private readers have no shared mount.
  for role in ['orchestrator','builder','investigator','challenger','private-connector','corporate-connector']:
   run(['podman','exec','acp-'+a+'-'+role,'sh','-c','printf offline-shared > /workspace/shared/'+role])
  read=subprocess.check_output(['podman','exec','acp-'+a+'-investigator','cat','/workspace/shared/builder'],env=ENV,text=True);assert read=='offline-shared'
  for reader in ['observer','summarizer']:
   data=json.loads(subprocess.check_output(['podman','inspect','acp-'+a+'-'+reader],env=ENV,text=True))[0]
   assert not any(m['Destination']=='/workspace/shared' for m in data['Mounts'])
   assert any(m['Destination']=='/context' and not m['RW'] for m in data['Mounts'])
   assert not (ACCOUNT_HOME/'projects'/a/'profiles'/reader/'home/mcp.json').exists()
  assert (ACCOUNT_HOME/'projects'/a/'operator-reports/SUMMARY.md').is_file()
  assert not (ACCOUNT_HOME/'projects'/b/'workspace/builder').exists()
  private=ACCOUNT_HOME/'projects'/a/'profiles/private-connector/home/private-fixture';private.write_text('offline-private')
  hidden=subprocess.run(['podman','exec','acp-'+a+'-builder','test','-e','/workspace/shared/private-fixture'],env=ENV);assert hidden.returncode!=0
  assert os.stat(ACCOUNT_HOME/'projects'/a/'db.sqlite').st_ino!=os.stat(ACCOUNT_HOME/'projects'/b/'db.sqlite').st_ino
  watcher=subprocess.Popen([str(TEAM),'watch',a,'-f'],env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
  sel=selectors.DefaultSelector();sel.register(watcher.stdout,selectors.EVENT_READ)
  assert sel.select(5);assert 'Live worker discussion' in watcher.stdout.readline()
  # Snapshot streaming start; request delivery uses admin only within our test broker.
  response=rpc(a,{'kind':'tell','from':'builder','to':'investigator','text':'OFFLINE_PROJECT_EVENT','urgent':False});assert response['kind']!='error'
  assert sel.select(5);assert 'OFFLINE_PROJECT_EVENT' in watcher.stdout.readline()
  with sqlite3.connect(ACCOUNT_HOME/'projects'/b/'db.sqlite') as db:assert db.execute('select count(*) from messages').fetchone()[0]==0
  run([TEAM,'stop',a]);wait_state(a,False);wait_state(b,True)
  run(['systemctl','--user','restart','assistant-connector@'+b+'.target']);wait_state(b,True)
  with sqlite3.connect(ACCOUNT_HOME/'projects'/a/'db.sqlite') as db:assert db.execute('select count(*) from messages').fetchone()[0]==1
  remaining=subprocess.check_output(['podman','ps','--format','{{.Names}}'],env=ENV,text=True)
  assert set(baseline.splitlines())<=set(remaining.splitlines())
  print('Two stock-schema projects, missing-auth refusal, eight dummy harnesses per project, shared read/write and private reader isolation, live stream, stop/restart isolation and persistent SQLite passed; no native provider or model invoked.')
 finally:
  if watcher:
   watcher.terminate()
   try:watcher.wait(timeout=5)
   except subprocess.TimeoutExpired:watcher.kill();watcher.wait()
  for name in made:
   subprocess.run(['systemctl','--user','stop','assistant-connector@'+name+'.target'],env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   containers=subprocess.check_output(['podman','ps','--all','--format','{{.Names}}'],env=ENV,text=True).splitlines()
   owned=[c for c in containers if c.startswith('acp-'+name+'-')]
   if owned:subprocess.run(['podman','rm','--force',*owned],env=ENV,check=True,stdout=subprocess.DEVNULL)
  for d in dropins:shutil.rmtree(d)
  subprocess.run(['systemctl','--user','daemon-reload'],env=ENV,check=True)
  for name in made:
   shutil.rmtree(ACCOUNT_HOME/'projects'/name)
  if sandbox is not None:shutil.rmtree(sandbox)
if __name__=='__main__':main()
