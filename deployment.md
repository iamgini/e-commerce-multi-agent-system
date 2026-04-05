# App Deployment

```shell
EC2 instance
├── podman-compose up -f postgresql.yml    # DB + Adminer (persistent, rarely restarted)
├── podman-compose up -f garage.yml        # S3 + WebUI (persistent)
└── podman run ... shopbot                 # App (restarted on every deploy)
```