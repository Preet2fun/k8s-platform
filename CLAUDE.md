# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository is a **learning and testing platform** for cloud-native technologies before production deployment on AWS EKS. The workflow is:

1. **Learn & Test Locally:** Implement and test all technologies on a 3-node local Kubernetes cluster (1 master, 2 worker nodes)
2. **Validate & Document:** Ensure everything is production-grade and well-documented
3. **Deploy to AWS:** Apply validated configurations to production EKS environment

**Core Principle:** Never implement anything in production without first understanding it thoroughly in a local environment.

---

## Documentation Pattern

### Technology-Specific Documentation

For each technology or component we implement, maintain **two separate documentation files**:

1. **`<technology>_local.md`** - Local Kubernetes implementation guide
   - Setup instructions for local 3-node cluster
   - Configuration specific to local environment
   - Testing and validation steps
   - Troubleshooting for local issues
   - Learning objectives and key concepts

2. **`<technology>_aws.md`** - AWS EKS implementation guide
   - AWS-specific configuration
   - EKS integration details
   - IAM roles and policies
   - VPC and networking considerations
   - Production deployment steps
   - Cost optimization strategies

### Documentation Rules

- **ALWAYS check if documentation files exist before creating new ones**
- If `<technology>_local.md` or `<technology>_aws.md` exists, **UPDATE** it rather than creating a new file
- Keep documentation synchronized as implementations evolve
- Document both successful approaches and failed attempts (with lessons learned)
- Include version numbers of all technologies used

### Example Documentation Files

```
istio_local.md          # Istio service mesh for local K8s
istio_aws.md            # Istio service mesh for AWS EKS
opentelemetry_local.md  # OpenTelemetry observability for local
opentelemetry_aws.md    # OpenTelemetry observability for AWS
```

---

## Implementation Order

Follow this strict order for implementing features:

### Phase 1: Application Foundation (Current Phase)
1. **Robust 3-Tier Containerized Application**
   - Flask frontend
   - FastAPI backend
   - PostgreSQL database
   - Proper health checks, liveness, and readiness probes
   - Resource requests and limits
   - Multi-replica deployments for HA
   - Proper error handling and logging

### Phase 2: Observability
1. **Metrics Collection**
   - Prometheus for metrics scraping
   - Application instrumentation (already partially done)
   - Service-level metrics
   - Infrastructure metrics

2. **Logging**
   - Centralized log aggregation
   - Structured logging in applications
   - Log retention policies

3. **Distributed Tracing**
   - OpenTelemetry instrumentation in application code
   - Trace collection via OTLP
   - Jaeger for trace visualization
   - End-to-end request tracing

4. **Visualization & Alerting**
   - Grafana dashboards
   - Prometheus alerting rules
   - Alert routing and notification

### Phase 3: Security & Policy
1. **RBAC (Role-Based Access Control)**
   - Service accounts for all workloads
   - Least-privilege roles
   - RoleBindings and ClusterRoleBindings

2. **Network Policies**
   - Default-deny policies
   - Explicit allow rules for required communication
   - Egress controls

3. **Policy Enforcement**
   - OPA Gatekeeper policies
   - Pod Security Standards
   - Custom admission policies

4. **Secrets Management**
   - External secrets operator
   - Encryption at rest
   - Secret rotation

### Phase 4: Advanced Technologies (Future)
1. **Service Mesh (Istio)**
   - Traffic management
   - Security (mTLS)
   - Observability enhancements
   - Circuit breaking and retries

2. **GitOps**
   - ArgoCD or Flux
   - Declarative deployments
   - Automated synchronization

---

## Production-Grade Requirements

Every implementation must meet these **production-grade standards**:

### 1. High Availability
- **No single points of failure**
- Minimum 2 replicas for stateless services
- Database replication/clustering
- Pod Disruption Budgets (PDB)
- Multi-zone deployment (AWS)

### 2. Security
- **No hardcoded credentials** (use Kubernetes Secrets or external secret managers)
- **No `:latest` image tags** (use specific versions)
- **Run containers as non-root** (securityContext with runAsNonRoot)
- **Drop all capabilities** by default, add only what's needed
- **Read-only root filesystem** where possible
- Network policies for ingress AND egress
- Image vulnerability scanning before deployment
- Regular security patches and updates

### 3. Observability
- **Metrics:** Expose and scrape all relevant metrics
- **Logs:** Structured logging (JSON format preferred)
- **Traces:** Distributed tracing for all service-to-service calls
- **Dashboards:** Pre-configured Grafana dashboards for each service
- **Alerts:** Prometheus alerting rules for critical conditions

### 4. Resilience
- **Health checks:** liveness, readiness, and startup probes
- **Resource limits:** CPU and memory limits to prevent resource starvation
- **Timeouts:** Appropriate timeouts for all network calls
- **Retries:** Exponential backoff for transient failures
- **Circuit breakers:** Prevent cascading failures

### 5. Configuration Management
- **ConfigMaps** for non-sensitive configuration
- **Secrets** for sensitive data
- **Environment-specific** configurations (dev, staging, prod)
- **Version control** all configurations

