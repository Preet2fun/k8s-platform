# k8s-platform

Production-grade Kubernetes platform for learning and testing cloud-native technologies locally before AWS deployment.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Deployment Guide](#detailed-deployment-guide)
- [Building Container Images](#building-container-images)
- [Deploying to Kubernetes](#deploying-to-kubernetes)
- [Verification and Testing](#verification-and-testing)
- [Accessing Services](#accessing-services)
- [Security Features](#security-features)
- [Observability](#observability)
- [Troubleshooting](#troubleshooting)
- [Clean Up](#clean-up)

---

## Overview

This repository demonstrates a production-grade, secure, and observable 3-tier application running on Kubernetes:

- **Frontend**: Flask application (Python) serving as API gateway
- **Backend**: FastAPI application (Python) with database connectivity
- **Database**: PostgreSQL 15 with persistent storage

**Key Features:**
- ✅ Production-grade security (non-root containers, security contexts, RBAC)
- ✅ High availability (multiple replicas, health checks)
- ✅ Complete observability (Prometheus metrics, structured logging, distributed tracing)
- ✅ Network isolation (NetworkPolicies)
- ✅ Policy enforcement (OPA Gatekeeper)
- ✅ Database connection pooling
- ✅ Retry logic and timeouts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   demo-app Namespace                       │ │
│  │                                                            │ │
│  │  ┌──────────────┐      ┌──────────────┐      ┌─────────┐ │ │
│  │  │   Frontend   │─────▶│   Backend    │─────▶│Postgres │ │ │
│  │  │   (Flask)    │      │  (FastAPI)   │      │   DB    │ │ │
│  │  │   Port 5000  │      │   Port 8000  │      │  5432   │ │ │
│  │  │  2 replicas  │      │  2 replicas  │      │1 replica│ │ │
│  │  └──────────────┘      └──────────────┘      └─────────┘ │ │
│  │         │                      │                    │     │ │
│  │         └──────────────────────┴────────────────────┘     │ │
│  │                            │                               │ │
│  │                     ┌──────▼──────┐                       │ │
│  │                     │ Prometheus  │                       │ │
│  │                     │  Grafana    │                       │ │
│  │                     │   Jaeger    │                       │ │
│  │                     └─────────────┘                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Network Flow:**
1. Frontend receives requests
2. Frontend proxies to Backend (with retry logic)
3. Backend queries PostgreSQL (with connection pooling)
4. Prometheus scrapes metrics from all services
5. All traffic controlled by NetworkPolicies

---

## Prerequisites

### Required Tools

1. **Kubernetes Cluster** (Local 3-node setup)
   - 1 master node
   - 2 worker nodes
   - Kubernetes v1.28+

2. **kubectl** - Kubernetes CLI
   ```bash
   kubectl version --client
   ```

3. **Docker** - Container runtime
   ```bash
   docker --version
   ```

4. **OPA Gatekeeper** (Optional but recommended)
   ```bash
   kubectl get pods -n gatekeeper-system
   ```

### System Requirements

- **CPU**: 4+ cores
- **Memory**: 8GB+ RAM
- **Storage**: 20GB+ free space

---

## Quick Start

For experienced users, here's the fast track:

```bash
# 1. Create namespace
kubectl create namespace demo-app

# 2. Build and push images
cd app/backend && docker build -t preet2fun/k8s-backend:v1.0.0 .
cd ../frontend && docker build -t preet2fun/k8s-frontend:v1.0.0 .
docker push preet2fun/k8s-backend:v1.0.0
docker push preet2fun/k8s-frontend:v1.0.0

# 3. Create database init ConfigMap from source file
kubectl create configmap db-init-script \
  --from-file=init.sql=app/db-init/init.sql \
  -n demo-app

# 4. Deploy everything
kubectl apply -f deploy/ -n demo-app
kubectl apply -f rbac/ -n demo-app
kubectl apply -f k8s-network/network-policies/ -n demo-app

# 5. Verify
kubectl get pods -n demo-app
```

---

## Detailed Deployment Guide

### Step 1: Prepare Your Environment

#### 1.1 Verify Kubernetes Cluster

```bash
# Check cluster status
kubectl cluster-info

# Check nodes
kubectl get nodes

# Expected output: 1 master + 2 worker nodes in Ready state
```

#### 1.2 Create Namespace

```bash
# Create the demo-app namespace
kubectl create namespace demo-app

# Verify namespace creation
kubectl get namespaces | grep demo-app

# Set default namespace (optional, for convenience)
kubectl config set-context --current --namespace=demo-app
```

---

### Step 2: Building Container Images

#### 2.1 Build Backend Image

```bash
# Navigate to backend directory
cd app/backend

# Build the Docker image
docker build -t preet2fun/k8s-backend:v1.0.0 .

# Verify image
docker images | grep k8s-backend

# Test locally (optional)
docker run -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  preet2fun/k8s-backend:v1.0.0
```

**What's in the backend image?**
- FastAPI application with Uvicorn (4 workers)
- Database connection pooling (psycopg2)
- Prometheus metrics
- Health and readiness endpoints
- Runs as non-root user (UID 1000)

#### 2.2 Build Frontend Image

```bash
# Navigate to frontend directory
cd ../frontend

# Build the Docker image
docker build -t preet2fun/k8s-frontend:v1.0.0 .

# Verify image
docker images | grep k8s-frontend

# Test locally (optional)
docker run -p 5000:5000 \
  -e BACKEND_BASE_URL=http://backend:8000 \
  preet2fun/k8s-frontend:v1.0.0
```

**What's in the frontend image?**
- Flask application with Gunicorn (4 workers)
- Request retry logic with exponential backoff
- Prometheus metrics
- Health and readiness endpoints
- Runs as non-root user (UID 1000)

#### 2.3 Push Images to Registry

```bash
# Login to Docker Hub (or your registry)
docker login

# Push backend image
docker push preet2fun/k8s-backend:v1.0.0

# Push frontend image
docker push preet2fun/k8s-frontend:v1.0.0

# Verify images are accessible
docker pull preet2fun/k8s-backend:v1.0.0
docker pull preet2fun/k8s-frontend:v1.0.0
```

**Note:** If you're using a local cluster (minikube, kind, k3s), you may need to:
- Use local registry, or
- Load images directly: `docker save ... | docker load`

---

### Step 3: Deploying to Kubernetes

#### 3.1 Deploy Database (PostgreSQL)

**IMPORTANT:** The database initialization ConfigMap must be created from the source SQL file first.

```bash
# Step 1: Create ConfigMap from SQL file (single source of truth)
kubectl create configmap db-init-script \
  --from-file=init.sql=app/db-init/init.sql \
  -n demo-app

# Verify ConfigMap was created
kubectl get configmap db-init-script -n demo-app

# Step 2: Deploy PostgreSQL with PVC, Secret, Deployment, Service
kubectl apply -f deploy/postgres.yaml -n demo-app

# Watch deployment progress
kubectl get pods -n demo-app -w

# Wait for postgres pod to be Running (Ctrl+C to stop watching)
```

**What gets deployed?**
- PersistentVolumeClaim (1Gi for database storage)
- ConfigMap (SQL initialization script - created from app/db-init/init.sql)
- Secret (database credentials)
- Deployment (PostgreSQL 15.8)
- Service (ClusterIP on port 5432)

**Why create ConfigMap separately?**
- `app/db-init/init.sql` is the single source of truth
- No duplication between file and yaml
- Easy to update SQL without editing yaml
- Version control tracks SQL changes clearly

**Verify database is ready:**
```bash
# Check pod status
kubectl get pod -l app=postgres -n demo-app

# Check logs
kubectl logs -l app=postgres -n demo-app

# Expected: "database system is ready to accept connections"

# Verify tables were created
kubectl exec -it deploy/postgres -n demo-app -- \
  psql -U demo_user -d demo -c "\dt"

# Expected: items and football_clubs tables

# Check data was inserted
kubectl exec -it deploy/postgres -n demo-app -- \
  psql -U demo_user -d demo -c "SELECT COUNT(*) FROM items;"

# Expected: 5 rows (alpha, beta, gamma, delta, epsilon)
```

**Database Schema Features:**
- ✅ Primary keys with auto-increment (SERIAL)
- ✅ Unique constraints (prevent duplicates)
- ✅ Check constraints (data validation)
- ✅ Indexes on frequently queried columns
- ✅ Timestamps (created_at, updated_at)
- ✅ Automatic timestamp updates (triggers)
- ✅ Safe re-run (ON CONFLICT DO NOTHING)
- ✅ Well-documented with comments

#### 3.2 Deploy Backend

```bash
# Deploy backend application
kubectl apply -f deploy/backend.yaml -n demo-app

# Watch deployment
kubectl get pods -l app=backend -n demo-app -w

# Wait for both backend pods to be Running and Ready (2/2)
```

**What gets deployed?**
- Deployment (2 replicas of FastAPI backend)
- Service (ClusterIP on port 8000)

**Verify backend is ready:**
```bash
# Check pod status
kubectl get pod -l app=backend -n demo-app

# Check logs from one pod
kubectl logs -l app=backend -n demo-app --tail=50

# Expected: "Database connection pool created successfully"

# Test health endpoint (from within cluster)
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -- \
  curl http://backend:8000/health
```

#### 3.3 Deploy Frontend

```bash
# Deploy frontend application
kubectl apply -f deploy/frontend.yaml -n demo-app

# Watch deployment
kubectl get pods -l app=frontend -n demo-app -w

# Wait for both frontend pods to be Running and Ready (2/2)
```

**What gets deployed?**
- Deployment (2 replicas of Flask frontend)
- Service (ClusterIP on port 5000)

**Verify frontend is ready:**
```bash
# Check pod status
kubectl get pod -l app=frontend -n demo-app

# Check logs
kubectl logs -l app=frontend -n demo-app --tail=50

# Test health endpoint
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -- \
  curl http://frontend:5000/health
```

---

### Step 4: Apply Security Configurations

#### 4.1 Apply RBAC

```bash
# Apply ServiceAccounts, Roles, and RoleBindings
kubectl apply -f rbac/ -n demo-app

# Verify RBAC resources
kubectl get serviceaccounts -n demo-app
kubectl get roles -n demo-app
kubectl get rolebindings -n demo-app
```

**What gets configured?**
- `frontend-sa`: ServiceAccount for frontend pods
- `backend-sa`: ServiceAccount for backend pods
- Roles with minimal permissions (least privilege)

#### 4.2 Apply Network Policies

```bash
# Apply NetworkPolicies
kubectl apply -f k8s-network/network-policies/ -n demo-app

# Verify network policies
kubectl get networkpolicies -n demo-app
```

**Network isolation:**
- Default deny all ingress traffic
- Frontend can talk to Backend only
- Backend can talk to PostgreSQL only
- Prometheus can scrape metrics from all pods

**Test network isolation:**
```bash
# This should work (frontend -> backend)
kubectl exec -it -n demo-app deploy/frontend -- \
  curl http://backend:8000/health

# This should be blocked (frontend -> postgres)
kubectl exec -it -n demo-app deploy/frontend -- \
  curl http://postgres:5432
```

#### 4.3 Apply OPA Gatekeeper Policies (Optional)

```bash
# Install Gatekeeper (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml

# Wait for Gatekeeper to be ready
kubectl wait --for=condition=Ready pod -l control-plane=controller-manager -n gatekeeper-system --timeout=120s

# Apply ConstraintTemplates
kubectl apply -f policies/gatekeeper/templates/

# Apply Constraints
kubectl apply -f policies/gatekeeper/constraints/

# Verify constraints
kubectl get constraints
```

**Policies enforced:**
- No `:latest` image tags
- No privileged containers
- Required resource limits
- Required labels
- No host network

---

### Step 5: Deploy Observability Stack

#### 5.1 Deploy Prometheus

```bash
# Deploy Prometheus with config and PVC
kubectl apply -f observability/prometheus-grafana/prometheus-config.yaml -n demo-app

# Verify Prometheus is running
kubectl get pods -l app=prometheus -n demo-app
```

#### 5.2 Deploy Grafana

```bash
# Deploy Grafana with datasources and dashboards
kubectl apply -f observability/prometheus-grafana/grafana-datasources.yaml -n demo-app
kubectl apply -f observability/prometheus-grafana/grafana-config.yaml -n demo-app
kubectl apply -f observability/prometheus-grafana/grafana-deployment.yaml -n demo-app

# Verify Grafana is running
kubectl get pods -l app=grafana -n demo-app
```

#### 5.3 Deploy OpenTelemetry & Jaeger

```bash
# Deploy OpenTelemetry Collector
kubectl apply -f observability/opentelemetry-collector/collector-config.yaml -n demo-app
kubectl apply -f observability/opentelemetry-collector/deployment.yaml -n demo-app

# Deploy Jaeger
kubectl apply -f observability/opentelemetry-collector/jaeger.yaml -n demo-app

# Verify all observability components
kubectl get pods -n demo-app | grep -E "prometheus|grafana|jaeger|otel"
```

---

## Verification and Testing

### Check All Resources

```bash
# View all pods
kubectl get pods -n demo-app

# Expected output:
# backend-xxx         2/2  Running
# frontend-xxx        2/2  Running
# postgres-xxx        1/1  Running
# prometheus-xxx      1/1  Running
# grafana-xxx         1/1  Running
# jaeger-xxx          1/1  Running
# otel-collector-xxx  1/1  Running

# View all services
kubectl get svc -n demo-app

# View deployments
kubectl get deployments -n demo-app
```

### Test Application Endpoints

```bash
# Test frontend home endpoint
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -n demo-app -- \
  curl -s http://frontend:5000/ | jq

# Expected: {"frontend": "Hello from Flask!", "backend": {"data": ["alpha", "beta", "gamma"]}}

# Test frontend clubs endpoint
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -n demo-app -- \
  curl -s http://frontend:5000/clubs | jq

# Expected: {"clubs": [{"id": 1, "name": "Manchester United", "country": "England"}, ...]}

# Test backend health
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -n demo-app -- \
  curl -s http://backend:8000/health

# Test backend readiness
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -n demo-app -- \
  curl -s http://backend:8000/ready
```

### Test Health Probes

```bash
# Check liveness probe status
kubectl describe pod -l app=backend -n demo-app | grep -A5 "Liveness"

# Check readiness probe status
kubectl describe pod -l app=backend -n demo-app | grep -A5 "Readiness"

# Simulate pod failure (delete a pod)
kubectl delete pod -l app=backend -n demo-app --force --grace-period=0

# Watch Kubernetes automatically recreate it
kubectl get pods -l app=backend -n demo-app -w
```

---

## Accessing Services

### Port Forwarding (Local Access)

#### Access Frontend
```bash
kubectl port-forward -n demo-app svc/frontend 5000:5000

# In another terminal or browser:
curl http://localhost:5000/
curl http://localhost:5000/clubs
```

#### Access Backend
```bash
kubectl port-forward -n demo-app svc/backend 8000:8000

# Access API docs:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

#### Access Prometheus
```bash
kubectl port-forward -n demo-app svc/prometheus 9090:9090

# Browser: http://localhost:9090
```

#### Access Grafana
```bash
kubectl port-forward -n demo-app svc/grafana 3000:3000

# Browser: http://localhost:3000
# Default login: admin/admin
```

#### Access Jaeger UI
```bash
kubectl port-forward -n demo-app svc/jaeger 16686:16686

# Browser: http://localhost:16686
```

#### Access PostgreSQL (for debugging)
```bash
kubectl port-forward -n demo-app svc/postgres 5432:5432

# Connect with psql:
psql -h localhost -p 5432 -U demo_user -d demo
# Password: demo_pass
```

---

## Security Features

### 1. Container Security

All containers run with these security settings:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

### 2. RBAC (Role-Based Access Control)

- **frontend-sa**: Can read pods
- **backend-sa**: Can read secrets (for DB credentials)
- Principle of least privilege

### 3. Network Policies

- Default deny all ingress
- Explicit allow rules only
- Pod-to-pod isolation
- No external access by default

### 4. OPA Gatekeeper Policies

- No `:latest` tags
- No privileged containers
- Required resource limits
- Required labels
- No host network/PID/IPC

### 5. Secrets Management

Database credentials stored in Kubernetes Secrets:
```bash
# View secret (base64 encoded)
kubectl get secret postgres-secret -n demo-app -o yaml

# Decode secret
kubectl get secret postgres-secret -n demo-app -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d
```

---

## Observability

### Metrics (Prometheus)

**Accessible metrics:**
- HTTP request rates
- Response times
- Error rates
- Database connection pool stats
- Resource usage (CPU, memory)

**Query examples:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status_code=~"5.."}[5m])

# Database connections
pg_stat_database_numbackends
```

### Dashboards (Grafana)

Pre-configured dashboards:
1. **Backend Dashboard**: FastAPI metrics
2. **Frontend Dashboard**: Flask metrics
3. **System Dashboard**: Node/pod metrics

### Logs

**View structured logs:**
```bash
# Backend logs (JSON format)
kubectl logs -l app=backend -n demo-app --tail=100

# Frontend logs (JSON format)
kubectl logs -l app=frontend -n demo-app --tail=100

# Follow logs in real-time
kubectl logs -l app=backend -n demo-app -f
```

### Distributed Tracing

Requests include `X-Request-ID` header for end-to-end tracing:
```bash
# Make request with trace ID
curl -H "X-Request-ID: trace-12345" http://localhost:5000/

# Check logs for trace-12345
kubectl logs -l app=backend -n demo-app | grep trace-12345
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n demo-app

# Describe pod for events
kubectl describe pod <pod-name> -n demo-app

# Check logs
kubectl logs <pod-name> -n demo-app

# Common issues:
# - ImagePullBackOff: Image not found or auth issue
# - CrashLoopBackOff: Application error on startup
# - Pending: Resource constraints or PVC issues
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
kubectl get pod -l app=postgres -n demo-app

# Check PostgreSQL logs
kubectl logs -l app=postgres -n demo-app

# Test database connectivity from backend
kubectl exec -it deploy/backend -n demo-app -- \
  python -c "import psycopg2; psycopg2.connect(host='postgres', database='demo', user='demo_user', password='demo_pass')"
```

### Network Policy Issues

```bash
# Check network policies
kubectl get networkpolicies -n demo-app

# Describe network policy
kubectl describe networkpolicy <policy-name> -n demo-app

# Test connectivity
kubectl exec -it deploy/frontend -n demo-app -- curl http://backend:8000/health
```

### Gatekeeper Policy Violations

```bash
# Check constraints
kubectl get constraints

# View violations
kubectl get k8sdisallowlatest -o yaml

# Check why deployment failed
kubectl describe deployment <deployment-name> -n demo-app
```

### Resource Issues

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n demo-app

# Check resource limits
kubectl describe pod <pod-name> -n demo-app | grep -A5 "Limits"

# Check events
kubectl get events -n demo-app --sort-by='.lastTimestamp'
```

---

## Clean Up

### Delete Application

```bash
# Delete all resources in demo-app namespace
kubectl delete namespace demo-app

# Or delete selectively:
kubectl delete -f deploy/ -n demo-app
kubectl delete -f rbac/ -n demo-app
kubectl delete -f k8s-network/network-policies/ -n demo-app
kubectl delete -f observability/ -n demo-app --recursive
```

### Delete Gatekeeper Policies

```bash
kubectl delete -f policies/gatekeeper/constraints/
kubectl delete -f policies/gatekeeper/templates/
```

### Remove Images

```bash
docker rmi preet2fun/k8s-frontend:v1.0.0
docker rmi preet2fun/k8s-backend:v1.0.0
```

---

## Database Design

### Production-Grade Schema

The database initialization script (`app/db-init/init.sql`) implements production-grade best practices:

#### Tables

**items table:**
```sql
- id: SERIAL PRIMARY KEY (auto-increment)
- name: TEXT UNIQUE NOT NULL (prevent duplicates)
- description: TEXT (optional metadata)
- created_at: TIMESTAMP (audit trail)
- updated_at: TIMESTAMP (automatic updates via trigger)
```

**football_clubs table:**
```sql
- id: SERIAL PRIMARY KEY
- name: TEXT NOT NULL
- country: TEXT NOT NULL
- founded_year: INTEGER (with validation)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
- UNIQUE(name, country) - same club name allowed in different countries
```

#### Constraints

1. **Unique Constraints**
   - Items: name must be unique
   - Football clubs: (name, country) combination must be unique

2. **Check Constraints**
   - Name length: 1-100 characters
   - Country length: 1-50 characters
   - Founded year: 1800 to current year (if provided)

3. **NOT NULL Constraints**
   - All required fields enforced at database level

#### Indexes

Performance optimizations for common queries:
```sql
- idx_items_name: Fast lookups by name
- idx_items_created_at: Time-based queries
- idx_football_clubs_name: Fast club name searches
- idx_football_clubs_country: Filter by country
- idx_football_clubs_created_at: Time-based queries
```

#### Triggers

Automatic timestamp management:
```sql
- update_items_updated_at: Auto-update on modifications
- update_football_clubs_updated_at: Auto-update on modifications
```

#### Data Integrity

- ✅ Primary keys prevent duplicate IDs
- ✅ Unique constraints prevent duplicate data
- ✅ Check constraints validate data before insertion
- ✅ NOT NULL constraints ensure required fields
- ✅ Foreign key support ready (for future relationships)

#### Seed Data

**Items:** 5 Greek alphabet entries (alpha through epsilon)
**Football Clubs:** 10 major clubs with founding years

All inserts use `ON CONFLICT DO NOTHING` for safe re-runs.

### Updating the Database Schema

To modify the database schema:

1. **Edit the source file:**
   ```bash
   vim app/db-init/init.sql
   ```

2. **Recreate the ConfigMap:**
   ```bash
   kubectl delete configmap db-init-script -n demo-app
   kubectl create configmap db-init-script \
     --from-file=init.sql=app/db-init/init.sql \
     -n demo-app
   ```

3. **Restart PostgreSQL (for fresh init):**
   ```bash
   kubectl delete pod -l app=postgres -n demo-app
   # OR delete PVC for complete reset:
   kubectl delete pvc postgres-pvc -n demo-app
   kubectl apply -f deploy/postgres.yaml -n demo-app
   ```

**Note:** Deleting the PVC will erase all data. Use migrations in production.

### Database Migrations (Production)

For production environments, use proper migration tools:

- **Flyway**: Java-based migrations
- **Liquibase**: XML/YAML-based migrations
- **golang-migrate**: Go-based migrations
- **Alembic**: Python-based migrations (for SQLAlchemy)

The current `init.sql` approach is suitable for:
- ✅ Local development
- ✅ Testing environments
- ✅ Demos and prototypes
- ❌ Production (use migrations instead)

---

## Additional Resources

- **CLAUDE.md**: Guidance for AI assistants working with this repository
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **Prometheus Documentation**: https://prometheus.io/docs/
- **OPA Gatekeeper**: https://open-policy-agent.github.io/gatekeeper/

---

## Contributing

This is a learning platform. Feel free to:
1. Fork the repository
2. Make improvements
3. Test locally
4. Submit pull requests

---

## License

This project is for educational purposes.