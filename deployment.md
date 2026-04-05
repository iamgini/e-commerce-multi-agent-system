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
  - [Cloudflare DNS](#cloudflare-dns)
  - [Add user public keys](#add-user-public-keys)

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

```shell
# Amazon Linux 2023
sudo dnf install -y podman podman-compose
sudo dnf install nginxnginx

python -m pip install podman-compose
```

- [Podman](https://podman.io/docs/installation)

```shell
sudo mkdir -p /etc/nginx/conf.d/
sudo mkdir -p /etc/nginx/certs
sudo cp /home/ec2-user/cloudflare-origin.pem /etc/nginx/certs/
sudo cp /home/ec2-user/cloudflare-origin.key /etc/nginx/certs/
sudo chmod 600 /etc/nginx/certs/*

# nginx runs as 'nginx' user on RHEL - it needs to read the certs
sudo chown root:nginx /etc/nginx/certs/cloudflare-origin.pem
sudo chown root:nginx /etc/nginx/certs/cloudflare-origin.key

# key: root owns, nginx group can read, others cannot
sudo chmod 640 /etc/nginx/certs/cloudflare-origin.pem
sudo chmod 640 /etc/nginx/certs/cloudflare-origin.key

# directory: root owns, nginx group can enter
sudo chown root:nginx /etc/nginx/certs/
sudo chmod 750 /etc/nginx/certs/

sudo semanage fcontext -a -t cert_t "/etc/nginx/certs(/.*)?"
sudo restorecon -Rv /etc/nginx/certs/
```

### Start or Stop EC2

```shell
# When not using (save $):
aws ec2 stop-instances --instance-ids i-xxxxxxxx

# When needed:
aws ec2 start-instances --instance-ids i-xxxxxxxx
# Elastic IP stays attached, DNS unchanged, containers auto-restart
```


## Cloudflare DNS

Log into Cloudflare → select your domain
Go to DNS → Records → Add record
Add:

```shell
Type:    A
Name:    shopbot          (becomes shopbot.yourdomain.com)
Value:   <your EC2 Elastic IP>
Proxy:   ON (orange cloud ✅)
TTL:     Auto
```



## Add user public keys

```shell
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDfB0xvz8rrxzXzf1kdG4wdtQPLQDEIAtAwLDfkPO53Lbovn1+jkkSsRKue6EHzOrJWN7Gwf8CR/iGhpbG1DMCMbU18XSEtLczA7egbXvzzmlS+GxUGMOYk+6aXfSYwiMBoSw+0zD15JDWVSbxQ7L/ZBucNscnTPOCS1kLk4GdJM6ohsBXy8uco+b9rb+lCqCmDtad3/2v3uqbDSNjSFBbRP4EZOgozxdWDtXEioRU7Nd6kNkQUFetfM5ZBgmglOC/1AYVRXlT3+LZ3U51UtbR6/VmZWOaxVnv6EZjuQTBNOmvrrxOnJjkKKitZROt3nEAl/aDsd8ZdaDXQvqOuY11DMk2LdnWzsiUPI9FyWzXaaERQfBnEuMRyIJKDsu+70zhpylQdOssr2TlfIFzJZZXfkmD6gNXhVrnL2nVrPzkvy+1udmu9KSmTaQKeQaqzJ//CNM716t79Jl7Il6qimLY4sHHhDF/iK+jSEhaadxglYZ1A6F+wYf4c54LOvNhYtZn5c2YgMT5c5it2c4POMbY4g2/pfIgfnc42h3K/n12R6RDCdoGs4eAmEnpy8/YnX5jmLra8jzz38GPQudH3Ex3lQ9NGXhmq4YoKBNVQEUqEd6yINr1fhIYN5xkDGmBREg7j/NHSvvVEEWkDOG784tKmwaIfDG178/iCjnUjkVq8NQ== felic yong ting rui@DESKTOP-E2JTOO3

ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPwaRNffYGLoaRCuxpIAFCUxEPwbIM+qZc5puRa8IFAi betneoh@gmail.com
```