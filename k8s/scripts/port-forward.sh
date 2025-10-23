#!/bin/bash

# Port forwarding script for Automata Workflows services
# Usage: ./port-forward.sh [environment] [service]
# Environment: dev, staging, prod
# Service: temporal, workers, all

set -e

# Default values
ENVIRONMENT=${1:-dev}
SERVICE=${2:-all}
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
    
    # Check if namespace exists
    if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
        print_error "Namespace ${NAMESPACE} does not exist. Please deploy first."
        exit 1
    fi
    
    print_status "Prerequisites check passed."
}

# Function to port forward Temporal services
port_forward_temporal() {
    print_status "Setting up port forwarding for Temporal services..."
    
    # Temporal Frontend (gRPC)
    kubectl port-forward -n ${NAMESPACE} svc/temporal-frontend 7233:7233 &
    TEMPORAL_PID=$!
    echo "Temporal gRPC: localhost:7233 (PID: ${TEMPORAL_PID})"
    
    # Temporal Web UI
    kubectl port-forward -n ${NAMESPACE} svc/temporal-web-ui 8088:8088 &
    WEB_UI_PID=$!
    echo "Temporal Web UI: http://localhost:8088 (PID: ${WEB_UI_PID})"
    
    # Save PIDs for cleanup
    echo ${TEMPORAL_PID} > /tmp/temporal-grpc.pid
    echo ${WEB_UI_PID} > /tmp/temporal-webui.pid
    
    print_status "Temporal port forwarding started."
}

# Function to port forward Worker services
port_forward_workers() {
    print_status "Setting up port forwarding for Worker services..."
    
    # Get worker services
    WORKER_SERVICES=$(kubectl get svc -n ${NAMESPACE} -l app.kubernetes.io/name=automata-workers -o jsonpath='{.items[*].metadata.name}')
    
    for service in ${WORKER_SERVICES}; do
        # Extract worker name from service name
        WORKER_NAME=$(echo ${service} | sed 's/.*-//')
        
        # Port forward HTTP endpoint
        kubectl port-forward -n ${NAMESPACE} svc/${service} 8080:8080 &
        HTTP_PID=$!
        echo "Worker ${WORKER_NAME} HTTP: http://localhost:8080 (PID: ${HTTP_PID})"
        
        # Port forward metrics endpoint
        kubectl port-forward -n ${NAMESPACE} svc/${service} 9090:9090 &
        METRICS_PID=$!
        echo "Worker ${WORKER_NAME} Metrics: http://localhost:9090/metrics (PID: ${METRICS_PID})"
        
        # Save PIDs for cleanup
        echo ${HTTP_PID} > /tmp/worker-${WORKER_NAME}-http.pid
        echo ${METRICS_PID} > /tmp/worker-${WORKER_NAME}-metrics.pid
    done
    
    print_status "Worker port forwarding started."
}

# Function to stop port forwarding
stop_port_forward() {
    print_status "Stopping port forwarding..."
    
    # Kill all saved PIDs
    for pid_file in /tmp/temporal-*.pid /tmp/worker-*.pid; do
        if [[ -f ${pid_file} ]]; then
            PID=$(cat ${pid_file})
            if kill -0 ${PID} 2>/dev/null; then
                kill ${PID}
                echo "Stopped process ${PID} from ${pid_file}"
            fi
            rm -f ${pid_file}
        fi
    done
    
    # Kill any remaining port-forward processes
    pkill -f "kubectl port-forward.*${NAMESPACE}" || true
    
    print_status "Port forwarding stopped."
}

# Function to show status
show_status() {
    print_status "Port forwarding status for namespace: ${NAMESPACE}"
    
    echo ""
    echo "Active port forwards:"
    ps aux | grep "kubectl port-forward.*${NAMESPACE}" | grep -v grep || echo "No active port forwards found."
    
    echo ""
    echo "Service URLs:"
    echo "- Temporal Web UI: http://localhost:8088"
    echo "- Temporal gRPC: localhost:7233"
    echo "- Worker HTTP: http://localhost:8080"
    echo "- Worker Metrics: http://localhost:9090/metrics"
}

# Function to handle cleanup on exit
cleanup() {
    print_status "Cleaning up port forwarding..."
    stop_port_forward
    exit 0
}

# Main logic
main() {
    # Handle cleanup signal
    trap cleanup SIGINT SIGTERM
    
    print_status "Starting port forwarding for environment: ${ENVIRONMENT}, service: ${SERVICE}"
    
    # Validate environment
    if [[ ! "${ENVIRONMENT}" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment. Use: dev, staging, or prod"
        exit 1
    fi
    
    # Validate service
    if [[ ! "${SERVICE}" =~ ^(temporal|workers|all|stop|status)$ ]]; then
        print_error "Invalid service. Use: temporal, workers, all, stop, or status"
        exit 1
    fi
    
    check_prerequisites
    
    case ${SERVICE} in
        "stop")
            stop_port_forward
            exit 0
            ;;
        "status")
            show_status
            exit 0
            ;;
        "temporal")
            port_forward_temporal
            ;;
        "workers")
            port_forward_workers
            ;;
        "all")
            port_forward_temporal
            port_forward_workers
            ;;
    esac
    
    show_status
    
    print_status "Port forwarding is active. Press Ctrl+C to stop."
    print_status "Use './port-forward.sh ${ENVIRONMENT} stop' to stop all port forwards."
    
    # Keep script running
    while true; do
        sleep 1
    done
}

# Run main function
main "$@"