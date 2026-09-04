import unittest

from fastapi.testclient import TestClient

from api.main import app


class HealthApiTest(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        
        # 创建一个测试客户端
        client = TestClient(app)

        # 模拟发送一个HTTP请求
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()

