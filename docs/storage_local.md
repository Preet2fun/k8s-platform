# Storage Configuration - Local Kubernetes Cluster

## Overview

This document describes the persistent storage setup for the local 3-node Kubernetes cluster. For AWS EKS storage configuration, see `storage_aws.md`.

## Problem Statement

Bare-metal Kubernetes clusters (installed via kubeadm, kubespray, etc.) do not come with a default StorageClass or dynamic volume provisioner. This causes PersistentVolumeClaims (PVCs) to remain unbound, preventing stateful applications like PostgreSQL from starting.

**Error Symptom:**
```
Warning  FailedScheduling  pod has unbound immediate PersistentVolumeClaims
0/3 nodes are available: pod has unbound immediate PersistentVolumeClaims
```

## Solution: Manual hostPath PersistentVolume

For the local learning environment, we use **manual hostPath PersistentVolumes**, which:
- Use local storage on worker nodes
- Are created manually for each application
- Store data in a directory on the node (e.g., `/mnt/data/postgres`)
- Simple and suitable for learning and testing
- No additional components required

### Version Information
- **Kubernetes version:** 1.20+
- **StorageClass name:** `manual` (custom, no provisioner)
- **Storage backend:** hostPath (local node directory)

---

## Implementation

### 1. Create PersistentVolume Manifest

Create `deploy/postgres-pv.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgres-pv
  labels:
    type: local
spec:
  storageClassName: manual
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain  # Data persists after PVC deletion
  hostPath:
    path: "/mnt/data/postgres"  # Directory on the worker node
    type: DirectoryOrCreate      # Creates directory if it doesn't exist
```

**Key Configuration:**
- **storageClassName:** `manual` - Custom name, must match in PVC
- **capacity:** Amount of storage to allocate
- **accessModes:** `ReadWriteOnce` - Volume can be mounted by one node at a time
- **persistentVolumeReclaimPolicy:** `Retain` - Data kept after PVC deletion
- **hostPath.type:** `DirectoryOrCreate` - Creates directory if missing

### 2. Update PVC to Use Manual StorageClass

In `deploy/postgres.yaml`, update the PVC:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  storageClassName: manual  # Must match PV's storageClassName
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi  # Must be <= PV capacity
```

### 3. Deploy to Cluster

```bash
# Create the PersistentVolume (cluster-wide, no namespace)
kubectl apply -f deploy/postgres-pv.yaml

# Verify PV is Available
kubectl get pv postgres-pv

# Delete old unbound PVC if it exists
kubectl delete pvc postgres-pvc -n demo-app 2>/dev/null || true

# Deploy postgres (creates PVC and Deployment)
kubectl apply -f deploy/postgres.yaml -n demo-app

# Verify PVC is Bound
kubectl get pvc -n demo-app

# Verify PV is Bound
kubectl get pv postgres-pv

# Check postgres pod is running
kubectl get pods -n demo-app -l app=postgres
```

---

## How It Works

### Binding Process

1. **PV Created:** Admin manually creates PV with `storageClassName: manual`
2. **PV Status:** Available (waiting for a matching PVC)
3. **PVC Created:** Application creates PVC with `storageClassName: manual`
4. **Matching:** Kubernetes finds PV with matching storageClassName and capacity
5. **Binding:** PVC binds to PV (both show status: Bound)
6. **Pod Scheduled:** Pod can now be scheduled to the node
7. **Volume Mounted:** hostPath directory is mounted into the container

### Storage Location

Data is stored on the worker node at:
```
/mnt/data/postgres/
```

To verify, SSH to the worker node where the pod is running:
```bash
# Find which node the pod is on
kubectl get pod -n demo-app -l app=postgres -o wide

# SSH to that node
ssh user@worker-node-ip

# Check the directory
ls -la /mnt/data/postgres/
```

You should see PostgreSQL data files (base/, global/, pg_wal/, etc.).

---

## Verification Commands

```bash
# Check PersistentVolume status
kubectl get pv

# Describe PV for details
kubectl describe pv postgres-pv

# Check PersistentVolumeClaim status
kubectl get pvc -n demo-app

# Describe PVC for binding info
kubectl describe pvc postgres-pvc -n demo-app

# Check which node the pod is on
kubectl get pod -n demo-app -l app=postgres -o wide

# View pod events
kubectl describe pod -n demo-app -l app=postgres

