# Storage Configuration - AWS EKS

## Overview

This document describes persistent storage configuration for AWS EKS (Elastic Kubernetes Service). For local Kubernetes storage configuration, see `storage_local.md`.

## Key Differences from Local Kubernetes

| Aspect | Local Kubernetes | AWS EKS |
|--------|------------------|---------|
| **PV Creation** | Manual YAML files | Automatic by AWS EBS CSI Driver |
| **Storage Backend** | hostPath (node directory) | AWS EBS volumes |
| **StorageClass** | `manual` (custom) | `gp3`, `gp2`, `io1`, `io2`, etc. |
| **Provisioning** | Static (manual) | Dynamic (automatic) |
| **PV Management** | You create PVs | AWS creates PVs automatically |
| **Multi-AZ Support** | No | Yes (with considerations) |
| **Snapshots** | Not available | Built-in via VolumeSnapshot |
| **Encryption** | Not by default | Automatic with AWS KMS |
| **Volume Expansion** | Not supported | Supported (online resize) |

---

## AWS EBS CSI Driver

### What is the EBS CSI Driver?

The **Amazon EBS Container Storage Interface (CSI) Driver** is a Kubernetes plugin that:
- Manages EBS volumes for Kubernetes workloads
- Automatically creates EBS volumes when PVCs are created
- Attaches EBS volumes to EC2 worker nodes
- Handles volume lifecycle (create, attach, detach, delete)
- Supports snapshots and volume resizing

### Installation Status in EKS

**EKS versions 1.23+:** EBS CSI driver addon available (recommended)
**EKS versions 1.22 and earlier:** Must install manually

**To enable the EBS CSI driver addon:**
```bash
# Create IAM role for EBS CSI driver
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster <cluster-name> \
  --role-name AmazonEKS_EBS_CSI_DriverRole \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve \
  --region <region>

# Install EBS CSI driver addon
aws eks create-addon \
  --cluster-name <cluster-name> \
  --addon-name aws-ebs-csi-driver \
  --service-account-role-arn arn:aws:iam::<account-id>:role/AmazonEKS_EBS_CSI_DriverRole
```

**Verify installation:**
```bash
kubectl get pods -n kube-system | grep ebs-csi
# Should show: ebs-csi-controller and ebs-csi-node pods running
```

---

## EBS Volume Types and StorageClasses

### Available EBS Volume Types

| Volume Type | StorageClass | Performance | Use Case | Cost | IOPS | Throughput |
|-------------|--------------|-------------|----------|------|------|------------|
| **gp3** | `gp3` | General Purpose SSD | **Recommended** - Most workloads | $$ | 3,000-16,000 | 125-1,000 MB/s |
| **gp2** | `gp2` | General Purpose SSD | Legacy (use gp3 instead) | $$ | 100-16,000 (scales with size) | Up to 250 MB/s |
| **io1** | `io1` | Provisioned IOPS SSD | High-performance databases | $$$$ | 100-64,000 | Up to 1,000 MB/s |
| **io2** | `io2` | Provisioned IOPS SSD | Mission-critical + Multi-Attach | $$$$ | 100-64,000 | Up to 1,000 MB/s |
| **st1** | `st1` | Throughput Optimized HDD | Big data, data warehouses | $ | 500 (baseline) | Up to 500 MB/s |
| **sc1** | `sc1` | Cold HDD | Infrequent access, archives | $ | 250 (baseline) | Up to 250 MB/s |

### Recommended Volume Types by Workload

| Workload | Recommended Type | Reasoning |
|----------|-----------------|-----------|
| **PostgreSQL/MySQL** | `gp3` (or `io1/io2` for high load) | Balanced performance and cost |
| **MongoDB/Cassandra** | `gp3` or `io2` | Good IOPS, consider io2 for clustering |
| **Redis (persistent)** | `gp3` | Fast enough for most use cases |
| **Elasticsearch** | `gp3` or `io1` | Depends on query load |
| **General apps** | `gp3` | Best price/performance ratio |
| **Logs/backups** | `sc1` or `st1` | Low cost for infrequent access |

---

## Basic Usage - PostgreSQL on EKS

### Simple PVC Configuration

