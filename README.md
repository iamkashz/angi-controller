# angi-controller

This is a custom controller built for take home assignment from Angi.

### File description

| Description                 | Payload                                           |
|-----------------------------|---------------------------------------------------|
| tests / *                   | Unit test files                                   |
| `Dockerfile`                | Build file for controller                         |
| `helper.py`                 | Hacky script to interact with `podinfo:8080`      |
| `kopf-controller.yaml`      | YAML for controller                               |
| `kopf-controller-role.yaml` | ClusterRole and ClusterRoleBinding for controller |
| `kopf-controller.py`        | kopf-controller code                              |
| `myappresource-crd.yaml`    | YAML CRD for customApp                            |
| `README.md`                 | Documentation                                     |
| `requirements.txt`          | Python requirements file                          |
| `sample-customApp.yaml`     | YAML for sample customApp                         |
| `setup.py`                  | Python package                                    |

# Prerequisites

- Local kubernetes setup (ex. minikube)
- Supported driver for kubernetes (ex. docker)
- Python runtime (v3.11)

# Deployment Steps

## Controller

1. Deploy Custom Resource CRD:

```bash
kubectl apply -f myappresource-crd.yaml
```

2. Apply controller permissions:

```bash
kubectl apply -f kopf-controller-role.yaml
```

3. Deploy the controller:

```bash
kubectl apply -f kopf-controller.yaml
```

## Custom Resource

Deploy the custom resource:

```bash
kubectl apply -f sample-customApp.yaml
```

### Making changes to Custom Resource

**To change ui.color:**

```bash
kubectl patch myappresources.my.api.group <customAppName> --type='json' -p='[{"op": "replace", "path": "/spec/ui/color", "value": "#4f82b8"}]'
```

**To change ui.message:**

```bash
kubectl patch myappresources.my.api.group <customAppName> --type='json' -p='[{"op": "replace", "path": "/spec/ui/message", "value": "This is a new message"}]'
```

**To change replica count:**

```bash
kubectl patch myappresources.my.api.group <customAppName> --type='json' -p='[{"op": "replace", "path": "/spec/replicaCount", "value": 5}]'
```

**To enable / disable redis:**

```bash
kubectl patch myappresources.my.api.group <customAppName> --type='json' -p='[{"op": "replace", "path": "/spec/redis/enabled", "value": true}]'
kubectl patch myappresources.my.api.group <customAppName> --type='json' -p='[{"op": "replace", "path": "/spec/redis/enabled", "value": false}]'
```

**To delete custom resource:**

```bash
kubectl delete myappresources.my.api.group <customAppName>
```

## Running the controller locally

The controller can be run locally as well.

1. Install the packages needed:

```bash
pip install -r requirements.txt
```

2. Run controller:

```bash
kopf run kopf-controller.py
```

# Tests

```bash
python3 -m unittest -v tests/unit_test_controller.py
python3 -m unittest -v tests/integration_test_controller.py
```

# Controller details

Once the controller is deployed, it watches for events for `('my.api.group', 'v1alpha1', 'myappresources')` and
responds. There are 3 major responses:

1. When a new customApp is deployed (`@kopf.on.create`), the controller creates the podinfo deployment and service.
   If `redis.enabled=true`, it creates the redis deployment and service and ensures proper env_vars are configured.
2. When an existing customApp is updated / patched (`@kopf.on.update`), the controller attempts to figure out what has between the
   old and new spec. The important check is the redis check to ensure proper values env_vars in the podinfo deployment
3. When a customApp is deleted (`@kopf.on.delete`), the controller deletes any existing (podinfo+redis) deployment and service.

# References

- [Kopf: Kubernetes Operators Framework](https://kopf.readthedocs.io/en/stable/)
- [Python Kubernetes-client](https://github.com/kubernetes-client/python)
- [Python unittest](https://docs.python.org/3/library/unittest.html)

## Information

I have pushed both `linux/amd64` & `linux/arm64` (for Apple Silicon) builds to
Dockerhub ([link](https://hub.docker.com/repository/docker/iamkashz/angi-controller)) for quick image fetch.