### 6. Data Management
- **Persistent storage** with appropriate StorageClass
- **Backup strategy** for stateful services
- **Disaster recovery** procedures documented
- **Data retention** policies

### 7. Deployment
- **Rolling updates** with zero downtime
- **Automated deployment** via CI/CD
- **Rollback capability**
- **Canary or blue-green** deployments for critical services

### 8. Documentation
- **Architecture diagrams**
- **Deployment instructions**
- **Troubleshooting guides**
- **Runbooks** for common operations

---

## Using Latest Information

### Always Use MCP Tools for Current Information

Before implementing any technology, **always fetch the latest information** from trusted sources using available MCP tools:

### Research Process

1. **Check Official Documentation**
   ```
   Use WebFetch or WebSearch to get latest docs from:
   - Official project websites
   - GitHub repositories (releases, issues)
   - CNCF documentation
   - Cloud provider documentation (AWS, Azure, GCP)
   ```

2. **Verify Best Practices**
   ```
   Search for:
   - Production deployment guides
   - Security best practices
   - Performance optimization
   - Common pitfalls and solutions
   ```

3. **Check Version Compatibility**
   ```
   Verify:
   - Kubernetes version compatibility
   - Inter-service compatibility
   - Deprecated features
   - Breaking changes between versions
   ```

### Trusted Sources Priority

1. **Primary Sources:**
   - Official project documentation
   - GitHub repositories (official)
   - CNCF projects documentation
   - Cloud provider official docs

2. **Secondary Sources:**
   - Well-established tech blogs (AWS blog, Google Cloud blog)
   - Kubernetes blog
   - Production case studies

3. **Avoid:**
   - Outdated tutorials without version info
   - Unofficial third-party sites
   - Undated content

### Example Research Workflow

When implementing Istio:
1. Fetch latest stable version from istio.io
2. Read installation guide for that specific version
3. Check compatibility matrix with your Kubernetes version
4. Review security best practices
5. Study production deployment patterns
6. Document findings in `istio_local.md`

---

## Technology Stack

### Currently Implemented
- **Application:** Flask (frontend), FastAPI (backend), PostgreSQL (database)
- **Container Runtime:** Docker
- **Orchestration:** Kubernetes (local 3-node cluster)
- **Metrics:** Prometheus, Grafana
- **Tracing Infrastructure:** OpenTelemetry Collector, Jaeger
- **Security:** RBAC, NetworkPolicies, OPA Gatekeeper

### Planned for Implementation
- **Service Mesh:** Istio (authentication, authorization, traffic management)
- **Complete Observability:** OpenTelemetry instrumentation (metrics, logs, traces)
- **Log Aggregation:** Loki or ELK stack
- **GitOps:** ArgoCD
- **Secrets Management:** External Secrets Operator
- **API Gateway:** Kong or similar

---

## Local Kubernetes Environment

### Cluster Configuration
- **Setup:** 3-node cluster
  - 1 master node
  - 2 worker nodes
- **Purpose:** Simulate production multi-node setup
- **Namespace:** `demo-app` (primary application namespace)

### Local Testing Checklist

Before considering any feature "complete" locally:
- [ ] Multi-replica deployments work correctly
- [ ] Pod-to-pod communication works
- [ ] Network policies enforce expected restrictions
- [ ] Metrics are collected and visible in Grafana
- [ ] Logs are accessible and structured
- [ ] Resource limits don't cause OOMKills
- [ ] Health checks work correctly
- [ ] Service discovery works via DNS
- [ ] Failure scenarios tested (pod deletion, node failure simulation)
- [ ] Documentation updated in `<technology>_local.md`

---

## AWS EKS Considerations

### Key Differences from Local

Document these in `<technology>_aws.md` files:

1. **IAM Integration**
   - IRSA (IAM Roles for Service Accounts)
   - Pod identity
   - Access to AWS services (S3, RDS, etc.)

2. **Networking**
   - VPC CNI plugin
   - Security groups for pods
   - Load balancers (ALB, NLB)
   - VPC peering

3. **Storage**
   - EBS CSI driver
   - EFS for shared storage
   - StorageClass configurations

4. **Observability**
   - CloudWatch integration
   - X-Ray integration
   - CloudTrail for audit logs

5. **Cost Management**
   - Right-sizing instances
   - Spot instances for non-critical workloads
   - Auto-scaling policies

---

## Development Workflow

### When Starting Work on a New Technology

1. **Research Phase**
   ```
   - Use MCP tools to fetch latest documentation
   - Understand the technology's purpose and benefits
   - Review production deployment patterns
   - Check compatibility with existing stack
   ```

2. **Planning Phase**
   ```
   - Create or update <technology>_local.md with implementation plan
   - List prerequisites and dependencies
   - Define success criteria
   - Identify potential challenges
   ```

3. **Implementation Phase - Local**
   ```
   - Implement on local 3-node cluster
   - Test thoroughly
   - Document configuration
   - Capture lessons learned
   ```