**No need to create PersistentVolume manually!** Just create a PVC:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: demo-app
spec:
  storageClassName: gp3  # AWS EBS gp3 volume
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi  # 20GB for production
```

**What happens automatically:**
1. PVC is created with `storageClassName: gp3`
2. EBS CSI driver sees the PVC
3. AWS API is called to create a 20GB gp3 EBS volume
4. PersistentVolume is created automatically
5. PVC binds to the PV
6. When pod is scheduled, EBS volume is attached to the worker node
7. Pod mounts the volume and starts

### Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: demo-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15.8
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
              subPath: postgres
      volumes:
        - name: postgres-data
          persistentVolumeClaim:
            claimName: postgres-pvc
```

### Verification

```bash
# Check PVC is Bound
kubectl get pvc -n demo-app

# Check PV was created automatically
kubectl get pv

# Check EBS volume in AWS
aws ec2 describe-volumes \
  --filters "Name=tag:kubernetes.io/cluster/<cluster-name>,Values=owned" \
  --region us-east-1

# Check pod is running
kubectl get pods -n demo-app -l app=postgres
```

---

## Custom StorageClasses

### High-Performance gp3 StorageClass

For workloads needing more IOPS/throughput:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: high-performance-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "10000"       # Baseline 3,000, max 16,000
  throughput: "500"   # MB/s, baseline 125, max 1,000
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/abcd1234-..."  # Optional
volumeBindingMode: WaitForFirstConsumer  # Wait until pod is scheduled
allowVolumeExpansion: true
reclaimPolicy: Delete
```

**Usage:**
```yaml
spec:
  storageClassName: high-performance-gp3
```

### Provisioned IOPS (io2) StorageClass

For high-performance databases:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: io2-high-iops
provisioner: ebs.csi.aws.com
parameters:
  type: io2
  iops: "20000"  # Up to 64,000 IOPS
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain  # Keep volume after PVC deletion
```

### Cost-Optimized (sc1) StorageClass

For backups and infrequent access:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: cold-storage
provisioner: ebs.csi.aws.com
parameters:
  type: sc1  # Cold HDD - cheapest option
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Delete
```

---

## Volume Snapshots and Backups

### Creating VolumeSnapshot

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot-20241204
  namespace: demo-app
spec:
  volumeSnapshotClassName: ebs-csi-snapshot-class
  source:
    persistentVolumeClaimName: postgres-pvc
```

### VolumeSnapshotClass Configuration

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-csi-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Delete  # Or Retain to keep snapshots
parameters:
  tagSpecification_1: "Name=Environment,Value=production"
  tagSpecification_2: "Name=Application,Value=postgres"
```

### Restore from Snapshot

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc-restored
  namespace: demo-app
spec:
  storageClassName: gp3
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  dataSource:
    name: postgres-snapshot-20241204
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

### Automated Backup with CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-snapshot
  namespace: demo-app
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: snapshot-creator
          containers:
            - name: snapshot
              image: bitnami/kubectl:latest
              command:
                - /bin/sh
                - -c
                - |
                  kubectl create -f - <<EOF
                  apiVersion: snapshot.storage.k8s.io/v1
                  kind: VolumeSnapshot
                  metadata:
                    name: postgres-snapshot-$(date +%Y%m%d-%H%M%S)
                    namespace: demo-app
                  spec:
                    volumeSnapshotClassName: ebs-csi-snapshot-class
                    source:
                      persistentVolumeClaimName: postgres-pvc
                  EOF
          restartPolicy: OnFailure
```

---

## Volume Expansion

### Enable Volume Expansion

Ensure your StorageClass has `allowVolumeExpansion: true`:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: ebs.csi.aws.com
allowVolumeExpansion: true  # Enable online resizing
```

### Expand a Volume

```bash
# Patch the PVC to increase size
kubectl patch pvc postgres-pvc -n demo-app -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'

# Watch the expansion process
kubectl get pvc postgres-pvc -n demo-app -w

# Verify new size
kubectl describe pvc postgres-pvc -n demo-app
```

**Notes:**
- ✅ **gp3, gp2, io1, io2:** Support online expansion (no downtime)
- ✅ **File system automatically resized** by the CSI driver
- ❌ **Cannot shrink volumes** - only expansion is supported
- ⚠️ **EBS volume must be at least 6 hours old** before first modification

---

## Multi-AZ High Availability

### Understanding EBS and Availability Zones

**Critical Limitation: EBS volumes are AZ-specific**

```
Availability Zone us-east-1a        Availability Zone us-east-1b
┌─────────────────────────┐        ┌─────────────────────────┐
│  EBS Volume (20 GB)     │        │                         │
│  ↓                      │        │                         │
│  Pod (postgres-0)       │        │  Pod CANNOT use         │
│  (Can mount)            │        │  the AZ-1a volume!      │
└─────────────────────────┘        └─────────────────────────┘
         ✓                                    ✗
