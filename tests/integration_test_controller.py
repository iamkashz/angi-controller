import unittest
from kubernetes import client, config
import time


class TestControllerIntegration(unittest.TestCase):
    def setUp(self):
        config.load_kube_config()
        self.api_instance = client.CustomObjectsApi()
        self.deployment_api = client.AppsV1Api()

        # Check if the MyAppResource CRD is deployed
        try:
            self.api_instance.list_cluster_custom_object(group="my.api.group", version="v1alpha1",
                                                         plural="myappresources")
        except client.exceptions.ApiException as e:
            raise Exception("MyAppResource CRD is not deployed. Please deploy the CRD first.")

    def create_my_app_resource(self, name, namespace):
        body = {
            "apiVersion": "my.api.group/v1alpha1",
            "kind": "MyAppResource",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {
                "replicaCount": 1,
                "image": {"repository": "ghcr.io/stefanprodan/podinfo", "tag": "latest"},
                "resources": {"cpuRequest": "100m", "memoryLimit": "128Mi"},
                "ui": {"color": "#236bb8", "message": "Original Message"},
                "redis": {"enabled": True}
            }
        }
        return self.api_instance.create_namespaced_custom_object(
            group="my.api.group",
            version="v1alpha1",
            namespace=namespace,
            plural="myappresources",
            body=body,
        )

    def update_my_app_resource(self, name, namespace):
        body = {
            "apiVersion": "my.api.group/v1alpha1",
            "kind": "MyAppResource",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {
                "replicaCount": 3,
                "image": {"repository": "ghcr.io/stefanprodan/podinfo", "tag": "latest"},
                "resources": {"cpuRequest": "100m", "memoryLimit": "64Mi"},
                "ui": {"color": "#9723b8", "message": "Message updated!"},
                "redis": {"enabled": True}
            }
        }
        return self.api_instance.patch_namespaced_custom_object(
            group="my.api.group",
            version="v1alpha1",
            namespace=namespace,
            plural="myappresources",
            name=name,
            body=body,
        )

    def delete_my_app_resource(self, name, namespace):
        return self.api_instance.delete_namespaced_custom_object(
            group="my.api.group",
            version="v1alpha1",
            namespace=namespace,
            plural="myappresources",
            name=name,
        )

    def test_my_app_resource_lifecycle(self):
        namespace = "default"
        name = "test-myappresource"

        # create
        self.create_my_app_resource(name, namespace)
        print(f"\nSent request to k8 to create customApp {name}, waiting 10 seconds before updates")
        time.sleep(10)

        try:
            response = self.deployment_api.read_namespaced_deployment(f"{name}-podinfo", namespace)
            self.assertIsNotNone(response)
            print("Controller is working, deployment found")
        except Exception as e:
            print(f"Error: {e}")

        # update
        self.update_my_app_resource(name, namespace)
        print(f"\nSent request to update customApp {name}, waiting 20 seconds before checks")
        time.sleep(20)

        try:
            response = self.deployment_api.read_namespaced_deployment(f"{name}-podinfo", namespace)
            self.assertEqual(response.spec.replicas, 3)
            print("spec.replicas check successful")

            containers = response.spec.template.spec.containers
            for container in containers:
                if container.name == f"{name}-podinfo":
                    for env_var in container.env:
                        if env_var.name == "PODINFO_UI_COLOR":
                            self.assertEqual(env_var.value, "#9723b8")
                            print("ui.color check successful!")
                        elif env_var.name == "PODINFO_UI_MESSAGE":
                            self.assertEqual(env_var.value, "Message updated!")
                            print("ui.message check successful!")
        except Exception as e:
            print(f"Error: {e}")

        # delete
        self.delete_my_app_resource(name, namespace)
        print(f"\nSent request to delete customApp {name}, waiting 20 seconds before tear down")
        time.sleep(20)

    def tearDown(self):
        # Cleanup the resources after the test
        name = "test-myappresource"
        namespace = "default"

        try:
            self.api_instance.delete_namespaced_custom_object(
                group="my.api.group",
                version="v1alpha1",
                namespace=namespace,
                plural="myappresources",
                name=name,
            )
        except Exception as e:
            if e.status == 404:
                pass
            else:
                print(f"Error: {e}")


if __name__ == '__main__':
    unittest.main()
