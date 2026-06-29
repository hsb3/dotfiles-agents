# Architecture Patterns

Ready-to-use patterns for common architectures.

## Web Application (3-Tier)

```python
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB, Route53
from diagrams.onprem.client import Users

with Diagram("Web Application", show=False, direction="TB"):
    users = Users("Users")
    dns = Route53("DNS")
    
    with Cluster("VPC"):
        lb = ELB("Load Balancer")
        
        with Cluster("Web Tier"):
            web = [EC2("web-1"), EC2("web-2")]
        
        with Cluster("Database Tier"):
            db_primary = RDS("Primary")
            db_replica = RDS("Replica")
            db_primary - db_replica
    
    users >> dns >> lb >> web >> db_primary
```

## Event-Driven Architecture

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import SQS, SNS, EventBridge
from diagrams.aws.storage import S3
from diagrams.aws.database import DynamoDB

with Diagram("Event Driven", show=False, direction="LR"):
    trigger = S3("uploads")
    
    with Cluster("Event Bus"):
        events = EventBridge("events")
        queue = SQS("queue")
    
    with Cluster("Processors"):
        handlers = [
            Lambda("validate"),
            Lambda("transform"),
            Lambda("notify")
        ]
    
    store = DynamoDB("results")
    notify = SNS("alerts")
    
    trigger >> events
    events >> queue >> handlers
    handlers >> store
    handlers >> notify
```

## Data Lake

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.analytics import Kinesis, Glue, Athena, QuickSight
from diagrams.aws.storage import S3
from diagrams.aws.database import Redshift

with Diagram("Data Lake", show=False, direction="LR"):
    sources = Kinesis("streams")
    
    with Cluster("Data Lake"):
        raw = S3("raw/")
        processed = S3("processed/")
        curated = S3("curated/")
        
        etl = Glue("ETL")
        catalog = Glue("Catalog")
    
    with Cluster("Analytics"):
        warehouse = Redshift("warehouse")
        query = Athena("ad-hoc")
        viz = QuickSight("dashboards")
    
    sources >> raw >> etl >> processed >> etl >> curated
    curated >> warehouse >> viz
    curated >> query
    etl >> catalog
```

## CI/CD Pipeline

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.container import Docker
from diagrams.aws.compute import ECS, ECR
from diagrams.aws.devtools import Codebuild

with Diagram("CI/CD Pipeline", show=False, direction="LR"):
    repo = Github("repo")
    
    with Cluster("Build"):
        ci = GithubActions("CI")
        build = Codebuild("build")
        registry = ECR("registry")
    
    with Cluster("Deploy"):
        staging = ECS("staging")
        prod = ECS("production")
    
    repo >> ci >> build >> registry
    registry >> Edge(label="deploy") >> staging
    staging >> Edge(label="promote", style="dashed") >> prod
```

## Microservices with Service Mesh

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.k8s.compute import Pod, Deployment
from diagrams.k8s.network import Service, Ingress
from diagrams.onprem.network import Istio, Envoy

with Diagram("Service Mesh", show=False):
    ingress = Ingress("gateway")
    
    with Cluster("Istio Mesh"):
        with Cluster("Service A"):
            svc_a = Service("svc-a")
            pod_a = Pod("pod-a")
            envoy_a = Envoy("sidecar")
        
        with Cluster("Service B"):
            svc_b = Service("svc-b")
            pod_b = Pod("pod-b")
            envoy_b = Envoy("sidecar")
        
        with Cluster("Service C"):
            svc_c = Service("svc-c")
            pod_c = Pod("pod-c")
            envoy_c = Envoy("sidecar")
    
    ingress >> svc_a >> pod_a
    pod_a - envoy_a
    envoy_a >> Edge(style="dashed") >> envoy_b >> pod_b
    envoy_a >> Edge(style="dashed") >> envoy_c >> pod_c
```

## Multi-Region Deployment

```python
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import Route53, CloudFront, ELB

with Diagram("Multi-Region", show=False, direction="TB"):
    dns = Route53("Global DNS")
    cdn = CloudFront("CDN")
    
    with Cluster("US-East"):
        lb_east = ELB("LB")
        web_east = [EC2("web-1"), EC2("web-2")]
        db_east = RDS("Primary")
    
    with Cluster("EU-West"):
        lb_west = ELB("LB")
        web_west = [EC2("web-1"), EC2("web-2")]
        db_west = RDS("Replica")
    
    dns >> cdn
    cdn >> lb_east >> web_east >> db_east
    cdn >> lb_west >> web_west >> db_west
    db_east - db_west
```

