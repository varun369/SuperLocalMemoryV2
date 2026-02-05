# Security Policy

## SuperLocalMemory V2 Security

This document outlines the security policy for SuperLocalMemory V2, including supported versions, vulnerability reporting procedures, and our privacy-first approach.

---

## Table of Contents

- [Supported Versions](#supported-versions)
- [Reporting Vulnerabilities](#reporting-vulnerabilities)
- [Security Architecture](#security-architecture)
- [Data Privacy](#data-privacy)
- [Threat Model](#threat-model)
- [Best Practices](#best-practices)
- [Security Updates](#security-updates)

---

## Supported Versions

### Currently Supported

| Version | Status | Support Level | Security Updates |
|---------|--------|---------------|------------------|
| 2.0.x   | Active | Full support  | Yes              |
| 1.x.x   | Legacy | Limited       | Critical only    |

### Support Timeline

- **Active support:** Latest 2.x release receives all security updates
- **Legacy support:** Previous major version (1.x) receives critical security fixes only
- **End of life:** Versions older than 1.x are no longer supported

**Recommendation:** Always use the latest 2.x release for best security.

---

## Reporting Vulnerabilities

### Security-First Approach

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### Reporting Process

**DO NOT create a public GitHub issue for security vulnerabilities.**

Instead, follow these steps:

#### Step 1: Private Disclosure

Use GitHub Security Advisories or email security details to the project maintainers.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)
- Your contact information

#### Step 2: Acknowledgment

We will acknowledge your report within **48 hours**.

#### Step 3: Investigation

Our team will:
- Verify the vulnerability
- Assess severity and impact
- Develop a fix
- Test the fix thoroughly

Typical timeline: **5-10 business days**

#### Step 4: Disclosure

Once fixed:
- Security advisory published
- Fix released in new version
- Reporter credited (unless anonymity requested)

### Severity Levels

We use the following severity classification:

**Critical:**
- Remote code execution
- Privilege escalation
- Data exfiltration

**High:**
- Authentication bypass
- SQL injection
- Local privilege escalation

**Medium:**
- Information disclosure
- Denial of service
- Path traversal

**Low:**
- Minor information leaks
- Configuration issues

---

## Security Architecture

### Local-First = Privacy-First

SuperLocalMemory V2 is designed with security and privacy as foundational principles.

### Core Security Principles

#### 1. Zero External Communication

**Guarantee:** The system makes **zero** external API calls or network requests.

**Implementation:**
- No telemetry
- No auto-updates
- No analytics
- No crash reporting to external services

#### 2. Local-Only Data Storage

**All data stored locally:**
- Database: `~/.claude-memory/memory.db`
- Backups: `~/.claude-memory/backups/`
- Profiles: `~/.claude-memory/profiles/`
- Vectors: `~/.claude-memory/vectors/`

**No cloud synchronization** by default.

#### 3. Standard Filesystem Permissions

**Security relies on operating system:**
- Unix/Linux: Standard file permissions (chmod 600)
- macOS: FileVault encryption (user responsibility)
- Windows: NTFS permissions

**Recommendation:**
```bash
# Secure database file
chmod 600 ~/.claude-memory/memory.db

# Secure entire directory
chmod 700 ~/.claude-memory/
```

#### 4. No Built-in Authentication

**Design decision:** Authentication is handled by the OS.

**Rationale:**
- Single-user system (runs on local machine)
- OS-level user authentication sufficient
- No network exposure = no remote authentication needed

**Multi-user environments:**
- Use separate OS user accounts
- Each user gets isolated `~/.claude-memory/`

---

## Data Privacy

### What Data is Stored

**User-provided data:**
- Memory content (text you add)
- Tags and metadata
- Configuration settings

**System-generated data:**
- Timestamps
- Memory IDs
- Graph cluster information
- Learned patterns

**NOT stored:**
- Personally identifiable information (unless you add it)
- System information
- Usage analytics
- Telemetry

### Data Lifecycle

```
User Input → Local Storage → Processing → Local Output
     ↓
No external transmission at any stage
```

### Data Retention

**User control:**
- Keep data forever (default)
- Delete selectively (per-memory deletion)
- Reset database (soft/hard reset options)
- Archive to cold storage (compression system)

**Automatic deletion:** None. All deletion is user-initiated.

### GDPR Compliance

**For EU users:**
- Right to access: Full access to all data (it is on your machine)
- Right to deletion: Use `memory-reset` commands
- Right to portability: Export database file
- Right to rectification: Edit memories directly

**No data controller:** You control your data completely.

---

## Threat Model

### What We Protect Against

#### 1. Data Integrity

**Protection:**
- SQLite ACID transactions
- Automatic backups before destructive operations
- Schema validation

**Mitigations:**
- Crash during write → Database rollback
- Corrupted data → Restore from backup
- Accidental deletion → Soft delete with recovery

#### 2. Unauthorized Local Access

**Limited protection:**
- Filesystem permissions (user responsibility)
- No application-level encryption (by design)

**Recommendation:** Use full-disk encryption (FileVault, LUKS, BitLocker).

#### 3. Code Injection

**Protection:**
- Parameterized SQL queries (no string concatenation)
- Input validation
- No eval or exec on user input

### What We DON'T Protect Against

#### 1. Physical Access

**Not protected:**
- Attacker with physical access to machine
- Attacker with root/admin privileges
- Forensic data recovery from disk

**Mitigation:** Use full-disk encryption.

#### 2. Malware on Same Machine

**Not protected:**
- Keyloggers
- Screen capture malware
- Filesystem-level malware

**Mitigation:** Standard OS security practices (antivirus, firewall).

#### 3. Supply Chain Attacks

**Limited protection:**
- Python standard library only (reduces dependency risk)
- Open source (code can be audited)
- No auto-updates (user initiates updates)

**Risk:** Compromised Python interpreter or OS.

---

## Best Practices

### For Users

#### 1. Enable Full-Disk Encryption

**macOS:**
```
System Preferences → Security & Privacy → FileVault
```

**Linux:**
```
Use LUKS encryption during installation
```

**Windows:**
```
Control Panel → System and Security → BitLocker
```

#### 2. Secure Filesystem Permissions

```bash
# Lock down .claude-memory directory
chmod 700 ~/.claude-memory/

# Lock down database
chmod 600 ~/.claude-memory/memory.db

# Lock down backups
chmod 700 ~/.claude-memory/backups/
```

#### 3. Regular Backups

```bash
# Manual backup with timestamp
cp ~/.claude-memory/memory.db ~/Backups/memory-backup.db
```

#### 4. Avoid Storing Secrets

**DO NOT store:**
- API keys
- Passwords
- Private keys
- Tokens
- Personal identification numbers

**If you must:**
- Use a dedicated password manager instead
- Or encrypt sensitive memories manually

### For Developers

#### 1. Code Review

**Every PR must:**
- Be reviewed by at least one maintainer
- Pass automated security checks
- Not introduce external dependencies without justification

#### 2. Input Validation

Validate all user input before processing.

#### 3. Parameterized Queries

Always use parameterized SQL queries to prevent injection attacks.

#### 4. No Secrets in Code

- Never hardcode API keys
- Never commit credentials
- Use `.gitignore` for sensitive files

---

## Security Updates

### Update Notification

**How you will be notified:**
1. GitHub Security Advisories
2. Release notes (CHANGELOG.md)
3. Project discussions

**What to do:**
1. Read the security advisory
2. Assess impact on your system
3. Update to latest version
4. Verify fix is applied

### Update Process

```bash
# Backup current version
cp -r ~/.claude-memory ~/.claude-memory.backup

# Pull latest code
cd ~/path/to/SuperLocalMemoryV2-repo
git pull origin main

# Reinstall
./install.sh

# Verify version
memory-status
```

---

## Security Audit

### Self-Audit Checklist

**For users:**
- [ ] Full-disk encryption enabled
- [ ] `.claude-memory/` directory has restrictive permissions
- [ ] Regular backups configured
- [ ] No secrets stored in memories
- [ ] Using latest version

**For developers:**
- [ ] Code reviewed before merge
- [ ] No external dependencies without justification
- [ ] Input validation on user data
- [ ] Parameterized SQL queries
- [ ] No secrets in code or config

---

## Contact

For security issues, please use GitHub Security Advisories or contact project maintainers directly.

**Response Time:**
- Acknowledgment: less than 48 hours
- Initial assessment: less than 5 business days
- Patch release: Varies by severity (critical: less than 7 days)

---

## Legal

### Responsible Disclosure

We appreciate responsible disclosure of security vulnerabilities.

**Safe harbor:**
- Good faith security research is welcomed
- We will not pursue legal action for responsible disclosure
- We request you do not publicly disclose until patch is available

### Disclaimer

SuperLocalMemory V2 is provided "as is" without warranty. See [LICENSE](LICENSE) for full terms.

**User responsibility:**
- Securing your system
- Enabling encryption
- Following best practices
- Keeping software updated

---

**Security is a shared responsibility.**

We build secure software. You secure your environment. Together we protect your data.
