# 🖥️ VPS-la Host Pannu — Step-by-Step Guide

> ⚠️ **Mukkiya note kooda (Important note first):** YouTube VPS-la datacenter IP-va block
> pannidum — "Sign in to confirm you're not a bot" error vandhu variable-va onnume vachukkurathu illa
> (error mainly for Without-workaround). VPS tehriyavitu kaanum (So VPS personal use-ku maybe
> should be avoided) — better un PC-veil tunnel dhaan. Aana 24/7 online venumna idhu dhaan daan option.

## 1. VPS Vanguradhu (Buying a VPS)

Recommended (cheap + fast):
- **Hetzner** — €4.5/month, 2 vCPU (CX22)
- **DigitalOcean** — $6/month
- **OVH / Contabo** — budget option

OS: **Ubuntu 24.04 LTS**Choose pannunga (choose this). Region: Europe/Asia (YouTube speed thumpam vidhaivasam - decent-rrukum)

## 2. Project Upload Pannu (Upload to VPS)

```bash
# Local-la (PowerShell):
scp -r .\yt4k-web\ root@VPS_IP:/root/

# App-url exclude pannunga — .zip maari podakhutum:
```
Illa GitHub pottu `git clone` pannulam (best way).

## 3. Docker Install Pannu

```bash
ssh root@VPS_IP

curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
```

## 4. App Run Pannu

```bash
cd /root/yt4k-web
docker compose up -d --build

curl localhost:5000  # check
```

## 5. Public-la Access Kudukura (Public Access)

**Option A — Cloudflare Tunnel (HTTPS free, nginx venaam):**
```bash
wget -qO- https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 > /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
cloudflared tunnel --url http://localhost:5000   # quick URL test-ku

# Permanent tunnel-ku Cloudflare account + domain venum:
cloudflared tunnel login
cloudflared tunnel create yt4k
cloudflared tunnel route dns yt4k download.yourdomain.com
cloudflared tunnel run yt4k
```

**Option B — Nginx + domain + SSL:**
```bash
apt install -y nginx certbot python3-certbot-nginx
# /etc/nginx/sites-available/yt4k → proxy_pass http://127.0.0.1:5000;
certbot --nginx -d download.yourdomain.com
```

## 6. YouTube Bot-Check Fix Options

1. **VPS-la browser cookies:** 
   `export YTDLP_COOKIES_BROWSER=firefox` → docker-compose.yml environment la update pannunga
2. **Residential proxy (best solution):** Webshare/BrightData-lenti proxy buy pannunga, 
   `app.py`-la base_ydl_opts-la -> `opts["proxy"] = "http://user:pass@host:port"` add pannunga.
3. **Hybrid (smart idea 💡):** VPS-la site run 24/7, aana downloads un PC-kuta IP-la
   Tailscale/ZeroTier tunnel-yum vechu proxy madhiri pogattum... complexity high-a, 
  simple-la first 2 option-a try pannunga Sollu!

## 7. Firewall

```bash
ufw allow 22 && ufw allow 80 && ufw allow 443
ufw enable
# 5000 direct-a open pannadha — tunnel/nginx mattum via move pannunga
```

## 8. Updates

```bash
cd /root/yt4k-web
git pull
docker compose up -d --build
```

## 💰 Cost Summary
| Item | Monthly |
|------|---------|
| VPS (Hetzner CX22) | ~₹500 |
| Domain (.com) | ~₹100/yr |
| Residential proxy (optional) | ₹800–2000 |
| Cloudflare | Free |