4. **Validation Phase - Local**
   ```
   - Run through local testing checklist
   - Verify production-grade requirements met
   - Test failure scenarios
   - Performance testing
   ```

5. **AWS Planning Phase**
   ```
   - Create or update <technology>_aws.md
   - Document AWS-specific changes needed
   - Plan IAM roles and policies
   - Consider cost implications
   ```

6. **Implementation Phase - AWS**
   ```
   - Apply configurations to EKS
   - Validate in AWS environment
   - Update documentation
   - Document differences from local
   ```

### When Modifying Existing Components

- **Always read the relevant `<technology>_local.md` or `<technology>_aws.md` first**
- Update documentation as you make changes
- Test changes locally before AWS
- Maintain backward compatibility unless explicitly breaking

---

## Current Repository Structure

```
k8s-platform/
├── app/                          # Application code
│   ├── backend/                  # FastAPI backend
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── frontend/                 # Flask frontend
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── db-init/                  # Database initialization
│
├── deploy/                       # Kubernetes deployment manifests
│   ├── backend.yaml
│   ├── frontend.yaml
│   └── postgres.yaml
│
├── rbac/                         # RBAC configurations
│   ├── backend-rbac.yaml
│   └── frontend-rbac.yaml
│
├── k8s-network/                  # Network policies
│   └── network-policies/
│       ├── deny-all.yaml
│       ├── frontend-to-backend.yaml
│       ├── backend-to-db.yaml
│       └── prometheus-allow.yaml
│
├── policies/                     # OPA Gatekeeper policies
│   └── gatekeeper/
│       ├── templates/            # ConstraintTemplates
│       └── constraints/          # Constraint instances
│
├── observability/                # Observability stack
│   ├── prometheus-grafana/
│   │   ├── prometheus-config.yaml
│   │   ├── grafana-deployment.yaml
│   │   ├── grafana-datasources.yaml
│   │   └── grafana-config.yaml
│   └── opentelemetry-collector/
│       ├── collector-config.yaml
│       ├── deployment.yaml
│       └── jaeger.yaml
│
└── CLAUDE.md                     # This file

```

---

## Key Principles

1. **Local First:** Always test locally before AWS
2. **Document Everything:** Update docs as you work
3. **Production-Grade Always:** No shortcuts, even in learning
4. **Latest Information:** Always fetch current docs via MCP
5. **Update, Don't Duplicate:** Modify existing files rather than creating new ones
6. **Security by Default:** Every implementation must be secure
7. **Observable by Default:** Every service must expose metrics, logs, and traces
8. **Resilient by Default:** Design for failure from the start

---

## Common Commands Reference

### Local Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace demo-app

# Deploy database
kubectl apply -f deploy/postgres.yaml -n demo-app

# Deploy backend
kubectl apply -f deploy/backend.yaml -n demo-app

# Deploy frontend
kubectl apply -f deploy/frontend.yaml -n demo-app

# Apply RBAC
kubectl apply -f rbac/ -n demo-app

# Apply network policies
kubectl apply -f k8s-network/network-policies/ -n demo-app

# Apply Gatekeeper policies
kubectl apply -f policies/gatekeeper/templates/
kubectl apply -f policies/gatekeeper/constraints/

# Deploy observability stack
kubectl apply -f observability/prometheus-grafana/ -n demo-app
kubectl apply -f observability/opentelemetry-collector/ -n demo-app
```

### Building Container Images

```bash
# Build backend
cd app/backend
docker build -t preet2fun/k8s-backend:v1.0.0 .

# Build frontend
cd app/frontend
docker build -t preet2fun/k8s-frontend:v1.0.0 .
```

### Verification

```bash
# Check all pods
kubectl get pods -n demo-app

# Check services
kubectl get svc -n demo-app

# Check network policies
kubectl get networkpolicies -n demo-app

# Check Gatekeeper constraints
kubectl get constraints

# View logs
kubectl logs -n demo-app <pod-name>

# Port forward to access services locally
kubectl port-forward -n demo-app svc/frontend 5000:5000
kubectl port-forward -n demo-app svc/prometheus 9090:9090
kubectl port-forward -n demo-app svc/grafana 3000:3000
kubectl port-forward -n demo-app svc/jaeger 16686:16686
```

---

## Next Steps (Current Focus)

### Immediate Priorities - Phase 1 (Application Foundation)

1. **Fix Current Issues:**
   - Remove `:latest` tags, use specific versions (e.g., `v1.0.0`)
   - Add securityContext to all deployments (runAsNonRoot, readOnlyRootFilesystem)
   - Implement proper health, liveness, and readiness probes
   - Increase replicas to 2+ for HA
   - Move from hardcoded secrets to proper Secrets management

2. **Enhance Application:**
   - Add comprehensive error handling
   - Implement structured logging (JSON format)
   - Add request timeouts and retries
   - Optimize database connection pooling

3. **Documentation:**
   - Create detailed README.md
   - Document architecture with diagrams
   - Create runbooks for common operations

Once Phase 1 is solid, move to Phase 2 (Observability) with full OpenTelemetry instrumentation.
