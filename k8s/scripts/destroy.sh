#!/bin/bash

# Destroy script for Automata Workflows on Kubernetes
# Usage: ./destroy.sh [environment] [component]
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
    
    # Check if namespace exists
    if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
        print_warning "Namespace ${NAMESPACE} does not exist. Nothing to destroy."
        exit 0
    fi
    
    print_status "Prerequisites check passed."
}

# Function to destroy Temporal
destroy_temporal() {
    print_status "Destroying Temporal deployment..."
    
    if helm list -n ${NAMESPACE} | grep -q "temporal"; then
        helm uninstall temporal -n ${NAMESPACE}
        print_status "Temporal uninstalled successfully."
    else
        print_warning "Temporal release not found in namespace ${NAMESPACE}."
    fi
}

# Function to destroy Workers
destroy_workers() {
    print_status "Destroying Automata Workers deployment..."
    
    if helm list -n ${NAMESPACE} | grep -q "automata-workers"; then
        helm uninstall automata-workers -n ${NAMESPACE}
        print_status "Automata Workers uninstalled successfully."
    else
        print_warning "Automata Workers release not found in namespace ${NAMESPACE}."
    fi
}

# Function to cleanup namespace
cleanup_namespace() {
    print_status "Cleaning up namespace ${NAMESPACE}..."
    
    # Wait for pods to terminate
    kubectl delete pods --all -n ${NAMESPACE} --wait=false
    
    # Delete remaining resources
    kubectl delete all --all -n ${NAMESPACE} --wait=false
    
    # Delete PVCs (with confirmation for production)
    if [[ "${ENVIRONMENT}" == "prod" ]]; then
        read -p "This will delete all PersistentVolumeClaims in production. Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kubectl delete pvc --all -n ${NAMESPACE} --wait=false
        else
            print_warning "Skipping PVC deletion in production."
        fi
    else
        kubectl delete pvc --all -n ${NAMESPACE} --wait=false
    fi
    
    # Delete namespace
    kubectl delete namespace ${NAMESPACE} --wait=false
    
    print_status "Namespace cleanup completed."
}

# Function to show final status
show_final_status() {
    print_status "Destroy operation completed."
    echo ""
    echo "Note: Some resources may take a few minutes to be fully removed."
    echo "You can check the status with: kubectl get namespaces"
}

# Main destroy logic
main() {
    print_status "Starting destroy operation for environment: ${ENVIRONMENT}, component: ${COMPONENT}"
    
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
    
    # Additional confirmation for production
    if [[ "${ENVIRONMENT}" == "prod" ]]; then
        read -p "This will destroy production resources. Are you absolutely sure? (type 'production' to confirm): " -r
        echo
        if [[ ! $REPLY =~ ^production$ ]]; then
            print_error "Production destroy confirmation failed. Aborting."
            exit 1
        fi
    fi
    
    check_prerequisites
    
    case ${COMPONENT} in
        "temporal")
            destroy_temporal
            ;;
        "workers")
            destroy_workers
            ;;
        "all")
            destroy_workers
            destroy_temporal
            cleanup_namespace
            ;;
    esac
    
    show_final_status
}

# Handle script interruption
trap 'print_error "Destroy operation interrupted."; exit 1' INT

# Run main function
main "$@"