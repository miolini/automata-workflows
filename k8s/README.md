# Kubernetes Deployment for Automata Workflows

This directory contains Helm charts and deployment scripts for running Automata Workflows on Kubernetes.

## Directory Structure

```
k8s/
├── temporal/                    # Temporal service Helm chart
│   ├── Chart.yaml
│   ├── values.yaml              # Default values
│   ├── values-dev.yaml          # Development overrides
│   ├── values-prod.yaml         # Production overrides
│   └── templates/               # Kubernetes manifests
│       ├── configmap.yaml
│       ├── deployment.yaml
│       ├── service.yaml
│       └── _helpers.tpl
├── workers/                     # Automata workers Helm chart
│   ├── Chart.yaml
│   ├── values.yaml              # Default values
│   ├── values-dev.yaml          # Development overrides
│   ├── values-prod.yaml         # Production overrides
│   └── templates/               # Kubernetes manifests
│       ├── worker-deployment.yaml
│       ├── worker-service.yaml
│       ├── serviceaccount.yaml
│       └── _helpers.tpl
├── scripts/                     # Deployment and management scripts
│   ├── deploy.sh                # Deploy components
│   ├── destroy.sh               # Destroy deployments
│   └── port-forward.sh          # Port forwarding utility
└── docs/                        # Documentation
    └── kubernetes-deployment.md  # Detailed deployment guide
```

## Quick Start

### Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured
- Helm v3.0+
- Cluster admin permissions

### Deploy to Development

```bash
# Deploy all components
./scripts/deploy.sh dev all

# Set up port forwarding
./scripts/port-forward.sh dev all

# Access services:
# - Temporal Web UI: http://localhost:8088
# - Worker HTTP: http://localhost:8080
# - Worker Metrics: http://localhost:9090/metrics
```

## Management Scripts

### deploy.sh

Deploy components to specified environment.

```bash
./scripts/deploy.sh [environment] [component] [namespace]

# Environment: dev, staging, prod
# Component: temporal, workers, all
# Namespace: automata-{environment} (default)
```

Examples:
```bash
# Deploy all to development
./scripts/deploy.sh dev all

# Deploy only temporal to production
./scripts/deploy.sh prod temporal

# Deploy to custom namespace
./scripts/deploy.sh dev all my-namespace
```

### destroy.sh

Destroy deployments in specified environment.

```bash
./scripts/destroy.sh [environment] [component] [namespace]
```

**⚠️ Warning:** This will delete all resources in the specified namespace.

### port-forward.sh

Set up port forwarding to access services.

```bash
./scripts/port-forward.sh [environment] [service] [namespace]

# Service: temporal, workers, all, stop, status
```

Examples:
```bash
# Forward all services
./scripts/port-forward.sh dev all

# Stop all port forwarding
./scripts/port-forward.sh dev stop

# Check status
./scripts/port-forward.sh dev status
```

## Configuration

### Environment-Specific Values

Each environment has dedicated values files:

- **Development**: Minimal resources, single replicas, debug logging
- **Production**: Multiple replicas, resource limits, monitoring enabled

### Custom Configuration

Create custom values files:

```bash
# Copy and modify
cp temporal/values-dev.yaml temporal/values-custom.yaml
cp workers/values-dev.yaml workers/values-custom.yaml

# Deploy with custom values
./scripts/deploy.sh dev temporal custom
```

## Monitoring

### Health Checks

All deployments include:
- Liveness probes
- Readiness probes
- Health endpoints

### Metrics

Prometheus metrics are available at:
- Temporal: `http://localhost:9090/metrics`
- Workers: `http://localhost:9090/metrics`

### Logs

View logs with kubectl:

```bash
# Temporal logs
kubectl logs -n automata-dev -l app.kubernetes.io/name=temporal

# Worker logs
kubectl logs -n automata-dev -l app.kubernetes.io/name=automata-workers
```

## Security

### Container Security

- Non-root user execution
- Read-only root filesystem
- Minimal capabilities (all dropped)
- Resource limits enforced

### Network Security

- Services use ClusterIP (internal only)
- Use Ingress for external access
- Implement network policies as needed

### Secrets Management

Use Kubernetes secrets for sensitive data:

```yaml
# Example: Database secret
apiVersion: v1
kind: Secret
metadata:
  name: temporal-postgres-secret
type: Opaque
data:
  postgres-password: <base64-encoded-password>
  username: <base64-encoded-username>
```

## Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   kubectl get pods -n automata-dev
   kubectl describe pod -n automata-dev <pod-name>
   ```

2. **Database connection issues**
   ```bash
   kubectl logs -n automata-dev -l app.kubernetes.io/name=postgresql
   ```

3. **Worker registration issues**
   ```bash
   kubectl logs -n automata-dev -l app.kubernetes.io/component=llm_inference
   ```

### Cleanup

Remove all deployments:

```bash
./scripts/destroy.sh dev all
```

## Support

For detailed deployment instructions, see [k8s/docs/kubernetes-deployment.md](docs/kubernetes-deployment.md).

For issues and questions:
1. Check this documentation
2. Review Kubernetes logs
3. Consult the main project documentation