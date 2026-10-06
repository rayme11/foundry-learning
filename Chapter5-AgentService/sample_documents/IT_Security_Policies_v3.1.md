# Contoso Corporation IT Security Policies

## Version: 3.1 | Effective: March 15, 2024 | Classification: Confidential

---

## 1. Purpose & Scope

This document defines the information security policies for Contoso Corporation. It applies to all employees, contractors, third parties, and systems that process, store, or transmit Contoso data.

**Compliance References**: ISO 27001, SOC 2 Type II, GDPR, CCPA, NIST CSF

---

## 2. Data Classification

All data must be classified at creation:

| Classification | Description | Examples | Handling |
|----------------|-------------|----------|----------|
| **Public** | Approved for external release | Marketing materials, public APIs | No restrictions |
| **Internal** | Company-internal use only | Org charts, internal memos | Authenticated access |
| **Confidential** | Sensitive business data | Financials, roadmaps, customer lists | Encrypted at rest/transit, need-to-know |
| **Restricted** | Highly sensitive/regulated | PII, PHI, credentials, keys | Encrypted, logged, DLP enforced |

---

## 3. Access Control

### 3.1 Authentication
- **MFA Required**: All human access (Microsoft Entra ID + Authenticator/FIDO2)
- **Password Policy**: 14 chars, complexity, rotation 90 days (service accounts: 30 days)
- **Service Accounts**: Managed identities preferred; no interactive login

### 3.2 Authorization (Least Privilege)
- **RBAC**: Role-based access via Entra ID groups
- **Access Reviews**: Quarterly for Confidential/Restricted data
- **JIT Access**: Privileged roles via PIM (max 4 hours)
- **Offboarding**: Access revoked within 4 hours of departure

### 3.3 Network Segmentation
- **Zero Trust**: No implicit trust by network location
- **Micro-segmentation**: Workload-to-workload encryption (mTLS)
- **Egress Control**: Default deny, allow-list for external APIs

---

## 4. Approved Tools & Platforms

### 4.1 Communication
| Category | Approved Tools | Prohibited |
|----------|----------------|------------|
| Chat | Microsoft Teams, Slack (Enterprise Grid) | Personal WhatsApp, Discord, Telegram |
| Email | Outlook (Exchange Online) | Personal Gmail/Yahoo for work |
| Video | Teams, Zoom (Enterprise) | Consumer Zoom, Google Meet |

### 4.2 File Sharing & Collaboration
| Data Classification | Approved |
|---------------------|----------|
| Public | SharePoint (Anyone link), Teams |
| Internal | SharePoint (Org link), Teams, OneDrive |
| Confidential | SharePoint (Specific people), OneDrive (Specific people), **Encrypted email** |
| Restricted | **Secure File Transfer Portal**, Encrypted email (S/MIME), **No Teams/Slack** |

> ⚠️ **Never share Confidential/Restricted data via Slack, Teams chat, or unencrypted email**

### 4.3 Development Tools
- **Source Control**: GitHub Enterprise (Contoso org only)
- **CI/CD**: GitHub Actions, Azure DevOps
- **Artifacts**: GitHub Packages, Azure Container Registry
- **Secrets**: Azure Key Vault, GitHub Environments secrets
- **Prohibited**: Personal GitHub, public npm/PyPI for proprietary code

---

## 5. Device & Endpoint Security

### 5.1 Managed Devices (Required for Confidential+ access)
- **MDM**: Intune enrollment mandatory
- **Encryption**: BitLocker (Windows), FileVault (macOS)
- **EDR**: Microsoft Defender for Endpoint
- **Patch**: Critical patches within 72 hours

### 5.2 BYOD (Internal data only)
- **Intune App Protection**: Required for Outlook, Teams, SharePoint apps
- **No Confidential/Restricted data** on personal devices
- **Remote Wipe**: Company can wipe corporate data

---

## 6. Incident Response

### 6.1 Reporting
- **Security Incidents**: security@contoso.com or #security-incidents (Teams)
- **Lost Device**: IT Service Desk within 1 hour
- **Phishing**: Forward to phish@contoso.com

### 6.2 Severity Levels
| SEV | Definition | Response Time | Examples |
|-----|------------|---------------|----------|
| **SEV-1** | Active breach, data exfiltration | 15 min | Ransomware, confirmed PII leak |
| **SEV-2** | Vulnerability exploited, no data loss | 1 hour | Compromised credential, malware |
| **SEV-3** | Policy violation, potential risk | 4 hours | MFA bypass attempt, misconfig |
| **SEV-4** | Low risk, hygiene issue | 24 hours | Expired cert, weak password |

### 6.3 Communication
- **Internal**: #security-incidents channel, stakeholder notifications
- **External**: Legal/Compliance approval required
- **Customers**: 72-hour notification for breaches (GDPR)

---

## 7. Encryption Standards

| State | Algorithm | Key Management |
|-------|-----------|----------------|
| **At Rest** | AES-256 | Azure Key Vault (CMK option) |
| **In Transit** | TLS 1.3 (min 1.2) | Managed certs (App Gateway, Front Door) |
| **Email (Restricted)** | S/MIME or PGP | User-managed keys |
| **File Transfer** | SFTP/HTTPS + AES-256 | Per-transfer keys |

---

## 8. Logging & Monitoring

- **Retention**: 1 year hot, 7 years cold (Azure Log Analytics)
- **SIEM**: Microsoft Sentinel
- **Key Logs**: Entra ID sign-ins, Key Vault access, DLP alerts, Defender alerts
- **Alerting**: SEV-1/2 → PagerDuty (24/7), SEV-3/4 → Teams (business hours)

---

## 9. Vendor & Third-Party Risk

- **Assessment Required**: Before sharing Confidential/Restricted data
- **DPA/BAA**: Signed for all processors
- **SOC 2 Type II**: Required for Confidential+ processors
- **Annual Review**: Critical vendors reassessed yearly

---

## 10. Training & Awareness

- **Annual**: Mandatory security training (90 min)
- **Quarterly**: Phishing simulations (failures → remedial training)
- **Role-Based**: Developers (secure coding), Admins (privileged access)

---

## 11. Policy Enforcement

Violations may result in:
- **First**: Warning + remedial training
- **Second**: Formal write-up, access restriction
- **Third**: Termination (gross misconduct for Restricted data exposure)

---

## 12. References & Related Documents

- [Data Classification Procedure](IT_Data_Classification_Procedure_v2.0.pdf)
- [Incident Response Playbook](IT_IR_Playbook_v1.5.pdf)
- [Vendor Assessment Checklist](IT_Vendor_Checklist_v3.0.xlsx)
- [Approved Software List](IT_Approved_Software_v2024_Q1.csv)

---

*Document Owner: CISO Office | Review Cycle: Semi-annual | Next Review: September 2024*
*Questions: security@contoso.com | Emergency: +1-800-CONTO-SEC*