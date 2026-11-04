import unittest

from httpx import ASGITransport, AsyncClient

from backend.main import app


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_calculation(self):
        response = await self.client.post("/api/calculate", json={"expression": " (12 + 3) × 2 "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"expression": "(12 + 3) × 2", "result": "30"})

    async def test_division_by_zero_returns_actionable_error(self):
        response = await self.client.post("/api/calculate", json={"expression": "1/0"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("zero", response.json()["detail"])

    async def test_request_validation(self):
        for payload in ({}, {"expression": ""}, {"expression": 123}, {"expression": "1" * 257}, {"expression": "1", "extra": True}):
            with self.subTest(payload=payload):
                response = await self.client.post("/api/calculate", json=payload)
                self.assertEqual(response.status_code, 422)

    async def test_health(self):
        response = await self.client.get("/api/health")
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