```

**Implications:**
- Pod and its EBS volume MUST be in the same AZ
- If AZ fails, volume is unavailable
- Simple single-replica deployments are NOT multi-AZ HA

### EBS Multi-Attach (io2) - Same AZ Only

**What is Multi-Attach?**
- Attach one io2 EBS volume to **multiple EC2 instances**
- All instances **must be in the SAME Availability Zone**
- Up to **16 instances** can attach to one volume
- Requires applications to handle concurrent access (clustering, locking)

**Enable Multi-Attach:**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: io2-multi-attach
provisioner: ebs.csi.aws.com
parameters:
  type: io2
  iops: "10000"
  multiAttachEnabled: "true"  # Enable Multi-Attach
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: false  # Not supported with Multi-Attach
```

**Use Cases:**
- ✅ Clustered databases (Oracle RAC, SAP HANA) in **same AZ**
- ✅ Active-active HA within **one AZ**
- ❌ **NOT for multi-AZ HA** (volume is still AZ-specific)

**Limitations:**
- Only io1 and io2 volume types
- Linux only (not Windows)
- XFS, ext4 filesystems need cluster-aware locking
- More expensive (io2 pricing)

### True Multi-AZ HA Strategies

#### Strategy 1: StatefulSet with Database Replication (Self-Managed)

**Architecture:**
```
AZ us-east-1a            AZ us-east-1b            AZ us-east-1c
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ postgres-0    │       │ postgres-1    │       │ postgres-2    │
│ (Primary)     │──────>│ (Replica)     │──────>│ (Replica)     │
│    ↓          │Stream │    ↓          │Stream │    ↓          │
│ EBS gp3 20GB  │Repl   │ EBS gp3 20GB  │Repl   │ EBS gp3 20GB  │
└───────────────┘       └───────────────┘       └───────────────┘
```

**Implementation Components:**
- **StatefulSet:** Manages postgres pods with stable identities
- **Patroni/Stolon:** Handles automatic failover and leader election
- **PostgreSQL Streaming Replication:** Replicates data between instances
- **etcd/Consul:** Distributed consensus for configuration
- **Each pod has its own EBS volume** in its AZ

**Example StatefulSet:**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: demo-app
spec:
  serviceName: postgres
  replicas: 3  # One per AZ
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values: [postgres]
              topologyKey: topology.kubernetes.io/zone  # Spread across AZs
      containers:
        - name: postgres
          image: postgres:15.8
          # ... container spec ...
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        storageClassName: gp3
        accessModes: [ReadWriteOnce]
        resources:
          requests:
            storage: 20Gi
```

**Pros:**
- ✅ True multi-AZ HA
- ✅ Each replica in different AZ with own EBS volume
- ✅ Automatic failover (with Patroni)
- ✅ Read scalability (replicas can serve reads)

**Cons:**
- ❌ Complex setup (Patroni, etcd, replication config)
- ❌ Need to manage replication lag
- ❌ Application must handle primary endpoint changes

#### Strategy 2: Amazon RDS Multi-AZ (Managed - Recommended)

**Architecture:**
```
AZ us-east-1a                    AZ us-east-1b
┌─────────────────────┐         ┌─────────────────────┐
│  RDS Primary        │         │  RDS Standby        │
│  (Active)           │────────>│  (Passive)          │
│       ↓             │Sync     │       ↓             │
│  EBS Volume         │Repl     │  EBS Volume         │
└─────────────────────┘         └─────────────────────┘
           ↓
    Single DNS Endpoint
    (Automatic failover 30-120s)
```

**Why RDS Multi-AZ is Better:**
- ✅ **Fully managed** - AWS handles everything
- ✅ **Automatic failover** (30-120 seconds)
- ✅ **Synchronous replication** (zero data loss)
- ✅ **Automated backups** with point-in-time recovery
- ✅ **Automated patching** and updates
- ✅ **Single endpoint** (DNS-based failover, transparent to app)
- ✅ **No operational overhead**

**Access from EKS:**
```yaml
# Use ExternalName service to access RDS
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: demo-app
spec:
  type: ExternalName
  externalName: postgres.c123xyz.us-east-1.rds.amazonaws.com  # RDS endpoint
