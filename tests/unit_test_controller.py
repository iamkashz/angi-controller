import unittest
from unittest.mock import patch, Mock

from kopf_controller import create_redis_deployment, create_podinfo_deployment, create_service
from kubernetes.client.models import V1Deployment, V1Service


class TestController(unittest.TestCase):

    @patch('kopf_controller.api')
    def test_create_redis_deployment(self, mock_api):
        mock_api.create_namespaced_deployment = Mock()
        name = 'test'
        namespace = 'default'

        create_redis_deployment(mock_api, name, namespace)

        args, _ = mock_api.create_namespaced_deployment.call_args
        self.assertEqual(args[0], namespace)
        self.assertIsInstance(args[1], V1Deployment)
        self.assertEqual(args[1].metadata.name, f"{name}-redis")

    @patch('kopf_controller.api')
    def test_create_podinfo_deployment(self, mock_api):
        mock_api.create_namespaced_deployment = Mock()
        name = 'test'
        namespace = 'default'
        spec = {
            'resources': {},
            'ui': {},
            'image': {
                'repository': 'ghcr.io/stefanprodan/podinfo',
                'tag': 'latest'
            },
            'replicaCount': 1
        }
        redis_service_address = ''

        create_podinfo_deployment(mock_api, name, namespace, spec, redis_service_address)

        args, _ = mock_api.create_namespaced_deployment.call_args
        self.assertEqual(args[0], namespace)
        self.assertIsInstance(args[1], V1Deployment)
        self.assertEqual(args[1].metadata.name, f"{name}-podinfo")

    @patch('kopf_controller.service_api')
    def test_create_podinfo_service(self, mock_service_api):
        mock_service_api.create_namespaced_service = Mock()
        name = 'test'
        namespace = 'default'

        create_service(mock_service_api, name, namespace, redis=False)

        args, _ = mock_service_api.create_namespaced_service.call_args
        self.assertEqual(args[0], namespace)
        self.assertIsInstance(args[1], V1Service)
        self.assertEqual(args[1].metadata.name, f"{name}-podinfo-svc")


if __name__ == '__main__':
    unittest.main()
