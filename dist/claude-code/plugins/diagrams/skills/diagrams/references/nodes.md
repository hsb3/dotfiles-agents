# Node Reference

Complete import paths for commonly used nodes by provider.

## AWS

### Compute
```python
from diagrams.aws.compute import (
    EC2, EC2Instance, EC2Instances, EC2Ami, EC2AutoScaling,
    Lambda, LambdaFunction,
    ECS, ECR, EKS, Fargate,
    Batch, ElasticBeanstalk, Lightsail
)
```

### Database
```python
from diagrams.aws.database import (
    RDS, RDSInstance, Aurora, AuroraInstance,
    DynamoDB, DynamodbTable, DynamodbGlobalSecondaryIndex,
    ElastiCache, ElasticacheForMemcached, ElasticacheForRedis,
    Redshift, Neptune, DocumentDB, Timestream, QLDB
)
```

### Network
```python
from diagrams.aws.network import (
    VPC, PrivateSubnet, PublicSubnet,
    ELB, ALB, NLB, CLB,
    Route53, CloudFront, APIGateway,
    DirectConnect, VPCPeering, TransitGateway,
    InternetGateway, NATGateway
)
```

### Storage
```python
from diagrams.aws.storage import (
    S3, SimpleStorageServiceS3Bucket, S3Glacier,
    EBS, EFS, FSx, StorageGateway, Backup
)
```

### Integration
```python
from diagrams.aws.integration import (
    SQS, SNS, StepFunctions, EventBridge,
    MQ, Appsync
)
```

### Analytics
```python
from diagrams.aws.analytics import (
    Kinesis, KinesisDataStreams, KinesisDataFirehose,
    Athena, Glue, EMR, QuickSight,
    DataPipeline, LakeFormation, MSK
)
```

### Security
```python
from diagrams.aws.security import (
    IAM, IAMRole, IAMPermissions,
    Cognito, SecretsManager, KMS,
    WAF, Shield, Macie, GuardDuty
)
```

### Management
```python
from diagrams.aws.management import (
    CloudWatch, CloudTrail, Config,
    SystemsManager, TrustedAdvisor,
    ControlTower, Organizations
)
```

## Azure

### Compute
```python
from diagrams.azure.compute import (
    VM, VMScaleSet, VirtualMachineScaleSets,
    FunctionApps, AppServices, ContainerInstances,
    AKS, ACR, BatchAccounts
)
```

### Database
```python
from diagrams.azure.database import (
    SQLDatabases, SQLServers, SQLManagedInstances,
    CosmosDb, DatabaseForMariadbServers,
    DatabaseForMysqlServers, DatabaseForPostgresqlServers,
    CacheForRedis, SQLDatawarehouse
)
```

### Network
```python
from diagrams.azure.network import (
    VirtualNetworks, Subnets,
    LoadBalancers, ApplicationGateway, TrafficManager,
    CDNProfiles, DNSZones, ExpressrouteCircuits,
    Firewall, NetworkSecurityGroups
)
```

### Storage
```python
from diagrams.azure.storage import (
    StorageAccounts, BlobStorage,
    DataLakeStorage, FileStorage, QueueStorage,
    NetappFiles, StorSimple
)
```

### Integration
```python
from diagrams.azure.integration import (
    ServiceBus, EventGridDomains, EventGridTopics,
    LogicApps, APIManagement, DataFactory
)
```

## GCP

### Compute
```python
from diagrams.gcp.compute import (
    GCE, ComputeEngine, GKE, KubernetesEngine,
    Functions, AppEngine, Run, GCF
)
```

### Database
```python
from diagrams.gcp.database import (
    SQL, BigQuery, Spanner, Firestore,
    Bigtable, Datastore, Memorystore
)
```

### Network
```python
from diagrams.gcp.network import (
    LoadBalancing, CDN, DNS, VPC,
    Armor, FirewallRules, Router
)
```

### Storage
```python
from diagrams.gcp.storage import (
    GCS, Storage, Filestore, PersistentDisk
)
```

### Analytics
```python
from diagrams.gcp.analytics import (
    BigQuery, Dataflow, Dataproc, Dataprep,
    PubSub, Composer
)
```