# Check postgres logs
kubectl logs -n demo-app -l app=postgres
```

---

## Troubleshooting

### Issue 1: PVC Stays in Pending State

**Symptoms:**
```bash
kubectl get pvc -n demo-app
NAME           STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
postgres-pvc   Pending                                      manual         5m
```

**Possible Causes:**

1. **No matching PV exists**
   ```bash
   # Check if PV exists and is Available
   kubectl get pv

   # If missing, create it:
   kubectl apply -f deploy/postgres-pv.yaml
   ```

2. **StorageClass name mismatch**
   ```bash
   # Check PV storageClassName
   kubectl get pv postgres-pv -o jsonpath='{.spec.storageClassName}'

   # Check PVC storageClassName
   kubectl get pvc postgres-pvc -n demo-app -o jsonpath='{.spec.storageClassName}'

   # They must match exactly!
   ```

3. **Capacity mismatch**
   ```bash
   # PVC requests more storage than PV offers
   # Solution: Increase PV capacity or decrease PVC request
   ```

4. **AccessMode mismatch**
   ```bash
   # PV and PVC must have compatible access modes
   kubectl describe pv postgres-pv | grep "Access Modes"
   kubectl describe pvc postgres-pvc -n demo-app | grep "Access Modes"
   ```

### Issue 2: Pod Stuck in Pending (Volume Not Attached)

**Symptoms:**
```bash
kubectl get pods -n demo-app
NAME                        READY   STATUS    RESTARTS   AGE
postgres-7d4f8c9b5d-xxxxx   0/1     Pending   0          5m
```

**Diagnosis:**
```bash
kubectl describe pod -n demo-app -l app=postgres
# Look for: "pod has unbound immediate PersistentVolumeClaims"
```

**Solution:**
- Ensure PVC is Bound first: `kubectl get pvc -n demo-app`
- If PVC is Pending, see "Issue 1" above

### Issue 3: Permission Denied Errors in Pod Logs

**Symptoms:**
```bash
kubectl logs -n demo-app -l app=postgres
# Error: could not open file "/var/lib/postgresql/data/...": Permission denied
```

**Cause:** Pod's securityContext user doesn't have permissions on hostPath directory

**Solution (SSH to worker node):**
```bash
# Option 1: Change directory ownership
sudo chown -R 999:999 /mnt/data/postgres
# (999 is postgres user UID in the container)

# Option 2: Use permissive permissions (for testing only!)
sudo chmod -R 777 /mnt/data/postgres
```

### Issue 4: Cannot Delete PVC - Stuck in Terminating

**Symptoms:**
```bash
kubectl delete pvc postgres-pvc -n demo-app
# PVC stays in Terminating state forever
```

**Cause:** PVC is still being used by a pod

**Solution:**
```bash
# 1. Find and delete pods using this PVC
kubectl get pods -n demo-app -o yaml | grep postgres-pvc
kubectl delete pod -n demo-app <pod-name>

# 2. Wait a moment, then check PVC
kubectl get pvc -n demo-app

# 3. If still stuck, remove finalizers (use with caution!)
kubectl patch pvc postgres-pvc -n demo-app -p '{"metadata":{"finalizers":null}}'
```

---

## Limitations & Considerations

### 1. **Node-Local Storage**
- ❌ Data is stored on a specific worker node
- ❌ If the node fails, data may be lost or inaccessible
- ❌ Pod cannot be scheduled to a different node (volume is not portable)
- ✅ Fine for learning and development
- ❌ **NOT suitable for production HA**

### 2. **No Dynamic Provisioning**
- ❌ You must manually create a PV for each application
- ❌ Tedious for many applications
- ✅ Simple and no extra components needed
- 💡 **Alternative:** Install local-path-provisioner for dynamic provisioning

### 3. **Access Modes**
- ✅ **ReadWriteOnce (RWO):** Supported (volume on one node at a time)
- ❌ **ReadWriteMany (RWX):** NOT supported (hostPath is node-local)
- ❌ **ReadOnlyMany (ROX):** NOT supported

### 4. **Backup Strategy**
Since data is node-local:
- Implement application-level backups (e.g., `pg_dump` for PostgreSQL)
- Store backups externally (another server, S3, etc.)
- Document restore procedures

**Example backup script:**
```bash
#!/bin/bash
# backup-postgres.sh
kubectl exec -n demo-app deployment/postgres -- \
  pg_dump -U demo_user demo > backup-$(date +%Y%m%d-%H%M%S).sql
