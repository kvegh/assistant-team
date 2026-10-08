#!/usr/bin/env python3
"""Operator-entered Vertex configuration and isolated Google ADC login."""
import json,os,pathlib,re,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
CONFIG=root/'.vertex.json'
ADC=root/'.config/gcloud/application_default_credentials.json'
KEYS={'CLAUDE_CODE_USE_VERTEX','CLOUD_ML_REGION','ANTHROPIC_VERTEX_PROJECT_ID','ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_OPUS_MODEL','ANTHROPIC_DEFAULT_SONNET_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL'}
GEMINI_KEYS={'GOOGLE_GENAI_USE_VERTEXAI','GOOGLE_CLOUD_PROJECT','GOOGLE_CLOUD_LOCATION','GEMINI_MODEL'}
def vendor():
 try:return json.loads((root/'.native-install.json').read_text())['flavour']
 except (OSError,ValueError):return 'claude'
def read_config():
 try:cfg=json.loads(CONFIG.read_text())
 except (OSError,ValueError):raise ValueError('Work Vertex configuration is missing; run ./login in claude-work')
 if vendor()=='gemini':
  if set(cfg)!=GEMINI_KEYS or cfg.get('GOOGLE_GENAI_USE_VERTEXAI')!='true':raise ValueError('Invalid Gemini Vertex configuration allowlist')
  if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',cfg['GOOGLE_CLOUD_PROJECT']):raise ValueError('Invalid Google project ID')
  if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',cfg['GOOGLE_CLOUD_LOCATION']):raise ValueError('Invalid Vertex location')
  if not re.fullmatch(r'[A-Za-z0-9_.@-]+',cfg['GEMINI_MODEL']):raise ValueError('Invalid explicit Gemini model ID')
  return cfg
 if set(cfg)!=KEYS or cfg['CLAUDE_CODE_USE_VERTEX']!='1':raise ValueError('Invalid Vertex configuration allowlist')
 if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',cfg['ANTHROPIC_VERTEX_PROJECT_ID']):raise ValueError('Invalid Google project ID')
 if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',cfg['CLOUD_ML_REGION']):raise ValueError('Invalid Vertex region/location')
 for k in ['ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_OPUS_MODEL','ANTHROPIC_DEFAULT_SONNET_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL']:
  if not re.fullmatch(r'claude-[a-z0-9-]+(?:@[0-9]{8})?',cfg[k]):raise ValueError('Use an explicit enabled Vertex Claude model ID, not an alias')
 return cfg

def environment(env):
 cfg=read_config()
 if not ADC.is_file():raise ValueError('Work Vertex ADC is missing; run ./login in claude-work')
 # The caller's environment is scoped already; no process-wide host configuration changes.
 result=env.copy()
 for key in ['ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN','CLAUDE_CODE_OAUTH_TOKEN','CLAUDE_CODE_USE_BEDROCK','CLAUDE_CODE_USE_FOUNDRY','GEMINI_API_KEY','GOOGLE_API_KEY']:
  result.pop(key,None)
 result.update(cfg);result['GOOGLE_APPLICATION_CREDENTIALS']=str(ADC);result['CLOUDSDK_CONFIG']=str(root/'.config/gcloud')
 return result

def login(env):
 sdk=root/'.install/google-cloud-sdk/bin/gcloud'
 if not sdk.is_file():raise ValueError('Google Cloud CLI is not installed yet; finish the approved Vertex setup first')
 current={}
 if CONFIG.is_file():
  try:current=read_config()
  except ValueError:pass
 def prompt(label,key,pattern,default=None):
  old=current.get(key,default or '')
  while True:
   value=input(label+(' ['+old+']' if old else '')+': ').strip() or old
   if re.fullmatch(pattern,value):return value
   if key in {'ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL'}:
    print('[AC-Agents]: Use the full Vertex model ID, for example claude-opus-5. Opus, opus and Opus-5 are not full IDs. The selected model must be enabled for your Google project and location; this prompt does not check access.')
   else:
    print('[AC-Agents]: Enter the requested identifier in its supported format.')
 is_gemini=vendor()=='gemini'
 project=prompt('Google project ID','GOOGLE_CLOUD_PROJECT' if is_gemini else 'ANTHROPIC_VERTEX_PROJECT_ID',r'[a-z][a-z0-9-]{4,28}[a-z0-9]')
 region=prompt('Vertex region/location (for example us-east5 or global)','GOOGLE_CLOUD_LOCATION' if is_gemini else 'CLOUD_ML_REGION',r'[a-z][a-z0-9-]{0,39}')
 if is_gemini:
  model=prompt('Enabled Vertex Gemini model ID','GEMINI_MODEL',r'[A-Za-z0-9_.@-]+')
  cfg={'GOOGLE_GENAI_USE_VERTEXAI':'true','GOOGLE_CLOUD_PROJECT':project,'GOOGLE_CLOUD_LOCATION':region,'GEMINI_MODEL':model}
 else:
  cfg=claude_models(prompt,project,region)
 CONFIG.write_text(json.dumps(cfg,indent=2)+'\n');CONFIG.chmod(0o600)
 scoped=env.copy()
 for key in ['GOOGLE_APPLICATION_CREDENTIALS','GEMINI_API_KEY','GOOGLE_API_KEY']:
  scoped.pop(key,None)
 scoped['CLOUDSDK_CONFIG']=str(root/'.config/gcloud');scoped['CLOUDSDK_CORE_DISABLE_USAGE_REPORTING']='true';scoped['CLOUDSDK_CORE_PROJECT']=project
 subprocess.run([str(sdk),'auth','application-default','login','--no-launch-browser','--project',project],env=scoped,check=True)
 if not ADC.is_file():raise ValueError('Google ADC login did not create the expected scoped credential file')
 ADC.chmod(0o600)
 if is_gemini:
  settings=root/'.gemini/settings.json';settings.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  value=json.loads(settings.read_text()) if settings.is_file() else {}
  auth=value.setdefault('security',{}).setdefault('auth',{});auth['selectedType']='vertex-ai';auth['enforcedType']='vertex-ai'
  settings.write_text(json.dumps(value,indent=2)+'\n');settings.chmod(0o600)
 print('[AC-Agents]: Work Vertex login saved in this directory. No API enablement, billing change or model probe was requested by this wrapper.')

def claude_models(prompt,project,region):
 model=prompt('Enabled Vertex Claude primary model ID (for example claude-opus-5; not Opus)','ANTHROPIC_MODEL',r'claude-[a-z0-9-]+(?:@[0-9]{8})?')
 small=prompt('Enabled small/background model ID (Enter uses primary)','ANTHROPIC_DEFAULT_HAIKU_MODEL',r'claude-[a-z0-9-]+(?:@[0-9]{8})?',model)
 cfg={'CLAUDE_CODE_USE_VERTEX':'1','CLOUD_ML_REGION':region,'ANTHROPIC_VERTEX_PROJECT_ID':project,'ANTHROPIC_MODEL':model,'ANTHROPIC_DEFAULT_OPUS_MODEL':model,'ANTHROPIC_DEFAULT_SONNET_MODEL':model,'ANTHROPIC_DEFAULT_HAIKU_MODEL':small}
 return cfg

if __name__=='__main__':
 try:
  os.umask(0o077)
  if sys.argv[1:]!=['login']:raise ValueError('Use the directory-local ./login command')
  login(os.environ.copy())
 except (ValueError,subprocess.CalledProcessError) as error:raise SystemExit(str(error))
