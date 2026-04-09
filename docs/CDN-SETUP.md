# CDN Setup Guide for Audio Quality Checker

## Option 1: Cloudflare (Recommended - Free)

Cloudflare provides free CDN, DDoS protection, and SSL.

### Setup Steps

1. **Create Cloudflare Account**
   - Go to https://dash.cloudflare.com/sign-up
   - Sign up with your email

2. **Add Your Domain**
   - Click "Add a Site"
   - Enter: `usergy.ai`
   - Select Free plan

3. **Update Nameservers**
   - Cloudflare will give you 2 nameservers (e.g., `xxx.ns.cloudflare.com`)
   - Go to your domain registrar (Namecheap)
   - Change nameservers from:
     ```
     pdns1.registrar-servers.com
     pdns2.registrar-servers.com
     ```
     To Cloudflare's nameservers

4. **Configure DNS Records**
   - Add A record: `tools` → `16.112.59.183` (Proxied ☁️)
   - This enables CDN caching

5. **Configure Caching Rules**
   - Go to Caching → Cache Rules
   - Create rule for static assets:
     ```
     If: URI Path contains "/audio-checker/" AND
         URI Path ends with ".js" OR ".css" OR ".png" OR ".jpg" OR ".svg" OR ".woff2"
     Then: Cache eligible, Edge TTL = 1 week
     ```

6. **Enable Performance Features**
   - Speed → Optimization → Enable Auto Minify (JS, CSS, HTML)
   - Speed → Optimization → Enable Brotli compression

### Benefits After Setup
- Global CDN (280+ data centers)
- DDoS protection
- Free SSL certificate management
- ~50% faster for international users
- Analytics dashboard

---

## Option 2: AWS CloudFront

Since you're already on AWS, CloudFront is a native option.

### Setup Steps

1. **Create CloudFront Distribution**
   ```bash
   aws cloudfront create-distribution \
     --origin-domain-name tools.usergy.ai \
     --default-root-object index.html
   ```

2. **Configure Origin**
   - Origin Domain: `16.112.59.183` or `tools.usergy.ai`
   - Protocol: HTTPS only
   - Origin Path: `/audio-checker`

3. **Configure Behaviors**
   - Default: Forward all, cache based on headers
   - `/api/*`: No cache
   - `*.css`, `*.js`: Cache 1 week

4. **Update DNS**
   - Create CNAME: `tools.usergy.ai` → CloudFront distribution URL

### Costs
- First 1TB/month: ~$0.085/GB
- Estimated: $5-20/month depending on traffic

---

## Current Server-Side Caching (Already Configured)

Even without a CDN, nginx is configured for optimal caching:

| Asset Type | Cache Duration |
|------------|----------------|
| CSS, JS, Images | 1 week |
| HTML | 10 minutes |
| API responses | No cache |

This means repeat visitors will load cached assets from their browser.

---

## Recommendation

**Start with Cloudflare (free)** - it provides:
- Global CDN
- DDoS protection
- Better performance for international users
- No cost

Only consider CloudFront if you need:
- Tighter AWS integration
- Custom Lambda@Edge functions
- Specific compliance requirements
