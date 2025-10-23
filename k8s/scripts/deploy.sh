#!/bin/bash

# Deployment script for Automata Workflows on Kubernetes
# Usage: ./deploy.sh [environment] [component]
# Environment: dev, staging, prod
# Component: temporal, workers, all

set -e

# Default values
ENVIRONMENT=${1:-dev}
COMPONENT=${2:-all}
NAMESPACE=${3:-automata-${ENVIRONMENT}}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed. Please install Helm first."
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    print_status "Prerequisites check passed."
}

# Function to create namespace
create_namespace() {
    print_status "Creating namespace: ${NAMESPACE}"
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
}

# Function to deploy Temporal
deploy_temporal() {
    print_status "Deploying Temporal to ${ENVIRONMENT} environment..."
    
    # Add Bitnami Helm repository if not already added
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo update
    
    # Deploy Temporal
    helm upgrade --install temporal ./temporal \
        --namespace ${NAMESPACE} \
        --values ./temporal/values.yaml \
        --values ./temporal/values-${ENVIRONMENT}.yaml \
        --wait \
        --timeout 10m
    
    print_status "Temporal deployed successfully."
}

# Function to deploy Workers
deploy_workers() {
    print_status "Deploying Automata Workers to ${ENVIRONMENT} environment..."
    
    # Deploy Workers
    helm upgrade --install automata-workers ./workers \
        --namespace ${NAMESPACE} \
        --values ./workers/values.yaml \
        --values ./workers/values-${ENVIRONMENT}.yaml \
        --wait \
        --timeout 10m
    
    print_status "Automata Workers deployed successfully."
}

# Function to show deployment status
show_status() {
    print_status "Deployment status for namespace: ${NAMESPACE}"
    kubectl get pods -n ${NAMESPACE}
    echo ""
    kubectl get services -n ${NAMESPACE}
}

# Function to show next steps
show_next_steps() {
    print_status "Deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Check the deployment status: kubectl get pods -n ${NAMESPACE}"
    echo "2. Access Temporal Web UI: kubectl port-forward -n ${NAMESPACE} svc/temporal-web-ui 8088:8088"
    echo "3. View logs: kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/name=temporal"
    echo "4. Monitor workers: kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/name=automata-workers"
    echo ""
    echo "Temporal Web UI will be available at: http://localhost:8088"
}

# Main deployment logic
main() {
    print_status "Starting deployment for environment: ${ENVIRONMENT}, component: ${COMPONENT}"
    
    # Validate environment
    if [[ ! "${ENVIRONMENT}" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment. Use: dev, staging, or prod"
        exit 1
    fi
    
    # Validate component
    if [[ ! "${COMPONENT}" =~ ^(temporal|workers|all)$ ]]; then
        print_error "Invalid component. Use: temporal, workers, or all"
        exit 1
    fi
    
    check_prerequisites
    create_namespace
    
    case ${COMPONENT} in
        "temporal")
            deploy_temporal
            ;;
        "workers")
            deploy_workers
            ;;
        "all")
            deploy_temporal
            deploy_workers
            ;;
    esac
    
    show_status
    show_next_steps
}

# Handle script interruption
trap 'print_error "Deployment interrupted."; exit 1' INT

# Run main function
main "$@"