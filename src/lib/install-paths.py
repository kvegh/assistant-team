"""Paths for one explicit PREFIX/ac-agents installation; no automatic migration."""
import importlib.util
import pathlib


class Paths:
    def __init__(self,root):self.root=pathlib.Path(root)
    @property
    def vendor(self):return self.root/'agent-connector'
    @property
    def models(self):return self.root/'model-environments'
    @property
    def environment(self):return self.root/'conf/environment.conf'
    @property
    def template(self):return self.root/'conf/templates/assistant.prompt.md.template'
    @property
    def team(self):return self.root/'bin/team'
    @property
    def archives(self):return self.root/'project-archive'
    @property
    def logs(self):return self.root/'environment-logs'
    def project(self,name):return self.root/'projects'/name
    def project_config(self,name):return self.project(name)/('project.'+name+'.config')
    def model(self,name):return self.models/name


def for_profile(profile):
    profile=pathlib.Path(profile).resolve()
    if profile.parent.name!='model-environments':
        raise ValueError('Profile is outside the installation model-environments directory; use the explicit migration procedure')
    return Paths(profile.parent.parent)


def load(script):
    source=pathlib.Path(script).resolve().with_name('install-paths.py')
    if not source.exists():source=pathlib.Path(script).resolve().parents[3]/'lib/install-paths.py'
    spec=importlib.util.spec_from_file_location('installation_paths',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
