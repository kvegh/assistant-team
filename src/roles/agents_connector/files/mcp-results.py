#!/usr/bin/env python3
"""Preserve stock MCP stdio while shielding Gemini's JSON-text promotion bug."""
import json
import subprocess
import sys
import threading

MAX_LINE = 1048576


def normalize(message):
    """Add an object envelope only to successful JSON non-object tool text."""
    if not isinstance(message, dict):
        return message
    result = message.get('result')
    if not isinstance(result, dict) or result.get('isError') or 'structuredContent' in result:
        return message
    content = result.get('content')
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        return message
    first = content[0]
    if first.get('type') != 'text' or not isinstance(first.get('text'), str):
        return message
    try:
        parsed = json.loads(first['text'])
    except (ValueError, TypeError):
        return message
    if isinstance(parsed, dict):
        return message
    result['structuredContent'] = {'items': parsed} if isinstance(parsed, list) else {'value': parsed}
    return message


def relay(command):
    child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def forward_input():
        try:
            while True:
                chunk = sys.stdin.buffer.read1(65536)
                if not chunk:
                    break
                child.stdin.write(chunk)
                child.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                child.stdin.close()
            except (BrokenPipeError, OSError):
                pass

    threading.Thread(target=forward_input, daemon=True).start()
    try:
        while True:
            line = child.stdout.readline(MAX_LINE + 1)
            if not line:
                break
            if len(line) > MAX_LINE:
                raise ValueError('MCP result exceeds bounded line size')
            try:
                response = normalize(json.loads(line))
            except (ValueError, TypeError):
                sys.stdout.buffer.write(line)
            else:
                sys.stdout.buffer.write(json.dumps(response, separators=(',', ':')).encode() + b'\n')
            sys.stdout.buffer.flush()
        return child.wait()
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('MCP result adapter requires the stock shim command')
    try:
        raise SystemExit(relay(sys.argv[1:]))
    except (OSError, ValueError):
        raise SystemExit('MCP result adapter failed; inspect native MCP status')
