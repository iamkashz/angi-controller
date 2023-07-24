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

I have pushed `linux/amd64` & `linux/arm64` (for Apple Silicon) builds to
Dockerhub ([link](https://hub.docker.com/repository/docker/iamkashz/angi-controller)) for quick image fetch to deploy
the controller.

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

## Tests

```bash
python3 -m unittest -v tests/unit_test_controller.py
python3 -m unittest -v tests/integration_test_controller.py
```

## Interacting with the podinfo container

1. Command to port forward using `kubectl` on 8080

```bash
kubectl port-forward svc/<customAppName>-podinfo-svc 8080:8080
```

2. Access http://localhost:8080 via browser to view the podinfo container

3. Use `helper.py` to interact with redis store
```bash
> python3 helper.py

POST key value

PUT key value

GET key

QUIT
```

# Cleanup Steps

1. Identify all resources for `myappresources.my.api.group` and delete them

```bash
kubectl get myappresources.my.api.group
kubectl delete myappresources.my.api.group <customAppName>
```

2. Clean up controller

```bash
kubectl delete deployment kopf-controller
kubectl delete -f kopf-controller-role.yaml
```

3. Delete CRD

```bash
kubectl delete -f myappresource-crd.yaml
```

# Controller details

Once the controller is deployed, it watches for events for `('my.api.group', 'v1alpha1', 'myappresources')` and
responds. There are 3 major responses:

1. When a new customApp is deployed (`@kopf.on.create`), the controller creates the podinfo deployment and service.
   If `redis.enabled=true`, it creates the redis deployment and service and ensures proper env_vars are configured.
2. When an existing customApp is updated / patched (`@kopf.on.update`), the controller attempts to figure out what has
   changed between the
   old and new spec. The redis check is to ensure proper values env_vars in the podinfo deployment
3. When a customApp is deleted (`@kopf.on.delete`), the controller deletes any existing (podinfo+redis) deployment and
   service.

# References

- [Kopf: Kubernetes Operators Framework](https://kopf.readthedocs.io/en/stable/)
- [Python Kubernetes-client](https://github.com/kubernetes-client/python)
- [Python unittest](https://docs.python.org/3/library/unittest.html)
- [Kubernetes Operators](https://developers.redhat.com/articles/2021/06/22/kubernetes-operators-101-part-2-how-operators-work#the_structure_of_kubernetes_operators)
- [Operator Pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Controller reconcile function](https://kubebyexample.com/learning-paths/operator-framework/operator-sdk-go/controller-reconcile-function)
- [Controllers and Reconciliation](https://cluster-api.sigs.k8s.io/developer/providers/implementers-guide/controllers_and_reconciliation.html)
