# Stealth C2 Server and Agent Prototype

## Overview
This Python-based Command and Control (C2) system is designed for security research and ethical hacking simulations. It includes advanced stealth features to demonstrate evasion techniques in controlled environments. **Use strictly for educational purposes with explicit permission. Unauthorized use is illegal and unethical.**

Built for studying C2 architectures (RAT, dedicated server, botnet), it now includes obfuscation, DNS tunneling, anti-VM checks, and randomized communication to evade detection.

## Features
- **C2 Server**: HTTPS and DNS listeners, per-agent encryption, task management, file hosting.
- **Agent**: RAT-like with command execution, file uploads, screenshots, keylogging, DDoS simulation.
- **Stealth Enhancements**:
  - **Obfuscation**: Base64 encoding, dynamic variable names, executable packing (PyArmor-ready).
  - **Covert Channels**: DNS tunneling for tasks/results.
  - **Anti-Detection**: VM/debugger checks, randomized beacons.
  - **Persistence**: Scheduled tasks (Windows), cron jobs (Linux).
- **Security**: TLS, Fernet encryption, HMAC integrity checks.

## What Can Be Achieved
- **Research**: Test evasion against EDR/antivirus, study covert channels, develop detection rules.
- **Education**: Learn advanced C2 techniques, from obfuscation to network stealth.
- **Red Teaming**: Simulate sophisticated attacks in authorized pentests.
- **Outcomes**: Build expertise in malware analysis, network security, and defense strategies.

## Pros
- Highly educational for advanced C2 concepts.
- Stealth features mimic real-world threats (DNS tunneling, anti-VM).
- Flexible for RAT, server, or botnet use cases.
- Collaborative via GitHub for group research.

## Cons
- Still detectable by advanced EDR with behavioral analysis.
- DNS tunneling requires custom DNS setup for production.
- Limited platform support (Windows/Linux only).
- Ethical/legal risks if misused; always get consent.
- Dependencies (dnslib, cryptography, etc.) needed.

## Setup and Usage
1. **Install Dependencies**: `pip install requests cryptography pynput pillow dnslib`
2. **Generate SSL Certs**: `openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes`
3. **Run Server**: `python c2_server.py` (starts HTTPS and DNS listeners).
4. **Generate Payload**: Creates `agent_<id>.py` with obfuscation.
5. **Deploy Agent**: Run on a test VM (disable antivirus for testing).
6. **Tasks**: `task_agent("agent_001", "command", "whoami")` or `broadcast_task("ddos", {"url": "http://target.com", "duration": "30"})`.

For full code, see `c2_server.py`.

## Stealth Notes
- **Obfuscation**: Use PyArmor for stronger protection: `pyarmor pack agent_<id>.py`.
- **DNS Tunneling**: Configure a custom DNS server for real-world use.
- **Anti-VM**: Agent sleeps if VM/debugger detected.
- **Randomized Beacons**: Avoids predictable traffic patterns.

## Contributing
Fork, add features (e.g., DGA, macOS support), and submit PRs. Focus on ethical research!

## License
MIT License – Use responsibly with this notice.

## Warning
**For educational use only in controlled environments with permission. Misuse can lead to legal consequences.**