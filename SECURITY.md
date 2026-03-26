# Security Policy

## Supported Versions

Security fixes are generally applied to the active development branch and included in the next release.

## Reporting a Vulnerability

Please do **not** open public issues for security vulnerabilities.

Instead:

1. Use private GitHub security reporting if enabled.
2. If unavailable, contact maintainers privately with:
   - A clear description of the issue
   - Reproduction steps
   - Potential impact
   - Suggested remediation (if known)

We will acknowledge reports promptly and coordinate remediation and disclosure.

## Secrets Handling

Never commit:

- API keys
- passwords
- JWT secrets
- encryption keys
- `.env` files

Use environment variables for all sensitive values.