```

### 5. **No Volume Expansion**
- ❌ Cannot resize the PV after creation
- Must create a new PV with larger capacity and migrate data

### 6. **Disk Space Management**
- Monitor disk space on worker nodes
- hostPath doesn't enforce storage limits
- Application can fill up the node's disk

---

## Production-Grade Alternatives

For production deployments in a local/on-prem environment, consider:

### Option 1: Local Path Provisioner (Recommended for Dev/Test)

**Pros:**
- Dynamic volume provisioning (no manual PV creation)
- Lightweight and easy to install
- Good for development and testing

**Cons:**
- Still node-local storage (no HA)
- No replication

**Installation:**
```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml

# Set as default StorageClass
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### Option 2: NFS Provisioner (For Shared Storage)

**Pros:**
- ReadWriteMany (RWX) support
- Shared storage across nodes
- Centralized storage management

**Cons:**
- NFS server is a single point of failure
- Performance limitations
- Requires separate NFS server setup

**Use Case:** Shared configurations, logs, media files (not databases)

### Option 3: Rook-Ceph (For Distributed Storage)

**Pros:**
- Distributed storage with replication
- Self-healing and HA
- Block, file, and object storage

**Cons:**
- Complex to set up and manage
- Requires significant resources (CPU, memory, disk)
- Steep learning curve

**Use Case:** Production on-prem with HA requirements

### Option 4: Longhorn (Simpler Distributed Storage)

**Pros:**
- Easier than Ceph
- Built-in snapshots and backups
- Good UI for management

**Cons:**
- Still requires resources
- Less mature than Ceph

**Use Case:** Production on-prem with moderate HA needs

---

## Comparison Table

| Solution | Dynamic Provisioning | HA / Replication | RWX Support | Complexity | Production Ready |
|----------|---------------------|------------------|-------------|------------|------------------|
| **hostPath (manual PV)** | ❌ No | ❌ No | ❌ No | Low | ❌ No |
| **local-path-provisioner** | ✅ Yes | ❌ No | ❌ No | Low | ⚠️ Dev/Test only |
| **NFS Provisioner** | ✅ Yes | ⚠️ Single NFS | ✅ Yes | Medium | ⚠️ For shared files |
| **Rook-Ceph** | ✅ Yes | ✅ Yes | ✅ Yes | Very High | ✅ Yes |
| **Longhorn** | ✅ Yes | ✅ Yes | ✅ Yes | High | ✅ Yes |

---

## Best Practices for Local Development

### 1. **Use Specific Storage Sizes**
```yaml
# Don't use tiny sizes
storage: 1Gi  # ✅ Good for testing

# Use realistic sizes for development
storage: 5Gi  # Better matches production testing needs
```

### 2. **Label Your PVs**
```yaml
metadata:
  name: postgres-pv
  labels:
    type: local
    app: postgres
    environment: dev
```

### 3. **Use Retain Reclaim Policy**
```yaml
persistentVolumeReclaimPolicy: Retain  # ✅ Keep data after PVC deletion
# NOT: Delete (too risky for learning)
```

### 4. **Document Storage Locations**
Keep a mapping of PVs to node directories:
```
postgres-pv    → /mnt/data/postgres
redis-pv       → /mnt/data/redis
mongodb-pv     → /mnt/data/mongodb
```

### 5. **Regular Backups (Even in Dev)**
Practice backup/restore procedures:
```bash
# Backup
kubectl exec -n demo-app deployment/postgres -- \
  pg_dump -U demo_user demo > backup.sql

# Restore
kubectl exec -i -n demo-app deployment/postgres -- \
  psql -U demo_user demo < backup.sql
```

---

## Migration to AWS EKS

When moving to AWS EKS, you'll switch from manual hostPath to dynamic EBS provisioning:

### Key Changes:

1. **Remove `deploy/postgres-pv.yaml`** (not needed in EKS)
2. **Update `storageClassName` in PVC:**
   ```yaml
   # Local
   storageClassName: manual

   # EKS
   storageClassName: gp3
   ```
3. **Increase storage size for production:**
   ```yaml
   # Local
   storage: 1Gi

   # EKS Production
   storage: 20Gi
   ```

See `storage_aws.md` for complete EKS storage configuration.

---

## Additional Resources

- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [hostPath Volume Type](https://kubernetes.io/docs/concepts/storage/volumes/#hostpath)
- [Local Path Provisioner](https://github.com/rancher/local-path-provisioner)
- [Rook-Ceph Documentation](https://rook.io/docs/rook/latest/)

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-04 | v1.0 | Initial documentation with manual hostPath PV implementation |
