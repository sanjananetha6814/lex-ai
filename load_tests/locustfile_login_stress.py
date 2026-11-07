import os
from locust import HttpUser, task, between

class LoginStressUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def login(self):
        self.client.post("/api/auth/login", json={
            "email": "alex.morgan@workspace.lexai",
            "password": "DemoUserPass123!"
        }, name="POST /api/auth/login")

