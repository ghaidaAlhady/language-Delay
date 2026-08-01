# Security Policy

Do not report real child or parent personal data in public issues. Do not commit API keys, tokens, local databases, user uploads, generated reports, or logs containing sensitive content. Use synthetic data for testing.


## Hosted beta safeguards

- Keep all production secrets in the Render/Netlify dashboards; never place them in Git.
- Production startup requires PostgreSQL, a strong random `SECRET_KEY`, and exact HTTPS
  `CORS_ORIGINS`; unsafe production configuration fails closed.
- Use Neon or another managed PostgreSQL service with backups. Local SQLite is development-only.
- The Docker build context is protected by `.dockerignore`, including `.env`, databases,
  virtual environments, Node dependencies, logs, reports, and test artifacts.
- Review hosting logs before public use and confirm they contain no tokens, prompts, child names,
  parent emails, or raw provider responses.
- The prepared free-host deployment is a beta/demo, not a production healthcare environment.
