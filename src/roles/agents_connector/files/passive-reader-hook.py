#!/usr/bin/env python3
"""Private lifecycle callback only; contains no team messaging capability."""
import argparse
import json
import pathlib
import socket
import struct
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--event',choices=['start','busy','done'],required=True)
args=parser.parse_args()
sys.stdin.read(1048576)  # Hook input remains local and is never copied into reports.
token=pathlib.Path('/home/agent/reader-token').read_text().strip()
raw=json.dumps({'kind':'reader_state','event':args.event,'token':token}).encode()
try:
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(5);connection.connect('/ipc/reader.sock')
        connection.sendall(struct.pack('!I',len(raw))+raw)
        def exact(size):
            data=b''
            while len(data)<size:
                chunk=connection.recv(size-len(data))
                if not chunk:raise ConnectionError('Incomplete lifecycle response')
                data+=chunk
            return data
        size=struct.unpack('!I',exact(4))[0]
        if size>4096:raise ConnectionError('Oversized lifecycle response')
        if json.loads(exact(size)).get('kind')!='ok':raise ConnectionError('Lifecycle request rejected')
except (OSError,ConnectionError,ValueError):
    print('Private reader lifecycle callback unavailable; no team message sent.',file=sys.stderr)
    sys.exit(1)
