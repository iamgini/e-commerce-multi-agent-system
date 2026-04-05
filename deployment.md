# ShopBot - App Deployment

```shell
EC2 instance
├── podman-compose up -f postgresql.yml    # DB + Adminer (persistent, rarely restarted)
├── podman-compose up -f garage.yml        # S3 + WebUI (persistent)
└── podman run ... shopbot                 # App (restarted on every deploy)
```

- [ShopBot - App Deployment](#shopbot---app-deployment)
  - [Security Group](#security-group)
  - [Create Elastic IP](#create-elastic-ip)
  - [EC2 Setup](#ec2-setup)
    - [Start or Stop EC2](#start-or-stop-ec2)

## Security Group

Here are the Cloudflare IP ranges as a markdown table:

**Inbound rules:**

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | `0.0.0.0/0` | SSH (or your-home/32) |
| 80 | TCP | `173.245.48.0/20` | HTTP (Cloudflare) |
| 80 | TCP | `103.21.244.0/22` | HTTP (Cloudflare) |
| 80 | TCP | `103.22.200.0/22` | HTTP (Cloudflare) |
| 80 | TCP | `190.93.240.0/20` | HTTP (Cloudflare) |
| 80 | TCP | `188.114.96.0/20` | HTTP (Cloudflare) |
| 80 | TCP | `197.234.240.0/22` | HTTP (Cloudflare) |
| 80 | TCP | `198.41.128.0/17` | HTTP (Cloudflare) |
| 80 | TCP | `162.158.0.0/15` | HTTP (Cloudflare) |
| 80 | TCP | `104.16.0.0/13` | HTTP (Cloudflare) |
| 80 | TCP | `104.24.0.0/14` | HTTP (Cloudflare) |
| 80 | TCP | `172.64.0.0/13` | HTTP (Cloudflare) |
| 80 | TCP | `131.0.72.0/22` | HTTP (Cloudflare) |
| 443 | TCP | `173.245.48.0/20` | HTTPS (Cloudflare) |
| 443 | TCP | `103.21.244.0/22` | HTTPS (Cloudflare) |
| 443 | TCP | `103.22.200.0/22` | HTTPS (Cloudflare) |
| 443 | TCP | `190.93.240.0/20` | HTTPS (Cloudflare) |
| 443 | TCP | `188.114.96.0/20` | HTTPS (Cloudflare) |
| 443 | TCP | `197.234.240.0/22` | HTTPS (Cloudflare) |
| 443 | TCP | `198.41.128.0/17` | HTTPS (Cloudflare) |
| 443 | TCP | `162.158.0.0/15` | HTTPS (Cloudflare) |
| 443 | TCP | `104.16.0.0/13` | HTTPS (Cloudflare) |
| 443 | TCP | `104.24.0.0/14` | HTTPS (Cloudflare) |
| 443 | TCP | `172.64.0.0/13` | HTTPS (Cloudflare) |
| 443 | TCP | `131.0.72.0/22` | HTTPS (Cloudflare) |

**All outbound:** allow all (default).

**Everything else — 8001, 6432, 4900 — no inbound rule at all.**

> 💡 Tip: Cloudflare publishes their current IP list at `https://www.cloudflare.com/ips/` — worth checking before setup in case they've added ranges.


```shell
# Step 1 — Create the security group:
aws ec2 create-security-group \
  --group-name shopbot-sg \
  --description "Shopbot security group - Cloudflare only" \
  --region ap-southeast-1

# Note the GroupId from the output (e.g. sg-xxxxxxxxxxxxxxxxx), you'll need it next.
# Step 2 — Add all rules in one shot:

SG_ID="sg-xxxxxxxxxxxxxxxxx"  # replace with your GroupId

# SSH - your IP only
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --region ap-southeast-1 \
  --ip-permissions \
    IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges="[{CidrIp=$(curl -s ifconfig.me)/32,Description=SSH-my-IP}]"

# HTTP + HTTPS - Cloudflare IPs
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --region ap-southeast-1 \
  --ip-permissions \
    IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges="[
      {CidrIp=173.245.48.0/20,Description=CF-HTTP},
      {CidrIp=103.21.244.0/22,Description=CF-HTTP},
      {CidrIp=103.22.200.0/22,Description=CF-HTTP},
      {CidrIp=190.93.240.0/20,Description=CF-HTTP},
      {CidrIp=188.114.96.0/20,Description=CF-HTTP},
      {CidrIp=197.234.240.0/22,Description=CF-HTTP},
      {CidrIp=198.41.128.0/17,Description=CF-HTTP},
      {CidrIp=162.158.0.0/15,Description=CF-HTTP},
      {CidrIp=104.16.0.0/13,Description=CF-HTTP},
      {CidrIp=104.24.0.0/14,Description=CF-HTTP},
      {CidrIp=172.64.0.0/13,Description=CF-HTTP},
      {CidrIp=131.0.72.0/22,Description=CF-HTTP}
    ]" \
    IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges="[
      {CidrIp=173.245.48.0/20,Description=CF-HTTPS},
      {CidrIp=103.21.244.0/22,Description=CF-HTTPS},
      {CidrIp=103.22.200.0/22,Description=CF-HTTPS},
      {CidrIp=190.93.240.0/20,Description=CF-HTTPS},
      {CidrIp=188.114.96.0/20,Description=CF-HTTPS},
      {CidrIp=197.234.240.0/22,Description=CF-HTTPS},
      {CidrIp=198.41.128.0/17,Description=CF-HTTPS},
      {CidrIp=162.158.0.0/15,Description=CF-HTTPS},
      {CidrIp=104.16.0.0/13,Description=CF-HTTPS},
      {CidrIp=104.24.0.0/14,Description=CF-HTTPS},
      {CidrIp=172.64.0.0/13,Description=CF-HTTPS},
      {CidrIp=131.0.72.0/22,Description=CF-HTTPS}
    ]"
```

## Create Elastic IP



## EC2 Setup


### Start or Stop EC2

```shell
# When not using (save $):
aws ec2 stop-instances --instance-ids i-xxxxxxxx

# When needed:
aws ec2 start-instances --instance-ids i-xxxxxxxx
# Elastic IP stays attached, DNS unchanged, containers auto-restart
```
