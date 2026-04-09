# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Audio Quality Checker, please report it responsibly.

**Do NOT open a public issue for security vulnerabilities.**

Instead, please email: **connect@usergy.ai**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge your email within 48 hours and work with you to understand and resolve the issue.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.6.x   | ✅ Yes             |
| < 4.6   | ❌ No              |

## Security Measures

This project implements:
- Input validation on all parameters
- File type and size validation
- Rate limiting to prevent abuse
- No sensitive data logging
- Configurable CORS policies

## Scope

Security concerns include:
- Authentication/authorization bypasses
- Remote code execution
- File upload vulnerabilities
- Data exposure
- Denial of service

Out of scope:
- Issues in third-party dependencies (report to them)
- Issues requiring physical access
- Social engineering
