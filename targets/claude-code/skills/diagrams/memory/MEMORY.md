# Diagram Memory

Accumulated learnings from diagram creation. Check before starting new diagrams. Add observations after completing diagrams.

## Import Errors

### Initial - Common Import Mistakes
**Problem**: Many node classes have non-obvious import paths
**Solution**: Reference `references/nodes.md` or use these patterns:
**Example**:
```python
# AWS: category is lowercase, class is PascalCase
from diagrams.aws.compute import EC2, Lambda, ECS
from diagrams.aws.database import RDS, DynamoDB  # NOT Dynamodb

# Azure: Some names differ from service names
from diagrams.azure.database import SQLDatabases  # NOT SQL or AzureSQL
from diagrams.azure.compute import FunctionApps  # NOT Functions or AzureFunctions

# GCP: Use full names
from diagrams.gcp.compute import ComputeEngine  # Can also use GCE alias
from diagrams.gcp.database import BigQuery  # NOT BQ

# K8s: Abbreviations work
from diagrams.k8s.compute import Pod, Deployment
from diagrams.k8s.storage import PV, PVC  # PersistentVolume, PersistentVolumeClaim
```

## Layout Issues

### Initial - Default Spacing Too Tight
**Problem**: Nodes overlap or appear cramped with default settings
**Solution**: Always set explicit spacing for diagrams with 5+ nodes
**Example**:
```python
graph_attr = {
    "nodesep": "0.8",  # Default is 0.25
    "ranksep": "1.0",  # Default is 0.5
    "pad": "0.5",
}
```

### Initial - Direction Affects Readability
**Problem**: Data pipelines look confusing with default TB direction
**Solution**: Use LR for pipelines/flows, TB for hierarchies
**Example**:
```python
# Data flows: left-to-right
with Diagram("Pipeline", direction="LR"):
    source >> process >> sink

# Hierarchies: top-to-bottom  
with Diagram("Org Chart", direction="TB"):
    ceo >> [vp1, vp2, vp3]
```

## Styling Problems

### Initial - Edges Cross Through Nodes
**Problem**: Default edge routing can cross through node icons
**Solution**: Use splines="ortho" for clean right-angle routing
**Example**:
```python
graph_attr = {
    "splines": "ortho",  # Right angles only
    # OR "spline" for curved edges that avoid nodes
}
```

### Initial - Output Background Not Transparent
**Problem**: PNG has white background, doesn't embed well in docs
**Solution**: Set bgcolor to transparent
**Example**:
```python
graph_attr = {
    "bgcolor": "transparent",
}
```

## Connection/Flow Issues

### Initial - Can't Connect to Clusters
**Problem**: Edges to/from clusters don't work by default
**Solution**: Enable compound mode and use lhead/ltail
**Example**:
```python
graph_attr = {"compound": "true"}

with Diagram("Cluster Edges", graph_attr=graph_attr):
    external = Server("external")
    with Cluster("Internal"):
        internal = Server("internal")
    
    # Use lhead to point edge to cluster boundary
    external >> Edge(lhead="cluster_Internal") >> internal
```

### Initial - Edge Labels Overlap
**Problem**: Multiple labeled edges create unreadable overlaps
**Solution**: Use minlen to space out edges, or decorate=true
**Example**:
```python
a >> Edge(label="request", minlen="2") >> b
b >> Edge(label="response", minlen="2", style="dashed") >> a
```

## Provider-Specific Notes

### Initial - OnPrem Client Icons
**Problem**: Need to show users/clients but not sure which icon
**Solution**: Use diagrams.onprem.client module
**Example**:
```python
from diagrams.onprem.client import Users, User, Client

users = Users("End Users")  # Multiple people icon
user = User("Admin")        # Single person icon
client = Client("Browser")  # Computer/device icon
```

### Initial - Custom Icons for Missing Services
**Problem**: Service not available in diagrams library
**Solution**: Use Custom node with downloaded icon
**Example**:
```python
from diagrams.custom import Custom
from urllib.request import urlretrieve

# Download icon first
urlretrieve("https://example.com/icon.png", "service_icon.png")

# Use in diagram
service = Custom("My Service", "service_icon.png")
```

## General Best Practices

### Initial - Always Set show=False
**Problem**: Diagram auto-opens in viewer, breaks headless execution
**Solution**: Always set show=False in Diagram constructor
**Example**:
```python
with Diagram("Name", show=False, filename="output"):
    ...
```

### Initial - Use Explicit Filenames
**Problem**: Default filename uses diagram title with spaces replaced
**Solution**: Set explicit filename for predictable output
**Example**:
```python
with Diagram("My Complex Architecture", 
             show=False, 
             filename="my_architecture",  # Creates my_architecture.png
             outformat="png"):
    ...
```

### Initial - Test Imports Before Full Diagram
**Problem**: Import errors only surface when running full script
**Solution**: Test imports in isolation first
**Example**:
```python
# Quick import test
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
print("Imports OK")
```