```

**RDS vs Self-Managed on EKS:**

| Feature | RDS Multi-AZ | StatefulSet + Patroni |
|---------|--------------|----------------------|
| **Setup Complexity** | Low (click to deploy) | Very High (manual config) |
| **Failover Time** | 30-120s (automatic) | 30-60s (with Patroni) |
| **Data Loss Risk** | None (sync replication) | Low (depends on config) |
| **Backup/Restore** | Automated, point-in-time | Manual scripts needed |
| **Patching** | Automated, scheduled | Manual |
| **Monitoring** | CloudWatch integrated | Need to setup Prometheus |
| **Cost** | Higher (managed service) | Lower (just EKS + EBS) |
| **Control** | Limited (AWS managed) | Full control |

**Recommendation:** Use RDS Multi-AZ for production unless you have specific requirements for running in Kubernetes.

#### Strategy 3: Amazon EFS (For Shared File Systems)

**NOT recommended for databases**, but useful for other workloads:

```
AZ us-east-1a    AZ us-east-1b    AZ us-east-1c
┌────────────┐  ┌────────────┐  ┌────────────┐
│  Pod 1     │  │  Pod 2     │  │  Pod 3     │
│     ↓      │  │     ↓      │  │     ↓      │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │
      └───────────────┴───────────────┘
                      ↓
         ┌────────────────────────────┐
         │    Amazon EFS (Shared)     │
         │  (Multi-AZ, Multi-Region)  │
         └────────────────────────────┘
```

**EFS StorageClass:**
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap  # EFS Access Point
  fileSystemId: fs-1234567890abcdef0
  directoryPerms: "700"
```

**Use Cases:**
- ✅ Shared configuration files
- ✅ Media files (images, videos)
- ✅ Logs aggregation
- ✅ ReadWriteMany (RWX) workloads
- ❌ **NOT for databases** (performance issues, NFS limitations)

---

## Security Best Practices

### 1. Encryption at Rest

**Default:** EBS volumes use AWS-managed keys

**Custom KMS Key:**
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/abcd1234-..."
```

**Enforce encryption:**
```json
// IAM Policy - Deny unencrypted EBS volumes
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "ec2:CreateVolume",
    "Resource": "*",
    "Condition": {
      "Bool": {"ec2:Encrypted": "false"}
    }
  }]
}
```

### 2. IAM Permissions for EBS CSI Driver

**Least-privilege IAM policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVolume",
        "ec2:DeleteVolume",
        "ec2:AttachVolume",
        "ec2:DetachVolume",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumeStatus",
        "ec2:ModifyVolume",
        "ec2:CreateSnapshot",
        "ec2:DeleteSnapshot",
        "ec2:DescribeSnapshots"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:volume/*",
        "arn:aws:ec2:*:*:snapshot/*"
      ]
    }
  ]
}
```

### 3. Resource Tagging

**Auto-tag EBS volumes:**
```yaml
parameters:
  tagSpecification_1: "Name=Environment,Value=production"
  tagSpecification_2: "Name=Application,Value=postgres"
  tagSpecification_3: "Name=ManagedBy,Value=kubernetes"
  tagSpecification_4: "Name=CostCenter,Value=engineering"
```

**Benefits:**
- Cost allocation
- Resource tracking
- Automated cleanup
- Compliance auditing

### 4. Volume Reclaim Policies

```yaml
# Production - Retain volumes for safety
reclaimPolicy: Retain

# Development - Delete to save costs
reclaimPolicy: Delete
```

**With Retain policy:**
```bash
# After deleting PVC, manually clean up PV and EBS volume
kubectl delete pv <pv-name>

aws ec2 delete-volume \
  --volume-id vol-1234567890abcdef0 \
  --region us-east-1
```

---

## Cost Optimization

### 1. Right-Size Volumes

```yaml
# Don't over-provision
storage: 100Gi  # ❌ If you only need 20Gi

# Use appropriate sizes
storage: 20Gi   # ✅ Start small, expand if needed
```

### 2. Choose Cost-Effective Volume Types

| Workload | Volume Type | Monthly Cost (100GB) |
|----------|-------------|---------------------|
| Production DB | gp3 | ~$8 |
| Dev/Test DB | gp3 (lower IOPS) | ~$8 |
| Backups | sc1 | ~$1.5 |
| Archives | sc1 | ~$1.5 |

### 3. Delete Unused Volumes

**Find orphaned volumes:**
```bash
# List volumes not attached to any instance
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" \
  --query "Volumes[*].[VolumeId,Size,CreateTime]" \
  --output table
```

**Set up automated cleanup with Lambda:**
- Tag volumes with expiry dates
- Lambda function deletes expired volumes
- Saves costs on forgotten dev/test volumes

