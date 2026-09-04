LOG = """systemd-coredump: Process 65630 (python3.14) of user 1000 dumped core.
signal: SIGSEGV
Stack trace of thread 65630: #0 libssl.so.3 SSL_do_handshake ...
Journal: openssl-3.5.1-1 upgraded, python-requests connection reset mid-handshake
Note: system memory at 61%, no pressure; disk 43% used."""

TASK = {
    "id": "T02",
    "title": "Crash log diagnosis",
    "category": "log-diagnosis",
    "prompt": f"A process crashed on this machine. Given the coredump summary and journal lines below, name in one short sentence which component failed and how.\n\n{LOG}",
    "checkers": [
        {"type": "contains_all", "values": ["libssl", "handshake"]},
        {"type": "contains_none", "values": ["out of memory", "oom", "disk full"]},
    ],
    "timeout_s": 120,
    "max_tokens": 4000,
    "judge": False,
}