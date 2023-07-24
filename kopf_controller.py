#!/usr/bin/env python3
import kopf
import kubernetes.client
import kubernetes.config
import logging

from kubernetes.client.models import V1Service, V1ServiceSpec, V1ServicePort
from kubernetes.client.models import V1Deployment, V1DeploymentSpec, V1PodTemplateSpec, V1ObjectMeta, V1PodSpec, \
    V1Container, V1ResourceRequirements, V1EnvVar

# initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# initialize k8s api client
try:
    kubernetes.config.load_incluster_config()
except kubernetes.config.ConfigException:
    kubernetes.config.load_kube_config()

api = kubernetes.client.AppsV1Api()
service_api = kubernetes.client.CoreV1Api()


def create_redis_deployment(api, name, namespace):
    """
    creates a redis deployment
    """
    redis_container = V1Container(
        name=f"{name}-redis",
        image="redis:latest",
    )
    redis_template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(labels={"app": f"{name}-redis"}),
        spec=V1PodSpec(containers=[redis_container]),
    )
    redis_deployment_spec = V1DeploymentSpec(
        replicas=1,
        selector={"matchLabels": {"app": f"{name}-redis"}},
        template=redis_template,
    )
    redis_deployment = V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=V1ObjectMeta(name=f"{name}-redis"),
        spec=redis_deployment_spec,
    )
    try:
        api.create_namespaced_deployment(namespace, redis_deployment)
    except Exception as e:
        logger.info(f"Failed to create {name}-redis deployment: {e}")
    else:

        logger.info(f"{name}-redis deployment created")


def create_podinfo_deployment(api, name, namespace, spec, redis_service_address):
    """
    creates podinfo deployment
    """
    labels = {'app': f"{name}-podinfo"}
    resources = spec.get('resources', {})
    ui = spec.get('ui', {})
    image_repository = spec.get('image', {}).get('repository')
    image_tag = spec.get('image', {}).get('tag')

    # Construct the podinfoContainer
    podinfoContainer = V1Container(
        name=f"{name}-podinfo",
        image=f'{image_repository}:{image_tag}',
        resources=V1ResourceRequirements(
            requests={
                "cpu": resources.get('cpuRequest'),
                "memory": resources.get('memoryLimit')
            }
        ),
        env=[
            V1EnvVar(name='PODINFO_UI_COLOR', value=ui.get('color')),
            V1EnvVar(name='PODINFO_UI_MESSAGE', value=ui.get('message')),
            V1EnvVar(name='PODINFO_CACHE_SERVER', value=redis_service_address),
        ]
    )

    template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(labels=labels),
        spec=V1PodSpec(containers=[podinfoContainer])
    )

    deployment_spec = V1DeploymentSpec(
        replicas=spec.get('replicaCount'),
        selector={'matchLabels': labels},
        template=template,
    )

    # Construct the deployment
    deployment = V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=V1ObjectMeta(name=f"{name}-podinfo"),
        spec=deployment_spec,
    )

    try:
        api.create_namespaced_deployment(namespace, deployment)
    except Exception as e:
        logger.info(f"Failed to create {name}-podInfo deployment: {e}")
    else:
        logger.info(f"{name}-podInfo deployment created")


def create_service(service_api, name, namespace, redis):
    """
    creates redis service if redis=true
    else: creates podinfo service
    """
    if redis:
        service_name = f"{name}-redis-svc"
        service_spec = V1ServiceSpec(
            selector={"app": f"{name}-redis"},
            ports=[V1ServicePort(port=6379)],
        )
        service = V1Service(
            api_version="v1",
            kind="Service",
            metadata=V1ObjectMeta(name=service_name),
            spec=service_spec,
        )
    else:
        service_name = f"{name}-podinfo-svc"
        service_spec = V1ServiceSpec(
            selector={"app": f"{name}-podinfo"},
            ports=[V1ServicePort(port=8080, target_port=9898)],
            type="NodePort",
        )

        service = V1Service(
            api_version="v1",
            kind="Service",
            metadata=V1ObjectMeta(name=service_name),
            spec=service_spec,
        )

    try:
        service_api.create_namespaced_service(namespace, service)
    except Exception as e:
        logger.info(f"Failed to create {service_name}: {e}")
    else:
        logger.info(f"{service_name} created")


