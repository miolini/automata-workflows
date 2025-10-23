# Kubernetes Deployment Guide

This guide covers deploying Automata Workflows and Temporal to a Kubernetes cluster using Helm charts.

## Prerequisites

### Required Tools
- **kubectl** - Kubernetes command-line tool
- **helm** - Kubernetes package manager (v3.0+)
- **docker** - Container runtime (for building images)
- **Access to a Kubernetes cluster** (v1.20+)

### Cluster Requirements
- Minimum 2 CPU cores and 4GB RAM for development
- Minimum 4 CPU cores and 8GB RAM for production
- Persistent storage support (for PostgreSQL)
- Network access to container registries

## Architecture Overview

The deployment consists of two main components:

1. **Temporal Service** - Workflow orchestration platform
   - Frontend service (gRPC API)
   - History service
   - Matching service
   - Worker service
   - Web UI
   - PostgreSQL database

2. **Automata Workers** - Workflow execution workers
   - LLM Inference Worker
   - Repository Indexing Worker
   - Additional workers as needed

## Quick Start

### 1. Clone and Prepare

```bash
git clone <repository-url>
cd automata-workflows/k8s
```

### 2. Deploy to Development Environment

```bash
# Deploy all components
./scripts/deploy.sh dev all

# Or deploy components separately
./scripts/deploy.sh dev temporal
./scripts/deploy.sh dev workers
```

### 3. Access Services

```bash
# Set up port forwarding
./scripts/port-forward.sh dev all

# Access services:
# - Temporal Web UI: http://localhost:8088
# - Worker HTTP: http://localhost:8080
# - Worker Metrics: http://localhost:9090/metrics
```

## Configuration

### Environment-Specific Values

Each environment has its own configuration files:

- `temporal/values-dev.yaml` - Development settings
- `temporal/values-prod.yaml` - Production settings
- `workers/values-dev.yaml` - Development worker settings
- `workers/values-prod.yaml` - Production worker settings

### Key Configuration Options

#### Temporal Configuration
- **Replica count**: Number of Temporal service instances
- **Resources**: CPU and memory limits/requests
- **PostgreSQL**: Database configuration and persistence
- **Prometheus**: Metrics collection settings

#### Worker Configuration
- **Enabled workers**: Which workers to deploy
- **Replica count**: Number of instances per worker
- **Resources**: Per-worker resource allocation
- **Environment variables**: Worker-specific configuration

### Custom Configuration

Create custom values files:

```bash
# Custom temporal values
cp temporal/values-dev.yaml temporal/values-custom.yaml
# Edit values-custom.yaml as needed

# Deploy with custom values
./scripts/deploy.sh dev temporal custom
```

## Deployment Environments

### Development Environment
- Single replica for each service
- Minimal resource allocation
- Debug logging enabled
- Small persistent volumes

### Production Environment
- Multiple replicas for high availability
- Resource limits and requests configured
- Structured JSON logging
- Large persistent volumes with SSD storage
- Pod anti-affinity rules
- Prometheus monitoring enabled

## Worker Management

### Adding New Workers

1. Update `workers/values.yaml`:

```yaml
workers:
  your_new_worker:
    enabled: true
    replicaCount: 1
    image:
      repository: automata-workflows
      tag: "latest"
    resources:
      limits:
        cpu: 500m
        memory: 1Gi
      requests:
        cpu: 250m
        memory: 512Mi
```

2. Deploy the updated configuration:

```bash
./scripts/deploy.sh <environment> workers
```

### Scaling Workers

Modify the replica count in values files:

```yaml
workers:
  llm_inference:
    replicaCount: 5  # Scale up to 5 instances
```

Then redeploy:

```bash
./scripts/deploy.sh <environment> workers
```

## Monitoring and Observability

### Metrics Collection

Enable Prometheus monitoring:

```yaml
prometheus:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 15s
```

### Logging

Configure logging levels and format:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "json"  # json, console
```

### Health Checks

Both Temporal and workers include:
- **Liveness probes**: Check if service is responsive
- **Readiness probes**: Check if service is ready to accept traffic
- **Startup probes**: Check if service has started successfully

## Security Considerations

### Network Security
- Services use ClusterIP by default (not exposed externally)
- Use Ingress controllers for external access
- Implement network policies for additional security

### Secrets Management
- Use Kubernetes secrets for sensitive data
- Reference secrets in values files:

```yaml
postgresql:
  auth:
    existingSecret: "temporal-postgres-secret"
```

### Pod Security
- Containers run as non-root users
- Read-only root filesystems
- Drop all Linux capabilities
- Security contexts enforced

## Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl get pods -n automata-dev

# Check pod logs
kubectl logs -n automata-dev -l app.kubernetes.io/name=temporal

# Describe pod for detailed information
kubectl describe pod -n automata-dev <pod-name>
```

#### Database Connection Issues
```bash
# Check PostgreSQL pod
kubectl get pods -n automata-dev -l app.kubernetes.io/name=postgresql

# Check database logs
kubectl logs -n automata-dev -l app.kubernetes.io/name=postgresql

# Test database connectivity
kubectl exec -it -n automata-dev deployment/temporal -- psql -h temporal-postgresql -U temporal -d temporal
```

#### Worker Registration Issues
```bash
# Check worker logs
kubectl logs -n automata-dev -l app.kubernetes.io/component=llm_inference

# Check Temporal connection
kubectl exec -it -n automata-dev deployment/temporal -- tctl --address temporal-frontend:7233 cluster health
```

### Performance Tuning

#### Resource Allocation
Monitor resource usage and adjust limits:

```bash
# Check resource usage
kubectl top pods -n automata-dev

# Check node resources
kubectl top nodes
```

#### Database Performance
- Use SSD storage for production
- Configure appropriate connection pools
- Monitor database metrics

## Backup and Recovery

### Database Backups

Automate PostgreSQL backups:

```yaml
# Example backup CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command:
            - pg_dump
            - -h
            - temporal-postgresql
            - -U
            - temporal
            - temporal
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### Disaster Recovery

1. **Restore from backup**: Use pg_restore to recover database
2. **Redeploy services**: Use deployment scripts to recreate services
3. **Verify functionality**: Test workflow execution

## Advanced Topics

### Horizontal Pod Autoscaling

Enable autoscaling for production:

```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Multi-Environment Deployments

Use separate namespaces for each environment:

```bash
# Development
./scripts/deploy.sh dev all

# Staging
./scripts/deploy.sh staging all

# Production
./scripts/deploy.sh prod all
```

### GitOps Integration

Integrate with GitOps tools like ArgoCD or Flux:

1. Store Helm charts in Git repository
2. Configure GitOps operator to sync changes
3. Use pull requests for deployment changes

## Maintenance

### Upgrading Temporal

```bash
# Update Temporal version in values.yaml
helm upgrade temporal ./temporal \
  --namespace automata-prod \
  --values temporal/values.yaml \
  --values temporal/values-prod.yaml
```

### Rolling Updates

Helm performs rolling updates by default:
- Updates pods one at a time
- Maintains service availability
- Rolls back on failure

### Cleanup

Remove deployments:

```bash
# Destroy specific component
./scripts/destroy.sh dev temporal

# Destroy all components
./scripts/destroy.sh dev all
```

## Support

For issues and questions:
1. Check this documentation
2. Review Kubernetes logs
3. Consult Temporal documentation
4. Contact the platform team