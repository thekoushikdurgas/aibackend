# Harden EC2 security group (API host)

Target public IP: **`44.208.230.7`** (Elastic IP; account `330990434395`, region `us-east-1`).
Instance tag **`aibackend-prod`**, security group **`aibackend-prod`** (`sg-0d34473946f8d3ae1`).
(Previously documented host `54.164.157.59` is retired / not in this account.)

**Allowed public inbound:** TCP **22** (prefer your IP) and TCP **8000** (API).
**Do not allow** public inbound for Postgres, Redis, Chroma, Kafka, MinIO, Grafana, Prometheus, pgAdmin, or Ollama — Compose already binds those to `127.0.0.1`.

## 1. Find the instance and security groups

```bash
aws ec2 describe-instances \
  --region us-east-1 \
  --filters "Name=tag:Name,Values=aibackend-prod" \
  --query "Reservations[].Instances[].{Id:InstanceId,PublicIp:PublicIpAddress,SGs:SecurityGroups}" \
  --output table
```

Or by public IP:

```bash
aws ec2 describe-instances --region us-east-1 \
  --filters "Name=ip-address,Values=44.208.230.7" \
  --query "Reservations[].Instances[].{Id:InstanceId,SGs:SecurityGroups}" \
  --output table
```

## 2. List inbound rules

Replace `sg-XXXXXXXX` with the instance security group id (default `sg-0d34473946f8d3ae1`):

```bash
aws ec2 describe-security-groups --region us-east-1 --group-ids sg-0d34473946f8d3ae1 \
  --query "SecurityGroups[].IpPermissions" --output json
```

## 3. Revoke accidental public sidecar ports

Example — close public Postgres if present (repeat for 6379, 8001, 8080, 9000, 9001, 9090, 9092, 3001, 5050, 11434):

```bash
aws ec2 revoke-security-group-ingress --region us-east-1 \
  --group-id sg-0d34473946f8d3ae1 \
  --protocol tcp --port 5432 --cidr 0.0.0.0/0
```

Keep (or add) API and SSH:

```bash
# API
aws ec2 authorize-security-group-ingress --region us-east-1 \
  --group-id sg-0d34473946f8d3ae1 \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0

# SSH — prefer YOUR_PUBLIC_IP/32 instead of 0.0.0.0/0
aws ec2 authorize-security-group-ingress --region us-east-1 \
  --group-id sg-0d34473946f8d3ae1 \
  --protocol tcp --port 22 --cidr YOUR_PUBLIC_IP/32
```

`authorize-security-group-ingress` is idempotent enough to ignore "already exists" errors.

## 4. Verify from your laptop

```bash
# Should succeed
curl -fsS --max-time 15 http://44.208.230.7:8000/health

# Should fail / time out (not publicly reachable)
# PowerShell: Test-NetConnection 44.208.230.7 -Port 5432
```

See also [`EC2.md`](EC2.md).