@kopf.on.create('my.api.group', 'v1alpha1', 'myappresources')
def create_fn(body, meta, spec, **kwargs):
    name = meta.get('name')
    namespace = meta.get('namespace')
    logger.info(f"Creating Deployment for MyAppResource: {name}")

    # Get details from the custom resource spec
    redis_enabled = spec.get('redis', {}).get('enabled', False)

    redis_service_address = ""

    if redis_enabled:
        # Create redis deployment, service
        create_redis_deployment(api, name, namespace)
        create_service(service_api, name, namespace, redis=True)
        redis_service_address = f"tcp://{name}-redis-svc:6379"

    # Create podinfo deployment, service
    create_podinfo_deployment(api, name, namespace, spec, redis_service_address)
    create_service(service_api, name, namespace, redis=False)


@kopf.on.delete('my.api.group', 'v1alpha1', 'myappresources')
def delete(body, **kwargs):
    name = body['metadata']['name']
    namespace = body['metadata']['namespace']

    logger.info(f"Deleting Deployment for MyAppResource: {name}")

    try:
        api.delete_namespaced_deployment(f"{name}-podinfo", namespace)
        service_api.delete_namespaced_service(f"{name}-podinfo-svc", namespace)
    except kubernetes.client.rest.ApiException as e:
        logger.info(f"Failed to delete {name}-podinfo deployment, service: {e}")
    else:
        logger.info(f"Deleted {name}-podinfo deployment, service.")

    if body['spec'].get('redis', {}).get('enabled', False):
        try:
            api.delete_namespaced_deployment(f"{name}-redis", namespace)
            service_api.delete_namespaced_service(f"{name}-redis-svc", namespace)
        except kubernetes.client.rest.ApiException as e:
            logger.info(f"Failed to delete {name}-redis deployment, service: {e}")
        else:
            logger.info(f"Deleted {name}-redis deployment, service.")


@kopf.on.update('my.api.group', 'v1alpha1', 'myappresources')
def update_fn(spec, name, namespace, old, status, **kwargs):
    if old['spec'] != spec:
        # Get the current deployment
        current_deployment = api.read_namespaced_deployment(name=f"{name}-podinfo", namespace=namespace)

        env_vars = current_deployment.spec.template.spec.containers[0].env

        # Update the values of env vars if they have changed
        for env_var in env_vars:
            if env_var.name == 'PODINFO_UI_COLOR' and old['spec']['ui']['color'] != spec['ui']['color']:
                env_var.value = spec['ui']['color']
            if env_var.name == 'PODINFO_UI_MESSAGE' and old['spec']['ui']['message'] != spec['ui']['message']:
                env_var.value = spec['ui']['message']
            if env_var.name == 'PODINFO_CACHE_SERVER':
                # Update the Redis enabled status based on spec
                env_var.value = f"tcp://{name}-redis-svc:6379" if spec['redis']['enabled'] else ""

        patch = {
            "spec": {
                "replicas": spec.get('replicaCount'),
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": f"{name}-podinfo",
                                "image": f'{spec["image"]["repository"]}:{spec["image"]["tag"]}',
                                "resources": {
                                    "requests": {
                                        "cpu": spec['resources'].get('cpuRequest'),
                                        "memory": spec['resources'].get('memoryLimit')
                                    }
                                },
                                "env": env_vars
                            }
                        ]
                    }
                }
            }
        }

        # deploy patch
        try:
            api.patch_namespaced_deployment(name=f"{name}-podinfo", namespace=namespace, body=patch)
        except Exception as e:
            logger.info(f"Failed to patch deployment: {e}")
        else:
            logger.info(f"Patch deployed")

        # Check if redis should be enabled
        # (create / delete) redis deployment, service based on spec
        if spec['redis']['enabled']:
            try:
                api.read_namespaced_deployment(name=f"{name}-redis", namespace=namespace)
                service_api.read_namespaced_service(name=f"{name}-redis-svc", namespace=namespace)
            except kubernetes.client.rest.ApiException as e:
                if e.status == 404:  # deployment, service does not exist, create them
                    create_redis_deployment(api, name, namespace)
                    create_service(service_api, name, namespace, redis=True)
                else:
                    logger.info(f"Failed to create {name}-redis deployment or service: {e}")
            else:
                logger.info(f"No actions needed.")
        else:
            try:
                api.delete_namespaced_deployment(name=f"{name}-redis", namespace=namespace)
                service_api.delete_namespaced_service(name=f"{name}-redis-svc", namespace=namespace)
                logger.info(f"Deleted {name}-redis deployment, service.")
            except kubernetes.client.rest.ApiException as e:
                if e.status == 404:
                    logger.info(f"No actions needed.")