## Monitoring Stack

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.logging import Loki, Fluentd
from diagrams.onprem.tracing import Jaeger
from diagrams.onprem.network import Nginx
from diagrams.onprem.compute import Server

with Diagram("Observability", show=False):
    with Cluster("Applications"):
        apps = [Server("app-1"), Server("app-2"), Server("app-3")]
    
    with Cluster("Collection"):
        metrics = Prometheus("metrics")
        logs = Fluentd("logs")
        traces = Jaeger("traces")
    
    with Cluster("Storage & Viz"):
        loki = Loki("log store")
        grafana = Grafana("dashboards")
    
    apps >> Edge(label="metrics") >> metrics >> grafana
    apps >> Edge(label="logs") >> logs >> loki >> grafana
    apps >> Edge(label="traces") >> traces >> grafana
```

## Machine Learning Pipeline

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.ml import Sagemaker, SagemakerModel, SagemakerNotebook
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import StepFunctions

with Diagram("ML Pipeline", show=False, direction="LR"):
    data = S3("training data")
    
    with Cluster("Development"):
        notebook = SagemakerNotebook("experiment")
    
    with Cluster("Training"):
        orchestrator = StepFunctions("workflow")
        training = Sagemaker("training job")
        model_store = S3("model artifacts")
    
    with Cluster("Serving"):
        endpoint = SagemakerModel("endpoint")
        inference = Lambda("inference API")
    
    data >> notebook
    notebook >> orchestrator >> training >> model_store
    model_store >> endpoint >> inference
```

## Serverless API

```python
from diagrams import Diagram, Cluster
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.compute import Lambda
from diagrams.aws.database import DynamoDB
from diagrams.aws.security import Cognito
from diagrams.aws.storage import S3

with Diagram("Serverless API", show=False):
    cdn = CloudFront("CDN")
    auth = Cognito("Auth")
    
    with Cluster("API"):
        api = APIGateway("REST API")
        
        with Cluster("Functions"):
            create = Lambda("create")
            read = Lambda("read")
            update = Lambda("update")
            delete = Lambda("delete")
    
    db = DynamoDB("data")
    static = S3("static assets")
    
    cdn >> api
    api >> auth
    api >> [create, read, update, delete]
    [create, read, update, delete] >> db
    cdn >> static
```

## Hybrid Cloud

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import VPC, DirectConnect
from diagrams.aws.compute import EC2
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.database import PostgreSQL

with Diagram("Hybrid Cloud", show=False):
    with Cluster("On-Premises DC"):
        firewall = Nginx("firewall")
        legacy = Server("legacy app")
        local_db = PostgreSQL("database")
    
    connect = DirectConnect("Direct Connect")
    
    with Cluster("AWS VPC"):
        with Cluster("Workloads"):
            cloud_app = [EC2("app-1"), EC2("app-2")]
    
    firewall >> connect >> cloud_app
    legacy >> local_db
    cloud_app >> Edge(style="dashed") >> connect >> legacy
```

## Healthcare Data Architecture (RaptorXAI-style)

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.azure.database import SQLDatabases
from diagrams.azure.compute import FunctionApps
from diagrams.azure.storage import BlobStorage
from diagrams.onprem.analytics import Dbt
from diagrams.programming.framework import FastAPI
from diagrams.onprem.client import Users

with Diagram("Healthcare Analytics Platform", show=False, direction="TB"):
    users = Users("MAOs/ACOs")
    
    with Cluster("Ingestion"):
        blob = BlobStorage("Claims Files")
        etl = FunctionApps("dlt Pipeline")
    
    with Cluster("Data Warehouse"):
        raw = SQLDatabases("raw schema")
        staging = SQLDatabases("staging")
        mart = SQLDatabases("data marts")
        transform = Dbt("transformations")
    
    with Cluster("Analytics API"):
        api = FastAPI("API")
        agents = FunctionApps("AI Agents")
    
    users >> blob >> etl >> raw
    raw >> transform >> staging >> transform >> mart
    mart >> api >> users
    api >> agents
```
