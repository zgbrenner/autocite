# AutoCite launch site

The public launch surface is an Astro static site. It has no runtime backend and no analytics dependency by default.

```bash
npm ci
npm run lint
npm test
npm run build
npm run audit:seo
npm run test:e2e
npm run lighthouse:ci
```

Production deployment is an explicit GitHub Actions workflow requiring a canonical HTTPS URL, Cloudflare account ID, API token, and production-environment approval.

The browser Citation Risk Scan is deliberately bounded. It checks only a small set of mechanical citation patterns, sends no pasted text, and produces share text containing counts and categories only.
