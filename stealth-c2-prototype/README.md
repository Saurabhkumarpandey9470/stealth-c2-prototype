# Stealth C2 Server and Agent Prototype

## Overview
This Python-based Command and Control (C2) system is designed for security research and ethical hacking simulations in controlled environments. It demonstrates advanced stealth techniques to evade detection, making it ideal for studying C2 architectures (Remote Access Trojan, dedicated server, botnet) and developing defensive countermeasures. **Use strictly for educational purposes with explicit, written permission. Unauthorized use is illegal and unethical, potentially violating laws like the Computer Fraud and Abuse Act (CFAA) or equivalent regulations.**

The tool features obfuscation, DNS tunneling with a custom DNS server, Domain Generation Algorithm (DGA), anti-VM/anti-debugging, and cross-platform persistence (Windows/Linux/macOS). It supports tasks like command execution, file uploads/downloads, screenshots, keylogging, remote shell, system information gathering, and DDoS simulation, suitable for red teaming, malware analysis, and educational workshops.

## Features
- **C2 Server**: Runs HTTPS (port 8443) and custom DNS (port 53) listeners, manages agents, assigns tasks, and hosts files.
- **Agent**: RAT-like functionality with command execution, file uploads/downloads, screenshots, keylogging, remote shell, system info, and DDoS simulation.
- **Stealth Enhancements**: Obfuscation, DNS tunneling, DGA, anti-VM checks, and advanced persistence.
- **Security**: TLS, per-agent Fernet encryption, and HMAC for secure communication.
- **Cross-Platform**: Persistence on Windows (schtasks), Linux (cron), and macOS (LaunchAgent).
- **New Tasks**: Remote shell for interactive commands and system info for reconnaissance.

## What Can Be Achieved
- **Research**: Test evasion against EDR/antivirus, develop detection rules for DNS tunneling, DGA, or persistence.
- **Education**: Learn advanced C2 techniques, including covert channels, obfuscation, and cross-platform persistence.
- **Red Teaming**: Simulate sophisticated attacks in authorized penetration tests, mimicking APT-like behavior.
- **Collaboration**: Enable group contributions via GitHub for CTFs, workshops, or research papers.
- **Outcomes**: Build expertise in malware analysis, network security, and defense strategy development.

## Key Stealth Enhancements
- **Advanced Obfuscation**:  
  The agent code is base64-encoded and wrapped in an `exec` statement.  
  Dynamic variable names (e.g., `v<random>`) prevent static analysis.  
  *To Do More*: Use PyArmor (`pip install pyarmor`) to obfuscate further: `pyarmor pack -e "--onefile" agent_<agent_id>.py`. This creates a standalone executable.

- **Randomized Communication**:  
  Beacon intervals are randomized (`random.randint(30, 120)` seconds) to avoid predictable patterns.  
  *To Do More*: Implement a Domain Generation Algorithm (DGA):  
  ```python
  def generate_domain(seed):
      import hashlib
      return hashlib.md5((seed + str(int(time.time() // 86400))).encode()).hexdigest()[:10] + ".com"

  - **Covert Communication (DNS Tunneling)**
  Uses dnslib to send tasks/results via DNS TXT records, which are less likely to be flagged than HTTP traffic.
Example: Agent queries task.agent_001.c2.example.com, server responds with encrypted task in TXT record.
Note: Requires a controlled DNS server in production; here, it uses a public DNS for testing.
- **Anti-VM/Anti-Debugging**
Checks for VM/debugger presence using IsDebuggerPresent, /proc/xen, and BIOS serial number length.
If detected, the agent sleeps for an hour to avoid analysis.
- **Advanced Persistence**
Windows: Uses schtasks for scheduled tasks (less detectable than registry).
Linux: Retains cron job but can be enhanced with systemd services.
- **Encrypted Payloads**
Per-agent Fernet keys and HMAC ensure secure, integrity-checked communication.
DNS tunneling encrypts payloads within TXT records.

## Additional Stealth Features##
- **Custom DNS Server** Runs a DNS server on port 53 to handle tunneling queries directly, eliminating reliance on public DNS servers.
- **Domain Generation Algorithm (DGA)** Generates daily-changing domains (e.g., a1b2c3d4e5.c2.example.com) to evade domain-based blocking.
- **macOS Persistence** Uses LaunchAgent plist files to run the agent at login on macOS systems.

Pros
Highly Stealthy: DNS tunneling, DGA, anti-VM checks, and randomized beacons evade most network and endpoint detection.
Cross-Platform: Supports persistence on Windows, Linux, and macOS, broadening research applicability.
Educational: Teaches advanced evasion techniques like DGA, DNS tunneling, and anti-debugging.
Flexible: Adapts to RAT, dedicated server, or botnet scenarios with diverse task types (e.g., remote shell, system info).
Secure: TLS, Fernet encryption, and HMAC ensure safe communication in controlled demos.
Collaborative: GitHub-ready for group contributions, ideal for workshops or CTFs

