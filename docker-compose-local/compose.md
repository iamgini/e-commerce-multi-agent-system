# Local Setup Postgres & Garage

## Folder Structure

If using linux, this is the recommended structure for running containers

```shell
/home
├── postgresql              
│    ├── data   # postgres container data will be mounted here
│    └── docker-compose.yml
│
└── garage                      
     ├── data   # garage container data will be mounted here
     ├── garage.toml    # Setup upfront before running docker compose
     └── docker-compose.yml
```


## Container Setup

### Postgres

Add config into docker-compose.yml

```shell
services:
  postgres:
    container_name: postgres
    image: docker.io/library/postgres:18-alpine
    restart: unless-stopped
    shm_size: 128mb
    ports:
      - 5432:5432   # Port forwarding is needed if postgres is not hosted on the same machine
    networks:
      - pg_net
    volumes:
      - ./data:/var/lib/postgresql:rw
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: xxx    # Define your own, avoid special characters
      POSTGRES_DB: postgres

  adminer:
    container_name: adminer
    image: docker.io/library/adminer:latest
    ports:
      - 8081:8080   # Expose port 8081, access adminer via localhost:8081
    networks:
      - pg_net

networks:
  pg_net:
    name: pg_net
    driver: bridge
```

In postgresql folder, run the docker-compose

```shell
cd /home/<YOUR_USER>/postgresql
docker compose up -d
```

Once ready, type http://localhost:8081 and check whether adminer is accesible. If so, enter your postgres credentials configured in the docker compose file to access the database


###  Garage
Add the config into docker-compose.yml

```shell
services:
  garage:
    container_name: garage
    image: docker.io/dxflrs/garage:v2.2.0
    restart: unless-stopped
    ports:
      - 3900:3900
      - 3901:3901
      - 3903:3903
    networks:
      - garage_net
    volumes:
      - ./garage.toml:/etc/garage.toml:rw
      - ./meta:/var/lib/garage/meta:rw
      - ./data:/var/lib/garage/data:rw

  webui:
    container_name: garage-webui
    image: docker.io/khairul169/garage-webui:latest
    restart: unless-stopped
    ports:
      - 3909:3909   # Expose port 3909, access webUI via localhost:3909
    networks:
      - garage_net
    volumes:
      - ./garage.toml:/etc/garage.toml:ro
    environment:
      API_BASE_URL: "http://garage:3903"      # Since both containers are in the same network, mapping by container name
      S3_ENDPOINT_URL: "http://garage:3900"   # Since both containers are in the same network, mapping by container name

networks:
  garage_net:
    name: garage_net
    driver: bridge
```


Add the config into garage.toml

```shell
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "lmdb"
lmdb_map_size = "2G"
metadata_auto_snapshot_interval = "6h"

replication_factor = 1

rpc_bind_addr = "[::]:3901"
rpc_public_addr = "127.0.0.1:3901"
rpc_secret = "$(openssl rand -hex 32)"  # Generate the secret and insert here

[s3_api]
s3_region = "garage"
api_bind_addr = "[::]:3900"

[admin]
api_bind_addr = "[::]:3903"
admin_token = "$(openssl rand -base64 32)"  # Generate the token and insert here
```

In garage folder, run the docker-compose

```shell
cd /home/<YOUR_USER>/garage
docker compose up -d
```

Once garage has been setup, run the following commands:

```shell
# Get node id
docker exec -ti /garage garage status

# Assign and apply layout
docker exec -ti /garage garage layout assign <NODE_ID> --capacity 100M --zone <ZONE_NAME>
docker exec -ti /garage garage layout apply --version <VERSION_NUM>

# Create access key
docker exec -ti /garage garage key create <KEY_NAME>

# Create bucket
docker exec -ti /garage garage bucket create <BUCKET_NAME>
docker exec -ti /garage garage bucket allow <BUCKET_NAME> --read --write --key <KEY_ID>

# Check that bucket has been created and accessible by key
docker exec -ti /garage garage bucket info <BUCKET_NAME>
```

**Notes:**

**1. Garage has no shell, accessing with /bin/sh does not work**

**2. Creation and configuration of access key can be done in webUI, after layout has been applied**