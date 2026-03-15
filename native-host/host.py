#!/usr/bin/env python3
"""
Native messaging host that bridges Firefox extension messages to Discord Rich Presence.
Communicates with Discord via local IPC (named pipe on Windows).
"""

import ctypes
import ctypes.wintypes
import json
import os
import struct
import sys
import uuid

DISCORD_CLIENT_ID = "1482383187882545233"


class DiscordIPC:
    OP_HANDSHAKE = 0
    OP_FRAME = 1

    def __init__(self, client_id):
        self.client_id = client_id
        self.pipe_handle = None
        self.is_connected = False

    def connect(self):
        if self.is_connected:
            return True

        kernel32 = ctypes.windll.kernel32
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3

        for pipe_num in range(10):
            pipe_path = f"\\\\.\\pipe\\discord-ipc-{pipe_num}"
            try:
                handle = kernel32.CreateFileW(
                    pipe_path, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None
                )
                if handle in (-1, 0xFFFFFFFF):
                    continue

                self.pipe_handle = handle
                self._send(self.OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
                response = self._recv()

                if response and response.get("cmd") == "DISPATCH" and response.get("evt") == "READY":
                    self.is_connected = True
                    return True
                else:
                    kernel32.CloseHandle(handle)
                    self.pipe_handle = None
            except Exception:
                continue
        return False

    def _send(self, op, data):
        payload = json.dumps(data).encode("utf-8")
        msg = struct.pack("<II", op, len(payload)) + payload
        written = ctypes.wintypes.DWORD()
        ctypes.windll.kernel32.WriteFile(
            self.pipe_handle, msg, len(msg), ctypes.byref(written), None
        )

    def _recv(self):
        try:
            buf = ctypes.create_string_buffer(65536)
            nread = ctypes.wintypes.DWORD()
            ok = ctypes.windll.kernel32.ReadFile(
                self.pipe_handle, buf, 65536, ctypes.byref(nread), None
            )
            if not ok or nread.value < 8:
                return None
            data = buf.raw[: nread.value]
            _op, length = struct.unpack("<II", data[:8])
            return json.loads(data[8 : 8 + length].decode("utf-8"))
        except Exception:
            return None

    def set_activity(self, activity):
        if not self.is_connected:
            if not self.connect():
                return False
        nonce = str(uuid.uuid4())
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": activity},
            "nonce": nonce,
        }
        try:
            self._send(self.OP_FRAME, payload)
            self._recv()
            return True
        except Exception:
            self.is_connected = False
            return False

    def clear_activity(self):
        if not self.is_connected:
            return False
        nonce = str(uuid.uuid4())
        try:
            self._send(self.OP_FRAME, {
                "cmd": "SET_ACTIVITY",
                "args": {"pid": os.getpid()},
                "nonce": nonce,
            })
            self._recv()
            return True
        except Exception:
            self.is_connected = False
            return False

    def close(self):
        try:
            if self.pipe_handle:
                ctypes.windll.kernel32.CloseHandle(self.pipe_handle)
        except Exception:
            pass
        self.pipe_handle = None
        self.is_connected = False


def read_message():
    raw = sys.stdin.buffer.read(4)
    if not raw or len(raw) < 4:
        return None
    length = struct.unpack("<I", raw)[0]
    if length == 0:
        return None
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode("utf-8")) if data else None


def send_message(msg):
    encoded = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


STATE_FILE = os.path.join(os.environ.get("APPDATA", ""), "SyncView", "now_playing.json")


def write_state(title=None, channel=None, connected=False):
    """Write current playback state to a shared file for SyncView.exe to read."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        state = {"title": title, "channel": channel, "connected": connected}
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def main():
    discord = DiscordIPC(DISCORD_CLIENT_ID)

    if discord.connect():
        send_message({"type": "CONNECTED"})
        write_state(connected=True)
    else:
        send_message({"type": "DISCONNECTED", "error": "Could not connect to Discord"})
        write_state(connected=False)

    while True:
        try:
            message = read_message()
            if message is None:
                break

            if message["type"] == "SET_ACTIVITY":
                activity = message.get("activity", {})

                # Build clean activity payload — only include non-empty fields
                discord_activity = {}
                if activity.get("details"):
                    discord_activity["details"] = activity["details"]
                if activity.get("state"):
                    discord_activity["state"] = activity["state"]
                if activity.get("timestamps"):
                    discord_activity["timestamps"] = activity["timestamps"]
                if activity.get("assets"):
                    discord_activity["assets"] = activity["assets"]
                if activity.get("buttons"):
                    discord_activity["buttons"] = activity["buttons"]

                success = discord.set_activity(discord_activity)
                if success:
                    send_message({"type": "CONNECTED"})
                    write_state(title=activity.get("details"), channel=activity.get("state"), connected=True)
                else:
                    if discord.connect():
                        discord.set_activity(discord_activity)
                        send_message({"type": "CONNECTED"})
                        write_state(title=activity.get("details"), channel=activity.get("state"), connected=True)
                    else:
                        send_message({"type": "DISCONNECTED"})
                        write_state(connected=False)

            elif message["type"] == "CLEAR_ACTIVITY":
                discord.clear_activity()
                send_message({"type": "CONNECTED"})
                write_state(connected=True)

        except Exception as e:
            send_message({"type": "ERROR", "error": str(e)})

    write_state(connected=False)
    discord.close()


if __name__ == "__main__":
    main()