## Kubernetes

### Compute
```python
from diagrams.k8s.compute import (
    Pod, Deployment, ReplicaSet, StatefulSet,
    DaemonSet, Job, CronJob
)
```

### Network
```python
from diagrams.k8s.network import (
    Service, Ingress, NetworkPolicy, Endpoint
)
```

### Storage
```python
from diagrams.k8s.storage import (
    PV, PVC, StorageClass, Volume
)
```

### Configuration
```python
from diagrams.k8s.clusterconfig import (
    HPA, Quota, LimitRange
)
from diagrams.k8s.podconfig import (
    ConfigMap, Secret
)
```

### Group/Infra
```python
from diagrams.k8s.group import (
    Namespace
)
from diagrams.k8s.infra import (
    Node, Master, ETCD
)
```

## On-Premises

### Compute
```python
from diagrams.onprem.compute import (
    Server, Nomad
)
```

### Database
```python
from diagrams.onprem.database import (
    PostgreSQL, MySQL, MariaDB, MongoDB,
    Cassandra, CockroachDB, ClickHouse,
    Couchbase, Couchdb, Dgraph, Druid,
    HBase, InfluxDB, Neo4J, Oracle,
    MSSQL
)
```

### Network
```python
from diagrams.onprem.network import (
    Nginx, Apache, HAProxy, Traefik,
    Consul, Envoy, Istio, Kong
)
```

### Queue
```python
from diagrams.onprem.queue import (
    Kafka, RabbitMQ, ActiveMQ, Celery, ZeroMQ
)
```

### In-Memory
```python
from diagrams.onprem.inmemory import (
    Redis, Memcached, Aerospike
)
```

### Monitoring
```python
from diagrams.onprem.monitoring import (
    Prometheus, Grafana, Datadog, Splunk,
    Nagios, Zabbix, Thanos, PagerDuty
)
```

### Logging
```python
from diagrams.onprem.logging import (
    Fluentd, FluentBit, Logstash, Loki
)
from diagrams.onprem.aggregator import Fluentd
```

### CI/CD
```python
from diagrams.onprem.ci import (
    Jenkins, GitlabCI, GithubActions, CircleCI,
    TravisCI, TeamCity, DroneCI
)
```

### Container
```python
from diagrams.onprem.container import (
    Docker, Containerd, Podman
)
```

### Client
```python
from diagrams.onprem.client import (
    Users, User, Client
)
```

### Analytics
```python
from diagrams.onprem.analytics import (
    Spark, Flink, Hadoop, Hive, Beam,
    Dbt, Presto, Trino, Tableau
)
```

## Generic

```python
from diagrams.generic.compute import Rack
from diagrams.generic.database import SQL
from diagrams.generic.network import Firewall, Router, Subnet, Switch, VPN
from diagrams.generic.storage import Storage
from diagrams.generic.os import Windows, Linux, Ubuntu, Android, IOS
from diagrams.generic.device import Mobile, Tablet
from diagrams.generic.blank import Blank  # invisible placeholder
```

## Programming Languages/Frameworks

```python
from diagrams.programming.language import (
    Python, Go, Java, JavaScript, TypeScript,
    Rust, Cpp, Csharp, Ruby, PHP, Kotlin, Swift
)

from diagrams.programming.framework import (
    React, Vue, Angular, Django, Flask,
    FastAPI, Spring, Rails, Laravel
)
```

## SaaS

```python
from diagrams.saas.analytics import Snowflake, Stitch
from diagrams.saas.cdn import Cloudflare, Fastly
from diagrams.saas.chat import Slack, Discord, Teams
from diagrams.saas.identity import Auth0, Okta
from diagrams.saas.logging import Datadog, NewRelic, Papertrail
from diagrams.saas.social import Facebook, Twitter, Github
```

## Custom Nodes

For services not included in the library:

```python
from diagrams import Diagram
from diagrams.custom import Custom

# Local icon file
node = Custom("Service Name", "./path/to/icon.png")

# Download from URL
from urllib.request import urlretrieve
urlretrieve("https://example.com/icon.png", "icon.png")
node = Custom("Service Name", "icon.png")
```
