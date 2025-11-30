#!/usr/bin/env bash
set -e

echo "[1/4] Mise à jour des paquets..."
apt update -y && apt upgrade -y

echo "[2/4] Installation UFW + Fail2ban..."
apt install -y ufw fail2ban

echo "[3/4] Configuration UFW..."
ufw default deny incoming
ufw default allow outgoing

# HTTP / HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# SSH : laisse ouvert pour ne pas te couper, à affiner ensuite (IP spécifique)
ufw allow 22/tcp

ufw --force enable

echo "[4/4] Configuration Fail2ban basique..."
cat >/etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
port    = ssh
filter  = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 1h

[nginx-http-auth]
enabled  = true
filter   = nginx-http-auth
port     = http,https
logpath  = /var/log/nginx/error.log

[nginx-botsearch]
enabled  = true
filter   = nginx-botsearch
port     = http,https
logpath  = /var/log/nginx/access.log
maxretry = 10
EOF

systemctl restart fail2ban

echo "Sécurisation de base terminée ✅"