import json
import subprocess
import threading
import time
import os

class PyrightLSPClient:
    def __init__(self):
        # Let's ensure node wrapper works or invoke `pyright --stdio` directly if pyright-langserver is failing.
        # Actually `pyright-langserver` is correct for pip installs.
        self.process = subprocess.Popen(
            ["pyright-langserver", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.message_id = 1
        self.responses = {}
        self.lock = threading.Lock()

        self.reader_thread = threading.Thread(target=self._read_stdout)
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def _read_stdout(self):
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            line = line.decode('utf-8')
            if line.startswith('Content-Length:'):
                length = int(line.split(':')[1].strip())
                self.process.stdout.readline() # read the \r\n
                content = self.process.stdout.read(length).decode('utf-8')
                try:
                    data = json.loads(content)
                    # print("DEBUG RECV:", data)
                    if 'id' in data:
                        with self.lock:
                            self.responses[data['id']] = data
                except Exception as e:
                    print(f"Error parsing JSON: {e}, Content: {content}")

    def _send_request(self, method, params):
        req_id = self.message_id
        self.message_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        content = json.dumps(message)
        # print("DEBUG SEND:", content)
        payload = f"Content-Length: {len(content)}\r\n\r\n{content}"
        self.process.stdin.write(payload.encode('utf-8'))
        self.process.stdin.flush()
        return req_id

    def _send_notification(self, method, params):
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        content = json.dumps(message)
        # print("DEBUG NOTIFY:", content)
        payload = f"Content-Length: {len(content)}\r\n\r\n{content}"
        self.process.stdin.write(payload.encode('utf-8'))
        self.process.stdin.flush()

    def wait_for_response(self, req_id, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                if req_id in self.responses:
                    return self.responses[req_id]
            time.sleep(0.1)
        return None

    def initialize(self, root_path):
        req_id = self._send_request("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{root_path}",
            "capabilities": {}
        })
        return self.wait_for_response(req_id)

    def initialized(self):
        self._send_notification("initialized", {})

    def did_open(self, filepath, text):
        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": f"file://{filepath}",
                "languageId": "python",
                "version": 1,
                "text": text
            }
        })

    def hover(self, filepath, line, character):
        req_id = self._send_request("textDocument/hover", {
            "textDocument": {"uri": f"file://{filepath}"},
            "position": {"line": line, "character": character}
        })
        return self.wait_for_response(req_id)

    def close(self):
        self.process.terminate()

if __name__ == "__main__":
    import os

    filepath = os.path.abspath("tests/fixtures/type_spike_fixture.py")
    with open(filepath, "r") as f:
        text = f.read()

    client = PyrightLSPClient()
    print("Initializing Pyright LSP...")
    client.initialize(os.path.dirname(filepath))
    client.initialized()

    print("Opening document...")
    client.did_open(filepath, text)
    time.sleep(5) # Increase sleep to ensure Pyright has analyzed the file

    # 0-indexed positions based on:
    # 0: from dataclasses import dataclass
    # 1: import torch
    # 2: from torch import nn
    # ...
    # 17:     x = batch.features
    # 18:     logits = model(x)
    # 19:     loss = logits.sum()
    # 20:
    # 21:     optimizer.zero_grad()
    # 22:     loss.backward()
    # 23:     optimizer.step()

    positions = [
        ("batch", 17, 9),
        ("batch.features", 17, 15),
        ("x", 17, 4),
        ("model", 18, 14),
        ("model(x)", 18, 18),
        ("logits", 18, 4),
        ("logits.sum", 19, 14),
        ("loss", 19, 4),
        ("optimizer", 21, 5),
        ("optimizer.zero_grad", 21, 15),
        ("optimizer.step", 23, 15),
    ]

    print("\n--- Hover Results ---")
    for name, line, char in positions:
        resp = client.hover(filepath, line, char)
        if resp and 'result' in resp and resp['result']:
            val = resp['result']['contents']['value']
            parts = val.split("```python")
            if len(parts) > 1:
                t = parts[1].split("```")[0].strip()
                print(f"{name}: {t}")
            else:
                print(f"{name}: {val}")
        else:
            print(f"{name}: No hover info")

    client.close()
