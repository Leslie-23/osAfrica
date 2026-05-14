#!/usr/bin/env python3
"""osAfrica Login Greeter — AI-powered TUI login screen.

Communicates with greetd via its IPC protocol to authenticate users.
Shows an AI welcome message after successful login.
"""

from __future__ import annotations

import json
import os
import socket
import struct
import sys
from getpass import getpass

GREETD_SOCK = os.environ.get("GREETD_SOCK", "")

BANNER = """\033[1;32m
   ╔═══════════════════════════════════════╗
   ║                                       ║
   ║         Welcome to osAfrica           ║
   ║       AI-Native Linux Desktop         ║
   ║                                       ║
   ╚═══════════════════════════════════════╝
\033[0m"""


def greetd_send(sock: socket.socket, msg: dict) -> dict:
    payload = json.dumps(msg).encode("utf-8")
    sock.sendall(struct.pack("=I", len(payload)) + payload)

    length_data = sock.recv(4)
    if len(length_data) < 4:
        raise ConnectionError("greetd disconnected")
    length = struct.unpack("=I", length_data)[0]
    response = sock.recv(length)
    return json.loads(response.decode("utf-8"))


def main():
    print(BANNER)

    if not GREETD_SOCK:
        print("\033[33mNot running under greetd. Enter demo mode.\033[0m\n")
        username = input("Username: ")
        print(f"\n\033[32mWelcome, {username}! Starting osAfrica desktop...\033[0m\n")
        return

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(GREETD_SOCK)

    try:
        username = input("  Username: ")

        resp = greetd_send(sock, {
            "type": "create_session",
            "username": username,
        })

        if resp.get("type") == "error":
            print(f"\033[31m  Error: {resp.get('description', 'Unknown error')}\033[0m")
            sys.exit(1)

        if resp.get("type") == "auth_message":
            password = getpass("  Password: ")
            resp = greetd_send(sock, {
                "type": "post_auth_message_response",
                "response": password,
            })

        if resp.get("type") == "success":
            print(f"\n\033[32m  Welcome, {username}! Starting osAfrica desktop...\033[0m\n")
            greetd_send(sock, {
                "type": "start_session",
                "cmd": ["osa-compositor"],
                "env": [
                    f"XDG_SESSION_TYPE=wayland",
                    f"XDG_CURRENT_DESKTOP=osAfrica",
                    f"USER={username}",
                    f"HOME=/home/{username}",
                ],
            })
        else:
            print(f"\033[31m  Authentication failed.\033[0m")
            sys.exit(1)

    finally:
        sock.close()


if __name__ == "__main__":
    main()
