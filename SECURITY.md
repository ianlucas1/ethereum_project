# Security Policy

## 🔒 Automated gates
| Tool | Threshold | Job |
|------|-----------|-----|
| **Bandit** | fail ≥ **Medium** severity | `static-security` |
| **Safety** | fail on **any** CVE | `static-security` |
| **CodeQL** | GitHub default | `CodeQL` |

## 🗓 Dependency hygiene
* Weekly Dependabot (pip & GitHub Actions)
* Nightly `scripts/qa_audit.py --mode=full` audit

## 📧 Reporting a vulnerability
Email **security@your-domain.io** (PGP key on Keybase) or open a **private security advisory** in GitHub → Security → Advisories.  
We triage within **24 h** and patch critical issues within **72 h**.
```

*Add this line to the end of `README.md`:*

```
For detailed config snippets see **docs/config-reference/**.
```
