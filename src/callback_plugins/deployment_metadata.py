"""Export allowlisted deployment metadata, never result bodies or host identity."""
import json
import os
import pathlib
from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION=2.0
    CALLBACK_TYPE='aggregate'
    CALLBACK_NAME='deployment_metadata'
    CALLBACK_NEEDS_ENABLED=True

    def record(self, category, result=None):
        directory=os.environ.get('ASSISTANT_DEPLOYMENT_LOG_DIR')
        if not directory:return
        event={'category':category}
        if result is not None:
            # Module names and task UUIDs are framework metadata, not remote result text.
            event['task_id']=str(result._task._uuid)
            action=str(result._task.action)
            event['module']=action if all(c.isalnum() or c in '._' for c in action) else 'unknown'
            value=result._result.get('rc')
            if type(value) is int:event['exit_code']=value
        path=pathlib.Path(directory)/'events.jsonl'
        fd=os.open(path,os.O_APPEND|os.O_CREAT|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w') as file:file.write(json.dumps(event)+'\n')

    def v2_runner_on_ok(self,result):self.record('task_ok',result)
    def v2_runner_on_failed(self,result,ignore_errors=False):self.record('task_failed',result)
    def v2_runner_on_unreachable(self,result):self.record('connection_failed',result)
    def v2_runner_on_skipped(self,result):self.record('task_skipped',result)
    def v2_playbook_on_stats(self,stats):self.record('playbook_finished')