### 4. Use Lifecycle Policies for Snapshots

```yaml
# Delete old snapshots automatically
apiVersion: v1
kind: ConfigMap
metadata:
  name: snapshot-retention-policy
data:
  retention_days: "30"  # Keep snapshots for 30 days
```

### 5. Monitor and Alert on Costs

```bash
# CloudWatch alarm for high EBS costs
aws cloudwatch put-metric-alarm \
  --alarm-name high-ebs-costs \
  --alarm-description "Alert when EBS costs exceed $500/month" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold
```

---

## Monitoring and Troubleshooting

### Key Metrics to Monitor

**EBS Volume Metrics (CloudWatch):**
- `VolumeReadBytes` / `VolumeWriteBytes` - I/O throughput
- `VolumeReadOps` / `VolumeWriteOps` - IOPS usage
- `VolumeThroughputPercentage` - Throughput utilization
- `VolumeQueueLength` - I/O queue depth
- `BurstBalance` - Credit balance for gp2 volumes

**Kubernetes Metrics:**
```bash
# Check PVC status
kubectl get pvc --all-namespaces

# Check PV status
kubectl get pv

# Check EBS CSI driver pods
kubectl get pods -n kube-system | grep ebs-csi

# View CSI driver logs
kubectl logs -n kube-system -l app=ebs-csi-controller
```

### Common Issues

#### Issue 1: PVC Stuck in Pending

```bash
# Describe PVC for events
kubectl describe pvc <pvc-name> -n <namespace>

# Common causes:
# - EBS CSI driver not installed
# - Invalid storageClassName
# - AWS IAM permissions issues
# - EBS volume quota exceeded
```

#### Issue 2: Volume Attachment Timeout

```bash
# Check EBS CSI node pods
kubectl get pods -n kube-system -l app=ebs-csi-node

# Check AWS EC2 instance limits
# Each instance type has max attachable volumes
# t3.medium: 28 volumes, t3.large: 28, m5.large: 28
```

#### Issue 3: Snapshot Creation Fails

```bash
# Check VolumeSnapshotClass exists
kubectl get volumesnapshotclass

# Check CSI snapshotter pods
kubectl get pods -n kube-system | grep snapshot

# Verify IAM permissions for snapshots
# (ec2:CreateSnapshot, ec2:DeleteSnapshot)
```

---

## Production Checklist

Before deploying to production:

- [ ] **EBS CSI Driver installed** with proper IAM role
- [ ] **StorageClasses defined** (gp3 as default)
- [ ] **Encryption enabled** on all StorageClasses
- [ ] **VolumeSnapshotClass configured** for backups
- [ ] **Automated snapshot CronJobs** deployed
- [ ] **Snapshot retention policy** defined (e.g., 30 days)
- [ ] **Volume reclaim policy** set appropriately (Retain for prod)
- [ ] **Resource tagging** configured for cost allocation
- [ ] **Monitoring and alerting** set up (CloudWatch, Prometheus)
- [ ] **Cost alerts** configured for EBS spending
- [ ] **Disaster recovery plan** documented
- [ ] **Multi-AZ strategy** implemented (RDS or StatefulSet)
- [ ] **Backup/restore procedures** tested
- [ ] **Volume expansion tested** (if needed)

---

## Migration from Local to EKS

### Step-by-Step Migration

1. **Update StorageClass in manifests:**
   ```yaml
   # Change from:
   storageClassName: manual

   # To:
   storageClassName: gp3
   ```

2. **Remove manual PV files:**
   ```bash
   # Delete local PV manifests
   rm deploy/postgres-pv.yaml
   ```

3. **Increase storage sizes for production:**
   ```yaml
   # Local: 1Gi
   # EKS Production: 20Gi or more
   storage: 20Gi
   ```

4. **Add volume snapshots:**
   ```bash
   kubectl apply -f backup/volumesnapshot-cronjob.yaml
   ```

5. **Test failover scenarios:**
   ```bash
   # Test AZ failure, volume expansion, restore from snapshot
   ```

---

## Additional Resources

- [AWS EBS CSI Driver Documentation](https://github.com/kubernetes-sigs/aws-ebs-csi-driver)
- [EBS Volume Types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html)
- [EKS Storage Best Practices](https://aws.github.io/aws-eks-best-practices/storage/)
- [Amazon RDS Multi-AZ](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-04 | v1.0 | Initial AWS EKS storage documentation with EBS CSI driver, Multi-AZ HA strategies, and production best practices |
