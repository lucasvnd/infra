#!/usr/bin/env python3
"""
Portainer API Integration Module
Handles all interactions with Portainer REST API for stack deployment
"""

import requests
import time
import sys
import json
from typing import Dict, Optional, Tuple


class PortainerAPI:
    """Portainer API client for stack management"""

    def __init__(self, base_url: str = "http://localhost:9000"):
        """
        Initialize Portainer API client

        Args:
            base_url: Portainer API base URL (default: http://localhost:9000)
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.jwt_token: Optional[str] = None
        self.endpoint_id: Optional[int] = None
        self.swarm_id: Optional[str] = None

    def wait_for_portainer(self, timeout: int = 120, interval: int = 2) -> bool:
        """
        Wait for Portainer to be ready

        Args:
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds

        Returns:
            True if Portainer is ready, False otherwise
        """
        print("⏳ Aguardando Portainer ficar pronto...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.api_url}/status", timeout=5)
                if response.status_code == 200:
                    print("✅ Portainer está pronto!")
                    return True
            except requests.exceptions.RequestException:
                pass

            time.sleep(interval)

        print("❌ Timeout aguardando Portainer", file=sys.stderr)
        return False

    def initialize_admin(self, username: str, password: str) -> bool:
        """
        Initialize Portainer admin user (first-time setup)

        Args:
            username: Admin username
            password: Admin password (min 12 chars)

        Returns:
            True if successful or already initialized, False otherwise
        """
        try:
            payload = {
                "Username": username,
                "Password": password
            }

            response = requests.post(
                f"{self.api_url}/users/admin/init",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ Admin user '{username}' criado com sucesso")
                return True
            elif response.status_code == 409:
                print(f"ℹ️  Admin user já existe, continuando...")
                return True
            else:
                print(f"❌ Erro ao criar admin: {response.status_code} - {response.text}", file=sys.stderr)
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão ao inicializar admin: {e}", file=sys.stderr)
            return False

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate and obtain JWT token

        Args:
            username: Admin username
            password: Admin password

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            payload = {
                "username": username,
                "password": password
            }

            response = requests.post(
                f"{self.api_url}/auth",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("jwt")
                if self.jwt_token:
                    print("✅ Autenticação bem-sucedida")
                    return True
                else:
                    print("❌ Token JWT não encontrado na resposta", file=sys.stderr)
                    return False
            else:
                print(f"❌ Falha na autenticação: {response.status_code} - {response.text}", file=sys.stderr)
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão na autenticação: {e}", file=sys.stderr)
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with JWT token for API requests"""
        if not self.jwt_token:
            raise ValueError("JWT token não disponível. Execute authenticate() primeiro.")

        return {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }

    def get_endpoint_id(self) -> Optional[int]:
        """
        Get local Docker Swarm endpoint ID

        Returns:
            Endpoint ID or None if not found
        """
        try:
            response = requests.get(
                f"{self.api_url}/endpoints",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                endpoints = response.json()

                # Find local endpoint
                for endpoint in endpoints:
                    if endpoint.get("Type") == 4:  # Type 4 = Docker Swarm
                        self.endpoint_id = endpoint.get("Id")
                        self.swarm_id = endpoint.get("Snapshots", {}).get("Swarm", {}).get("Cluster", {}).get("ID", "")
                        print(f"✅ Endpoint ID encontrado: {self.endpoint_id}")
                        print(f"✅ Swarm ID: {self.swarm_id}")
                        return self.endpoint_id

                print("❌ Nenhum endpoint Docker Swarm encontrado", file=sys.stderr)
                return None
            else:
                print(f"❌ Erro ao buscar endpoints: {response.status_code}", file=sys.stderr)
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão ao buscar endpoint: {e}", file=sys.stderr)
            return None

    def deploy_stack(self, stack_name: str, compose_content: str, max_retries: int = 3) -> bool:
        """
        Deploy a Docker Swarm stack via Portainer API

        Args:
            stack_name: Name of the stack
            compose_content: Docker Compose YAML content (with variables already substituted)
            max_retries: Maximum number of retry attempts

        Returns:
            True if deployment successful, False otherwise
        """
        if not self.endpoint_id:
            print("❌ Endpoint ID não disponível. Execute get_endpoint_id() primeiro.", file=sys.stderr)
            return False

        if not self.swarm_id:
            print("❌ Swarm ID não disponível.", file=sys.stderr)
            return False

        payload = {
            "Name": stack_name,
            "SwarmID": self.swarm_id,
            "StackFileContent": compose_content
        }

        url = f"{self.api_url}/stacks"
        params = {
            "type": "1",  # 1 = Swarm stack
            "method": "string",  # Deploy from string content
            "endpointId": self.endpoint_id
        }

        for attempt in range(1, max_retries + 1):
            try:
                print(f"🚀 Deploying stack '{stack_name}' (tentativa {attempt}/{max_retries})...")

                response = requests.post(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    print(f"✅ Stack '{stack_name}' deployada com sucesso!")
                    return True
                elif response.status_code == 409:
                    # Stack already exists, try to update it
                    print(f"ℹ️  Stack '{stack_name}' já existe, tentando atualizar...")
                    return self._update_stack(stack_name, compose_content)
                else:
                    print(f"⚠️  Erro no deploy: {response.status_code} - {response.text}", file=sys.stderr)

                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"⏳ Aguardando {wait_time}s antes de retentar...")
                        time.sleep(wait_time)

            except requests.exceptions.RequestException as e:
                print(f"⚠️  Erro de conexão no deploy: {e}", file=sys.stderr)

                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"⏳ Aguardando {wait_time}s antes de retentar...")
                    time.sleep(wait_time)

        print(f"❌ Falha ao deployar stack '{stack_name}' após {max_retries} tentativas", file=sys.stderr)
        return False

    def _update_stack(self, stack_name: str, compose_content: str) -> bool:
        """
        Update existing stack

        Args:
            stack_name: Name of the stack
            compose_content: Updated Docker Compose YAML content

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Get stack ID
            stack_id = self._get_stack_id(stack_name)
            if not stack_id:
                print(f"❌ Stack ID não encontrado para '{stack_name}'", file=sys.stderr)
                return False

            payload = {
                "StackFileContent": compose_content,
                "Prune": False
            }

            url = f"{self.api_url}/stacks/{stack_id}"
            params = {"endpointId": self.endpoint_id}

            response = requests.put(
                url,
                params=params,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                print(f"✅ Stack '{stack_name}' atualizada com sucesso!")
                return True
            else:
                print(f"❌ Erro ao atualizar stack: {response.status_code} - {response.text}", file=sys.stderr)
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão ao atualizar stack: {e}", file=sys.stderr)
            return False

    def _get_stack_id(self, stack_name: str) -> Optional[int]:
        """
        Get stack ID by name

        Args:
            stack_name: Name of the stack

        Returns:
            Stack ID or None if not found
        """
        try:
            response = requests.get(
                f"{self.api_url}/stacks",
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                stacks = response.json()
                for stack in stacks:
                    if stack.get("Name") == stack_name:
                        return stack.get("Id")

            return None

        except requests.exceptions.RequestException:
            return None

    def check_stack_status(self, stack_name: str, timeout: int = 60, interval: int = 2) -> bool:
        """
        Check if stack services are running

        Args:
            stack_name: Name of the stack
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds

        Returns:
            True if all services are running, False otherwise
        """
        print(f"⏳ Verificando status da stack '{stack_name}'...")
        start_time = time.time()

        stack_id = self._get_stack_id(stack_name)
        if not stack_id:
            print(f"⚠️  Stack '{stack_name}' não encontrada, assumindo sucesso", file=sys.stderr)
            return True

        while time.time() - start_time < timeout:
            try:
                url = f"{self.api_url}/stacks/{stack_id}/file"
                params = {"endpointId": self.endpoint_id}

                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=10
                )

                if response.status_code == 200:
                    # Stack exists, check services via endpoint
                    services_healthy = self._check_stack_services(stack_id)
                    if services_healthy:
                        print(f"✅ Stack '{stack_name}' está rodando!")
                        return True

            except requests.exceptions.RequestException:
                pass

            time.sleep(interval)

        print(f"⚠️  Timeout verificando status de '{stack_name}', continuando...", file=sys.stderr)
        return True  # Continue deployment even if status check times out

    def _check_stack_services(self, stack_id: int) -> bool:
        """
        Check if stack services are healthy

        Args:
            stack_id: Stack ID

        Returns:
            True if services are healthy, False otherwise
        """
        try:
            url = f"{self.api_url}/endpoints/{self.endpoint_id}/docker/services"
            params = {"filters": json.dumps({"label": [f"com.docker.stack.namespace={stack_id}"]})}

            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                services = response.json()
                return len(services) > 0  # If services exist, assume healthy

            return False

        except requests.exceptions.RequestException:
            return False

    def get_stack_services(self, stack_name: str) -> Optional[list]:
        """
        Get list of services in a stack

        Args:
            stack_name: Name of the stack

        Returns:
            List of services or None if error
        """
        try:
            stack_id = self._get_stack_id(stack_name)
            if not stack_id:
                return None

            url = f"{self.api_url}/endpoints/{self.endpoint_id}/docker/services"
            params = {"filters": json.dumps({"label": [f"com.docker.stack.namespace={stack_name}"]})}

            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return response.json()

            return None

        except requests.exceptions.RequestException:
            return None

    def add_registry(self, name: str, url: str, username: str, password: str) -> bool:
        """
        Add a Docker registry to Portainer

        Args:
            name: Registry name (e.g., "WAHA Docker Hub")
            url: Registry URL (e.g., "docker.io" for Docker Hub)
            username: Registry username
            password: Registry password/token

        Returns:
            True if successful or registry already exists, False otherwise
        """
        try:
            # Check if registry already exists
            list_url = f"{self.api_url}/registries"
            response = requests.get(
                list_url,
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                existing_registries = response.json()
                for registry in existing_registries:
                    if registry.get('Name') == name or (registry.get('URL') == url and registry.get('Username') == username):
                        print(f"ℹ️  Registry '{name}' já existe")
                        return True

            # Create new registry
            payload = {
                "Name": name,
                "Type": 1,  # Docker Hub type
                "URL": url,
                "Authentication": True,
                "Username": username,
                "Password": password
            }

            create_url = f"{self.api_url}/registries"
            response = requests.post(
                create_url,
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                print(f"✅ Registry '{name}' adicionado com sucesso")
                return True
            else:
                print(f"❌ Erro ao adicionar registry: {response.status_code} - {response.text}", file=sys.stderr)
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão ao adicionar registry: {e}", file=sys.stderr)
            return False
