#!/usr/bin/env python3
"""
Diagrams skill helper script.
- Validates environment (graphviz, diagrams library)
- Generates boilerplate diagram code from a simple spec
"""

import subprocess
import sys
import shutil


def check_graphviz():
    """Check if Graphviz is installed."""
    if shutil.which("dot"):
        result = subprocess.run(["dot", "-V"], capture_output=True, text=True)
        version = result.stderr.strip() if result.stderr else "unknown"
        print(f"✓ Graphviz installed: {version}")
        return True
    else:
        print(
            "✗ Graphviz not found. Install with: brew install graphviz (macOS) "
            "or apt-get install graphviz (Debian/Ubuntu)"
        )
        return False


def check_diagrams():
    """Check if diagrams library is installed."""
    try:
        import diagrams

        print(f"✓ diagrams library installed: {diagrams.__version__}")
        return True
    except ImportError:
        print("✗ diagrams library not found. Install with: pip install diagrams")
        return False


def validate_environment():
    """Run all environment checks."""
    print("Checking environment...\n")
    results = [check_graphviz(), check_diagrams()]
    print()
    if all(results):
        print("Environment ready for diagram generation.")
        return True
    else:
        print("Please fix the issues above before proceeding.")
        return False


def generate_boilerplate(
    name: str, provider: str = "aws", direction: str = "TB", output_format: str = "png"
) -> str:
    """Generate boilerplate diagram code."""

    provider_imports = {
        "aws": """from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.database import RDS, DynamoDB
from diagrams.aws.network import ELB, Route53, VPC
from diagrams.aws.storage import S3
from diagrams.aws.integration import SQS, SNS""",
        "azure": """from diagrams.azure.compute import VM, FunctionApps, AKS
from diagrams.azure.database import SQLDatabases, CosmosDb
from diagrams.azure.network import LoadBalancers, ApplicationGateway
from diagrams.azure.storage import BlobStorage""",
        "gcp": """from diagrams.gcp.compute import GCE, Functions, GKE
from diagrams.gcp.database import BigQuery, SQL
from diagrams.gcp.network import LoadBalancing
from diagrams.gcp.storage import GCS
from diagrams.gcp.analytics import PubSub, Dataflow""",
        "k8s": """from diagrams.k8s.compute import Pod, Deployment, StatefulSet
from diagrams.k8s.network import Service, Ingress
from diagrams.k8s.storage import PV, PVC
from diagrams.k8s.clusterconfig import HPA""",
        "onprem": """from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL, MySQL, Redis
from diagrams.onprem.network import Nginx, HAProxy
from diagrams.onprem.queue import Kafka, RabbitMQ
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.client import Users""",
    }

    imports = provider_imports.get(provider, provider_imports["aws"])
    filename = name.lower().replace(" ", "_")

    return f'''"""
Diagram: {name}
Generated boilerplate - customize as needed
"""
from diagrams import Diagram, Cluster, Edge
{imports}

# Graph attributes for customization
graph_attr = {{
    "fontsize": "16",
    "bgcolor": "white",
    # "splines": "ortho",  # Uncomment for right-angle edges
    # "nodesep": "1.0",    # Increase node spacing
    # "ranksep": "1.5",    # Increase rank spacing
}}

with Diagram(
    "{name}",
    show=False,
    filename="{filename}",
    outformat="{output_format}",
    direction="{direction}",
    graph_attr=graph_attr,
):
    # TODO: Add your nodes here
    # Example:
    # with Cluster("Group Name"):
    #     node1 = EC2("instance-1")
    #     node2 = EC2("instance-2")
    #
    # node1 >> node2  # Create connection
    pass
'''


USAGE = """Usage:
  python3 scripts/diagram_helper.py validate
  python3 scripts/diagram_helper.py boilerplate <name> [provider] [direction] [format]

Providers: aws, azure, gcp, k8s, onprem
Directions: TB (top-bottom), LR (left-right), BT, RL
Formats: png, svg, pdf, jpg"""


def main():
    # Asking what this does is not an error: `--help` and a bare call both answer 0,
    # so a model can discover the script instead of reading exit 1 as "wrong tool".
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    command = sys.argv[1]

    if command == "validate":
        success = validate_environment()
        sys.exit(0 if success else 1)

    elif command == "boilerplate":
        if len(sys.argv) < 3:
            print("Error: Name required for boilerplate")
            sys.exit(1)

        name = sys.argv[2]
        provider = sys.argv[3] if len(sys.argv) > 3 else "aws"
        direction = sys.argv[4] if len(sys.argv) > 4 else "TB"
        fmt = sys.argv[5] if len(sys.argv) > 5 else "png"

        code = generate_boilerplate(name, provider, direction, fmt)
        print(code)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
