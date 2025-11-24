import os
import re
import subprocess
import sys
import glob
import time
import shutil
import secrets
import string
import hashlib
from portainer_api import PortainerAPI

# Configuration
VPS_SETUP_FILE = "VPS_setup.md"
STACKS_DIR = "Stacks"
JOIN_TOKEN_FILE = "swarm_join_token.txt"
PORTAINER_CREDENTIALS_FILE = "/root/portainer_credentials.txt"

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {msg} {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_step(msg):
    print(f"\n{Colors.CYAN}➜ {msg}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.GREEN}✔ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✘ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.ENDC}")

# =============================================================================
# DISTRIBUTION DETECTION AND COMMAND MAPPINGS
# =============================================================================

def detect_distro():
    """Detects Linux distribution using /etc/os-release."""
    distro_info = {}

    if os.path.exists('/etc/os-release'):
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    distro_info[key.lower()] = value.strip('"')

    distro_id = distro_info.get('id', '').lower()
    id_like = distro_info.get('id_like', '').lower()

    # Normalize to family
    if distro_id in ['debian']:
        return 'debian'
    elif distro_id in ['ubuntu', 'linuxmint', 'pop']:
        return 'ubuntu'
    elif distro_id in ['centos', 'rhel', 'rocky', 'almalinux', 'oracle']:
        return 'rhel'
    elif distro_id == 'fedora':
        return 'fedora'
    elif distro_id == 'alpine':
        return 'alpine'
    elif distro_id in ['arch', 'manjaro', 'endeavouros']:
        return 'arch'
    elif 'debian' in id_like or 'ubuntu' in id_like:
        return 'debian'
    elif 'rhel' in id_like or 'fedora' in id_like or 'centos' in id_like:
        return 'rhel'

    return 'unknown'

def get_init_system():
    """Detects init system (systemd or openrc)."""
    if os.path.exists('/run/systemd/system'):
        return 'systemd'
    elif os.path.exists('/sbin/openrc'):
        return 'openrc'
    return 'systemd'

# Command mappings for each distribution
DISTRO_COMMANDS = {
    'debian': {
        'update': 'apt update && apt full-upgrade -y',
        'install_base': 'apt install -y sudo gnupg2 wget ca-certificates apt-transport-https curl gnupg nano htop',
        'docker_repo_setup': [
            'install -m 0755 -d /etc/apt/keyrings',
            'curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
            'chmod a+r /etc/apt/keyrings/docker.gpg',
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null',
            'apt-get update',
        ],
        'install_docker': 'apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'enable_docker': 'systemctl enable docker.service && systemctl enable containerd.service',
    },
    'ubuntu': {
        'update': 'apt update && apt full-upgrade -y',
        'install_base': 'apt install -y sudo gnupg2 wget ca-certificates apt-transport-https curl gnupg nano htop',
        'docker_repo_setup': [
            'install -m 0755 -d /etc/apt/keyrings',
            'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
            'chmod a+r /etc/apt/keyrings/docker.gpg',
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null',
            'apt-get update',
        ],
        'install_docker': 'apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'enable_docker': 'systemctl enable docker.service && systemctl enable containerd.service',
    },
    'rhel': {
        'update': 'dnf update -y',
        'install_base': 'dnf install -y sudo gnupg2 wget ca-certificates curl nano htop dnf-plugins-core',
        'docker_repo_setup': [
            'dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo',
        ],
        'install_docker': 'dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'enable_docker': 'systemctl enable docker.service && systemctl enable containerd.service',
    },
    'fedora': {
        'update': 'dnf update -y',
        'install_base': 'dnf install -y sudo gnupg2 wget ca-certificates curl nano htop dnf-plugins-core',
        'docker_repo_setup': [
            'dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo',
        ],
        'install_docker': 'dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'enable_docker': 'systemctl enable docker.service && systemctl enable containerd.service',
    },
    'alpine': {
        'update': 'apk update && apk upgrade',
        'install_base': 'apk add sudo gnupg wget ca-certificates curl nano htop bash',
        'docker_repo_setup': [],  # Docker is in community repos
        'install_docker': 'apk add docker docker-cli-compose',
        'enable_docker': 'rc-update add docker boot',
    },
    'arch': {
        'update': 'pacman -Syu --noconfirm',
        'install_base': 'pacman -S --noconfirm sudo gnupg wget ca-certificates curl nano htop',
        'docker_repo_setup': [],  # Docker is in official repos
        'install_docker': 'pacman -S --noconfirm docker docker-compose docker-buildx',
        'enable_docker': 'systemctl enable docker.service && systemctl enable containerd.service',
    },
}

def generate_vps_setup_commands(distro):
    """Generates VPS setup commands based on detected distribution."""
    if distro not in DISTRO_COMMANDS:
        print_error(f"Unsupported distribution: {distro}")
        return []

    cmds = DISTRO_COMMANDS[distro]
    commands = []

    # 1. System update
    commands.append(('System Update', cmds['update']))

    # 2. Install base packages
    commands.append(('Install Base Packages', cmds['install_base']))

    # 3. Docker repository setup
    for i, cmd in enumerate(cmds['docker_repo_setup'], 1):
        commands.append((f'Docker Repo Setup ({i}/{len(cmds["docker_repo_setup"])})', cmd))

    # 4. Install Docker
    commands.append(('Install Docker', cmds['install_docker']))

    # 5. Enable Docker services
    commands.append(('Enable Docker Services', cmds['enable_docker']))

    # 6. Start Docker
    init_system = get_init_system()
    if init_system == 'systemd':
        commands.append(('Start Docker', 'systemctl start docker'))
    else:
        commands.append(('Start Docker', 'rc-service docker start'))

    # 7. Docker Swarm Init (placeholder - will be handled specially)
    commands.append(('Docker Swarm Init', 'docker swarm init --advertise-addr=#'))

    # 8. Create network
    commands.append(('Create Docker Network', 'docker network create --driver=overlay --attachable network_swarm_public'))

    return commands

def execute_distro_vps_setup():
    """Executes VPS setup using distro-specific commands."""
    print_header("Phase 1: VPS Setup")

    # Detect distribution
    distro = detect_distro()
    if distro == 'unknown':
        print_error("Could not detect Linux distribution!")
        print_info("Supported: Debian, Ubuntu, CentOS/RHEL, Fedora, Alpine, Arch")
        if input("Try to continue with Debian commands? (y/n): ").lower() != 'y':
            return False
        distro = 'debian'

    print_success(f"Detected distribution: {distro.upper()}")

    # Generate commands for this distro
    commands = generate_vps_setup_commands(distro)
    if not commands:
        return False

    total = len(commands)
    manager_ip = None

    for i, (description, cmd) in enumerate(commands, 1):
        print_step(f"Step {i}/{total}: {description}")

        # Handle Swarm Init specially
        if "docker swarm init" in cmd:
            if "--advertise-addr=#" in cmd:
                print_info("Configuring Docker Swarm Advertise Address...")
                manager_ip = get_server_ip()
                if not manager_ip:
                    manager_ip = input(f"{Colors.WARNING}Could not auto-detect IP. Enter Manager IP: {Colors.ENDC}").strip()

                cmd = cmd.replace('#', manager_ip)
                print_info(f"Resolved command: {cmd}")

            if execute_command(cmd, description):
                print_info("Capturing Swarm Join Token...")
                token_res = subprocess.run("docker swarm join-token worker", shell=True, capture_output=True, text=True, executable='/bin/bash')
                if token_res.returncode == 0:
                    with open(JOIN_TOKEN_FILE, 'w') as f:
                        f.write(token_res.stdout)
                    print_success(f"Token saved to {JOIN_TOKEN_FILE}")
                else:
                    print_error("Failed to capture join token")
            else:
                print_info("Swarm might already be initialized. Continuing...")
            continue

        # Normal command
        if not execute_command(cmd, description):
            if input(f"{Colors.WARNING}Command failed. Continue? (y/n): {Colors.ENDC}").lower() != 'y':
                return False

    return True

def get_server_ip():
    """Auto-detects the primary IP address of the server."""
    try:
        result = subprocess.run(
            ["ip", "route", "get", "8.8.8.8"],
            capture_output=True, text=True
        )
        match = re.search(r"src ([\d\.]+)", result.stdout)
        if match:
            return match.group(1)
        else:
            raise Exception("Could not parse IP")
    except Exception:
        return None

def parse_vps_setup():
    """Parses the VPS_setup.md file to extract commands."""
    commands = []
    if not os.path.exists(VPS_SETUP_FILE):
        return []

    with open(VPS_SETUP_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            # Match lines like "1 - sudo apt update"
            match = re.match(r'^\d+\s-\s(.*)', line.strip())
            if match:
                commands.append(match.group(1))
    return commands

def execute_command(cmd, description=None):
    """Executes a shell command with nice output."""
    if description:
        print_info(f"Running: {description}")
    else:
        print_info(f"Executing: {cmd}")
    
    try:
        # We use Popen to stream output if needed, but for now run() is fine
        # For better UX, we could suppress output unless error, but user asked for verbosity
        subprocess.run(cmd, shell=True, executable='/bin/bash', check=True)
        print_success("Command completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e}")
        return False

def execute_vps_setup(commands):
    """Executes setup commands."""
    print_header("Phase 1: VPS Setup")
    
    total = len(commands)
    manager_ip = None

    for i, cmd in enumerate(commands, 1):
        print_step(f"Step {i}/{total}")
        
        # Handle Swarm Init
        if "docker swarm init" in cmd:
            if "--advertise-addr=#" in cmd:
                print_info("Configuring Docker Swarm Advertise Address...")
                manager_ip = get_server_ip()
                if not manager_ip:
                    manager_ip = input(f"{Colors.WARNING}Could not auto-detect IP. Enter Manager IP: {Colors.ENDC}").strip()
                
                base_cmd = cmd.split('#')[0]
                cmd = f"{base_cmd}{manager_ip}"
                print_info(f"Resolved command: {cmd}")
            
            if execute_command(cmd, "Initializing Docker Swarm"):
                print_info("Capturing Swarm Join Token...")
                token_res = subprocess.run("docker swarm join-token worker", shell=True, capture_output=True, text=True, executable='/bin/bash')
                if token_res.returncode == 0:
                    with open(JOIN_TOKEN_FILE, 'w') as f:
                        f.write(token_res.stdout)
                    print_success(f"Token saved to {JOIN_TOKEN_FILE}")
                else:
                    print_error("Failed to capture join token")
            else:
                print_info("Swarm might already be initialized. Continuing...")
            continue

        # Normal command
        if not execute_command(cmd):
            if input(f"{Colors.WARNING}Command failed. Continue? (y/n): {Colors.ENDC}").lower() != 'y':
                sys.exit(1)

import json

# ... (existing imports)

def configure_chatwoot():
    """Waits for Chatwoot container to be stable and runs db:chatwoot_prepare."""
    print_header("Phase 4.5: Configuring Chatwoot Database")

    service_name = "11_chatwoot_admin_chatwoot_admin"

    # 1. Wait for container to be running
    print_step("Waiting for Chatwoot container to be ready...")
    container_id = None

    for attempt in range(30):  # Wait up to 2.5 minutes
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={service_name}"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            container_id = result.stdout.strip().split('\n')[0]
            print_success(f"Container found: {container_id[:12]}")
            break
        print_info(f"Waiting for container... (attempt {attempt + 1}/30)")
        time.sleep(5)

    if not container_id:
        print_error("Chatwoot container not found. Run manually: docker exec -it <container_id> bundle exec rails db:chatwoot_prepare")
        return

    # 2. Wait for container to stabilize (not restarting)
    print_step("Waiting for container to stabilize...")
    time.sleep(30)  # Give Rails time to boot

    # 3. Run db:chatwoot_prepare
    print_step("Running database preparation...")
    result = subprocess.run(
        ["docker", "exec", container_id, "bundle", "exec", "rails", "db:chatwoot_prepare"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print_success("Chatwoot database prepared successfully!")
        if result.stdout:
            print(result.stdout)
    else:
        print_error("Failed to prepare Chatwoot database")
        print(result.stderr)
        print_info("You can run manually: docker exec -it <container_id> bundle exec rails db:chatwoot_prepare")

def configure_minio(env_values):
    """Configures Minio bucket and keys using a temporary Docker container."""
    print_header("Phase 2.5: Configuring Minio")
    
    domain = env_values.get('DOMINIO')
    root_user = env_values.get('MINIO_ROOT_USER')
    root_pass = env_values.get('MINIO_ROOT_PASSWORD')
    
    if not all([domain, root_user, root_pass]):
        print_error("Missing Minio credentials. Skipping configuration.")
        return

    minio_url = f"https://s3storage.{domain}"
    alias = "myminio"
    
    # 1. Wait for Minio to be ready
    print_step("Waiting for Minio to start...")
    print_info("Will retry mc commands until MinIO is ready...")

    # Helper to run mc commands
    def run_mc(command):
        docker_cmd = [
            "docker", "run", "--rm", "--network", "network_swarm_public",
            "--entrypoint", "/bin/sh",
            "minio/mc", "-c", command
        ]
        return subprocess.run(docker_cmd, capture_output=True, text=True)

    print_step("Setting Minio Alias...")
    # Docker Swarm service names - use the service name directly
    service_names = ["minio", "7_minio_minio", "tasks.7_minio_minio"]

    connected = False
    connected_service = None
    for service_name in service_names:
        cmd_alias = f"mc alias set {alias} http://{service_name}:9000 {root_user} {root_pass}"
        print_info(f"Trying to connect to {service_name}...")

        for attempt in range(15):
            res = run_mc(cmd_alias)
            if res.returncode == 0:
                print_success(f"Connected to Minio via {service_name}")
                connected = True
                connected_service = service_name
                break
            print_info(f"Waiting for Minio service... (attempt {attempt + 1}/15)")
            time.sleep(5)

        if connected:
            break

    if not connected:
        print_error("Could not connect to Minio. Check logs with: docker service logs 7_minio_minio")
        return

    # 2. Create Bucket
    print_step("Creating 'chatwoot' bucket...")
    # Need to set alias again in each command since each docker run is a new container
    cmd_bucket = f"mc alias set {alias} http://{connected_service}:9000 {root_user} {root_pass} && mc mb {alias}/chatwoot --ignore-existing"
    res = run_mc(cmd_bucket)
    if res.returncode == 0:
        print_success("Bucket 'chatwoot' created")
    else:
        print_error("Failed to create bucket")
        print(res.stderr)

    # 3. Create Service Account
    print_step("Generating Access Keys...")
    # Need to set alias again and then create service account in same command
    # because each docker run is a new container
    cmd_create_key = f"mc alias set {alias} http://{connected_service}:9000 {root_user} {root_pass} && mc admin user svcacct add {alias} {root_user} --json"
    res = run_mc(cmd_create_key)

    if res.returncode == 0:
        try:
            # Output contains alias success message + JSON, extract just the JSON
            output = res.stdout.strip()
            # Find the JSON part (starts with {)
            json_start = output.find('{')
            if json_start != -1:
                json_str = output[json_start:]
                data = json.loads(json_str)
                access_key = data.get('accessKey')
                secret_key = data.get('secretKey')

                if access_key and secret_key:
                    env_values['STORAGE_ACCESS_KEY_ID'] = access_key
                    env_values['STORAGE_SECRET_ACCESS_KEY'] = secret_key
                    print_success("Keys generated and injected into configuration.")
                    print_info(f"Access Key: {access_key}")
                else:
                    print_error("Failed to parse keys from JSON.")
            else:
                print_error("No JSON found in output.")
                print(output)
        except json.JSONDecodeError as e:
            print_error(f"Failed to decode JSON output from mc: {e}")
            print(res.stdout)
    else:
        print_error("Failed to create service account.")
        print(res.stderr)

def generate_portainer_password():
    """Generates a secure password for Portainer admin."""
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(32))
    return password

def initialize_portainer_api(env_values):
    """Initializes Portainer API after Portainer stack deployment."""
    print_header("Phase 2.1: Initializing Portainer API")

    # Generate admin credentials
    admin_username = "admin"
    admin_password = generate_portainer_password()

    print_step("Configuring Portainer API access...")
    print_info(f"Admin username: {admin_username}")

    # Initialize API client
    portainer_api = PortainerAPI(base_url="http://localhost:9000")

    # Wait for Portainer to be ready
    if not portainer_api.wait_for_portainer(timeout=120):
        print_error("Portainer did not become ready in time")
        return None

    # Initialize admin user
    if not portainer_api.initialize_admin(admin_username, admin_password):
        print_error("Failed to initialize Portainer admin")
        return None

    # Authenticate and get JWT token
    if not portainer_api.authenticate(admin_username, admin_password):
        print_error("Failed to authenticate with Portainer")
        return None

    # Get endpoint ID
    endpoint_id = portainer_api.get_endpoint_id()
    if not endpoint_id:
        print_error("Failed to get Portainer endpoint ID")
        return None

    # Save credentials to file
    try:
        with open(PORTAINER_CREDENTIALS_FILE, 'w') as f:
            f.write(f"Username: {admin_username}\n")
            f.write(f"Password: {admin_password}\n")
            f.write(f"Endpoint ID: {endpoint_id}\n")
            if 'WAHA_API_KEY_PLAIN' in env_values:
                f.write(f"\nWAHA API Key: {env_values['WAHA_API_KEY_PLAIN']}\n")
                f.write(f"WAHA Dashboard User: {env_values['WAHA_DASHBOARD_USERNAME']}\n")
                f.write(f"WAHA Dashboard Pass: {env_values['WAHA_DASHBOARD_PASSWORD']}\n")
        print_success(f"Credentials saved to {PORTAINER_CREDENTIALS_FILE}")
    except Exception as e:
        print_error(f"Failed to save credentials: {e}")

    # Store password in env_values for display at the end
    env_values['PORTAINER_ADMIN_USER'] = admin_username
    env_values['PORTAINER_ADMIN_PASSWORD'] = admin_password

    # Add WAHA Docker Hub registry
    if 'WAHA_DOCKER_HUB_KEY' in env_values:
        print_step("Adding WAHA Docker Hub registry...")
        if portainer_api.add_registry(
            name="WAHA Docker Hub",
            url="docker.io",
            username="devlikeapro",
            password=env_values['WAHA_DOCKER_HUB_KEY']
        ):
            print_success("WAHA Docker Hub registry added")
        else:
            print_warning("Failed to add WAHA Docker Hub registry - you may need to add it manually")

    print_success("Portainer API initialized successfully")
    return portainer_api

def get_required_variables():
    """Scans stack files for variables."""
    required_vars = set()
    stack_files = glob.glob(os.path.join(STACKS_DIR, "*.yaml")) + glob.glob(os.path.join(STACKS_DIR, "*.yml"))
    
    for file_path in stack_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'\$\{([A-Z0-9_]+)\}', content)
            required_vars.update(matches)
            
    # Remove keys that we will auto-generate
    if 'STORAGE_ACCESS_KEY_ID' in required_vars:
        required_vars.remove('STORAGE_ACCESS_KEY_ID')
    if 'STORAGE_SECRET_ACCESS_KEY' in required_vars:
        required_vars.remove('STORAGE_SECRET_ACCESS_KEY')

    return sorted(list(required_vars))

def generate_password(length=32):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_secret_key_base():
    """Generates a 128-character hex string for SECRET_KEY_BASE."""
    return secrets.token_hex(64)

def generate_sha512_hash(text):
    """Generates a SHA512 hash of the given text."""
    return hashlib.sha512(text.encode()).hexdigest()

def get_auto_generated_vars():
    """Returns variables that should be auto-generated with their generators."""
    return {
        'POSTGRES_PASSWORD': lambda: generate_password(32),
        'DB_POSTGRESDB_PASSWORD': lambda: None,  # Will use POSTGRES_PASSWORD
        'MINIO_ROOT_USER': lambda: generate_password(16),
        'MINIO_ROOT_PASSWORD': lambda: generate_password(32),
        'RABBITMQ_DEFAULT_PASS': lambda: generate_password(32),
        'RABBITMQ_ERLANG_COOKIE': lambda: generate_password(48),
        'N8N_ENCRYPTION_KEY': lambda: generate_password(32),
        'SECRET_KEY_BASE': lambda: generate_secret_key_base(),
        'WAHA_API_KEY_PLAIN': lambda: generate_password(32),
        'WAHA_API_KEY_PLAIN_SHA512': lambda: None,  # Will be generated from WAHA_API_KEY_PLAIN
        'WAHA_DASHBOARD_USERNAME': lambda: generate_password(16),
        'WAHA_DASHBOARD_PASSWORD': lambda: generate_password(32),
    }

def collect_variables(required_vars):
    """Collects values for required variables, auto-generating passwords."""
    print_header("Phase 2: Configuration")

    env_values = {}
    auto_gen = get_auto_generated_vars()

    # Variables that user must provide
    user_required = [
        'DOMINIO',
        'ACME_EMAIL',
        'SMTP_HOST',
        'SMTP_PORT',
        'SMTP_USER',
        'SMTP_PASS',
        'SMTP_SENDER',
        'RABBITMQ_DEFAULT_USER',
        'WAHA_DOCKER_HUB_KEY',
    ]

    # Variables with defaults that don't need user input
    auto_defaults = {
        'POSTGRES_IMAGE': 'pgvector/pgvector:pg16',
    }

    # Apply auto defaults first
    for var, default_val in auto_defaults.items():
        if var in required_vars:
            env_values[var] = default_val
            print_info(f"Using default {var}: {default_val}")

    # Collect user-provided values
    for var in required_vars:
        if var in user_required:
            default = ""
            if var == 'SMTP_PORT':
                default = "587"
            elif var == 'RABBITMQ_DEFAULT_USER':
                default = "admin"

            if default:
                value = input(f"{Colors.CYAN}{var}{Colors.ENDC} [{default}]: ").strip()
                env_values[var] = value if value else default
            else:
                while True:
                    value = input(f"{Colors.CYAN}{var}{Colors.ENDC}: ").strip()
                    if value:
                        env_values[var] = value
                        break
                    print_error(f"{var} is required!")

    # Auto-generate passwords
    print_step("Generating secure passwords...")
    for var in required_vars:
        if var in auto_gen and var not in env_values:
            generator = auto_gen[var]
            value = generator()
            if value:
                env_values[var] = value
                print_info(f"Generated {var}")

    # Sync related passwords
    if 'POSTGRES_PASSWORD' in env_values:
        env_values['DB_POSTGRESDB_PASSWORD'] = env_values['POSTGRES_PASSWORD']
        print_info("Synced DB_POSTGRESDB_PASSWORD with POSTGRES_PASSWORD")

    # Generate SHA512 hash for WAHA API key
    if 'WAHA_API_KEY_PLAIN' in env_values:
        env_values['WAHA_API_KEY_PLAIN_SHA512'] = generate_sha512_hash(env_values['WAHA_API_KEY_PLAIN'])
        print_info("Generated WAHA_API_KEY_PLAIN_SHA512 from WAHA_API_KEY_PLAIN")

    # Sync SMTP credentials for Chatwoot compatibility
    if 'SMTP_HOST' in env_values:
        env_values['SMTP_ADDRESS'] = env_values['SMTP_HOST']
        env_values['SMTP_DOMAIN'] = env_values['SMTP_HOST']
    if 'SMTP_USER' in env_values:
        env_values['SMTP_USERNAME'] = env_values['SMTP_USER']
        env_values['MAILER_SENDER_EMAIL'] = env_values['SMTP_SENDER'] if 'SMTP_SENDER' in env_values else env_values['SMTP_USER']
    if 'SMTP_PASS' in env_values:
        env_values['SMTP_PASSWORD'] = env_values['SMTP_PASS']

    print_success(f"Collected {len(env_values)} configuration values")
    return env_values

def create_docker_volumes():
    """Creates all required Docker volumes."""
    print_step("Creating Docker volumes...")

    volumes = [
        'traefik_certificates',
        'portainer_data',
        'redis_data',
        'redis_cw_data',
        'redis_n8n_data',
        'redis_waha_data',
        'postgres_data',
        'postgres_init',
        'rabbitmq_data',
        'minio_data',
        'n8n_data',
        'chatwoot_storage',
        'chatwoot_public',
        'chatwoot_mailer',
        'chatwoot_mailers',
    ]

    for vol in volumes:
        try:
            subprocess.run(['docker', 'volume', 'create', vol],
                         capture_output=True, check=True)
            print_info(f"Created volume: {vol}")
        except subprocess.CalledProcessError:
            print_info(f"Volume {vol} already exists")

    print_success("All volumes ready")

def setup_postgres_init_script():
    """Creates the PostgreSQL initialization script to create databases."""
    print_step("Setting up PostgreSQL init script...")

    init_script = """#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE n8n;
    CREATE DATABASE cwdb;
    CREATE DATABASE wahadb;
    GRANT ALL PRIVILEGES ON DATABASE n8n TO postgres;
    GRANT ALL PRIVILEGES ON DATABASE cwdb TO postgres;
    GRANT ALL PRIVILEGES ON DATABASE wahadb TO postgres;
EOSQL
"""

    # Create init script using docker to write to volume
    try:
        # Use cat with heredoc to properly handle the multi-line script
        cmd = [
            'docker', 'run', '--rm',
            '-v', 'postgres_init:/init',
            'alpine', 'sh', '-c',
            f'''cat > /init/init-databases.sh << 'ENDOFSCRIPT'
{init_script}
ENDOFSCRIPT
chmod +x /init/init-databases.sh'''
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print_success("PostgreSQL init script created")
        else:
            print_error(f"Failed to create init script: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to setup PostgreSQL init script: {e}")

def create_docker_network():
    """Creates the Docker network."""
    print_step("Creating Docker network...")
    try:
        subprocess.run([
            'docker', 'network', 'create',
            '--driver', 'overlay',
            '--attachable',
            'network_swarm_public'
        ], capture_output=True, check=True)
        print_success("Created network: network_swarm_public")
    except subprocess.CalledProcessError:
        print_info("Network network_swarm_public already exists")

def validate_configuration(env_values, required_vars):
    """Validates that all required variables have been collected."""
    print_step("Validating configuration...")

    missing = []
    for var in required_vars:
        if var not in env_values or not env_values[var]:
            missing.append(var)

    if missing:
        print_error(f"Missing required variables: {missing}")
        return False

    # Validate critical values
    if 'DOMINIO' in env_values:
        domain = env_values['DOMINIO']
        if not domain or domain == 'your-domain.com':
            print_error("DOMINIO must be set to a valid domain")
            return False

    print_success("Configuration validated successfully")
    return True

def deploy_stacks(env_values):
    """Deploys stacks using Docker CLI for bootstrap (stacks 1-2) and Portainer API for the rest."""
    print_header("Phase 4: Stack Deployment")

    files = glob.glob(os.path.join(STACKS_DIR, "*.yaml")) + glob.glob(os.path.join(STACKS_DIR, "*.yml"))

    def sort_key(f):
        basename = os.path.basename(f)
        match = re.match(r'^(\d+)_', basename)
        return int(match.group(1)) if match else 999

    files.sort(key=sort_key)

    if not files:
        print_error(f"No stack files found in {STACKS_DIR}")
        return

    # Initialize Portainer API client (will be set after stack 2)
    portainer_api = None

    total = len(files)
    for i, file_path in enumerate(files, 1):
        filename = os.path.basename(file_path)
        stack_name = os.path.splitext(filename)[0]

        # Extract stack number
        stack_number_match = re.match(r'^(\d+)_', filename)
        stack_number = int(stack_number_match.group(1)) if stack_number_match else 999

        print_step(f"Deploying Stack {i}/{total}: {stack_name}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace variables
        for var, val in env_values.items():
            content = content.replace(f"${{{var}}}", val)

        # Check for missing
        remaining = re.findall(r'\$\{([A-Z0-9_]+)\}', content)
        if remaining:
            print_error(f"Unresolved variables in {filename}: {remaining}")
            if input("Continue? (y/n): ").lower() != 'y':
                continue

        # Deploy using Docker CLI for stacks 1-2 (bootstrap), API for the rest
        deployment_success = False

        if stack_number <= 2:
            # Use Docker CLI for Traefik and Portainer (bootstrap)
            print_info("Using Docker CLI for bootstrap deployment")
            cmd = ["docker", "stack", "deploy", "-c", "-", stack_name]
            try:
                subprocess.run(cmd, input=content, text=True, check=True)
                print_success(f"{stack_name} deployed successfully")
                deployment_success = True
                time.sleep(5)  # Wait for services to start

                # After Portainer is deployed, initialize API
                if stack_number == 2 and "portainer" in filename:
                    portainer_api = initialize_portainer_api(env_values)
                    if not portainer_api:
                        print_error("Failed to initialize Portainer API. Falling back to Docker CLI for remaining stacks.")

            except subprocess.CalledProcessError:
                print_error(f"Failed to deploy {stack_name}")
                if input("Abort? (y/n): ").lower() == 'y':
                    sys.exit(1)
        else:
            # Use Portainer API for stacks 3+
            if portainer_api:
                print_info("Using Portainer API for deployment")
                deployment_success = portainer_api.deploy_stack(stack_name, content, max_retries=3)

                if deployment_success:
                    # Check stack status
                    portainer_api.check_stack_status(stack_name, timeout=60)
                else:
                    print_error(f"Failed to deploy {stack_name} via Portainer API")
                    print_info("Falling back to Docker CLI...")
                    cmd = ["docker", "stack", "deploy", "-c", "-", stack_name]
                    try:
                        subprocess.run(cmd, input=content, text=True, check=True)
                        print_success(f"{stack_name} deployed successfully via Docker CLI fallback")
                        deployment_success = True
                        time.sleep(5)
                    except subprocess.CalledProcessError:
                        print_error(f"Failed to deploy {stack_name} even with Docker CLI fallback")
                        if input("Abort? (y/n): ").lower() == 'y':
                            sys.exit(1)
            else:
                # Portainer API not available, use Docker CLI
                print_info("Portainer API not available, using Docker CLI")
                cmd = ["docker", "stack", "deploy", "-c", "-", stack_name]
                try:
                    subprocess.run(cmd, input=content, text=True, check=True)
                    print_success(f"{stack_name} deployed successfully")
                    deployment_success = True
                    time.sleep(5)
                except subprocess.CalledProcessError:
                    print_error(f"Failed to deploy {stack_name}")
                    if input("Abort? (y/n): ").lower() == 'y':
                        sys.exit(1)

        # POST-DEPLOY HOOKS (only if deployment was successful)
        if deployment_success:
            # POST-DEPLOY HOOK: Minio
            if "minio" in filename and "7" in filename:
                configure_minio(env_values)

            # POST-DEPLOY HOOK: Chatwoot
            if "chatwoot_admin" in filename and "11" in filename:
                configure_chatwoot()

def main():
# ... (rest of main)
    # Clear screen for fresh start
    print("\033[H\033[J", end="")
    
    print(f"{Colors.CYAN}")
    print("  _____       __                 ___           __        ____")
    print(" /_  _/____  / /_  ____ _       / _ \___  ____/ /__     / __/")
    print("  / / / __ \/ __/ / __ `/______/ // / _ \/ __  / _ \   / /_  ")
    print(" / / / / / / /_  / /_/ //_____/ // /  __/ /_/ /  __/  / __/  ")
    print("/_/ /_/ /_/\__/  \__,_/      /____/\___/\__,_/\___/  /_/     ")
    print(f"{Colors.ENDC}")
    print("Automated Infrastructure Installer")
    print("==========================================================\n")

    if os.name == 'nt':
        print_error("This script is designed for Linux (Debian/Ubuntu).")
        if input("Continue anyway (debug mode)? (y/n): ").lower() != 'y':
            sys.exit(0)

    # Check requirements
    if not os.path.exists(STACKS_DIR):
        print_error(f"Directory '{STACKS_DIR}' not found!")
        print("Please ensure you have uploaded the entire 'infra_install' folder.")
        sys.exit(1)

    # 1. VPS Setup (Multi-Distro Support)
    if input("Run VPS Setup? (y/n): ").lower() == 'y':
        execute_distro_vps_setup()
    
    # 2. Variables
    req_vars = get_required_variables()
    env_values = {}
    if req_vars:
        env_values = collect_variables(req_vars)

    # 3. Validate configuration
    if not validate_configuration(env_values, req_vars):
        print_error("Configuration validation failed. Please fix the issues and try again.")
        sys.exit(1)

    # 4. Create Docker resources
    create_docker_network()
    create_docker_volumes()
    setup_postgres_init_script()

    # 5. Deploy
    deploy_stacks(env_values)
    
    print_header("Installation Complete")
    print_success("All stacks have been processed.")
    
    # Summary
    domain = env_values.get('DOMINIO', 'your-domain.com')
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== Service URLs ==={Colors.ENDC}")
    print(f"{Colors.CYAN}Portainer:{Colors.ENDC}      https://manager.{domain}")
    print(f"{Colors.CYAN}Chatwoot:{Colors.ENDC}       https://crm.{domain}")
    print(f"{Colors.CYAN}n8n Editor:{Colors.ENDC}     https://automacao.{domain}")
    print(f"{Colors.CYAN}n8n Webhook:{Colors.ENDC}    https://eventos.{domain}")
    print(f"{Colors.CYAN}Minio Console:{Colors.ENDC}  https://s3console.{domain}")
    print(f"{Colors.CYAN}Minio API:{Colors.ENDC}      https://s3storage.{domain}")
    print(f"{Colors.CYAN}WAHA API:{Colors.ENDC}       https://wapi.{domain}")

    # Show credentials
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== Credentials ==={Colors.ENDC}")
    if 'PORTAINER_ADMIN_USER' in env_values:
        print(f"{Colors.CYAN}Portainer User:{Colors.ENDC} {env_values['PORTAINER_ADMIN_USER']}")
        print(f"{Colors.CYAN}Portainer Pass:{Colors.ENDC} {env_values['PORTAINER_ADMIN_PASSWORD']}")
    if 'MINIO_ROOT_USER' in env_values:
        print(f"{Colors.CYAN}Minio User:{Colors.ENDC}     {env_values['MINIO_ROOT_USER']}")
        print(f"{Colors.CYAN}Minio Password:{Colors.ENDC} {env_values['MINIO_ROOT_PASSWORD']}")
    if 'POSTGRES_PASSWORD' in env_values:
        print(f"{Colors.CYAN}PostgreSQL User:{Colors.ENDC} postgres")
        print(f"{Colors.CYAN}PostgreSQL Pass:{Colors.ENDC} {env_values['POSTGRES_PASSWORD']}")
    if 'RABBITMQ_DEFAULT_USER' in env_values:
        print(f"{Colors.CYAN}RabbitMQ User:{Colors.ENDC}  {env_values['RABBITMQ_DEFAULT_USER']}")
        print(f"{Colors.CYAN}RabbitMQ Pass:{Colors.ENDC}  {env_values['RABBITMQ_DEFAULT_PASS']}")
    if 'WAHA_API_KEY_PLAIN' in env_values:
        print(f"{Colors.CYAN}WAHA API Key:{Colors.ENDC}   {env_values['WAHA_API_KEY_PLAIN']}")
        print(f"{Colors.CYAN}WAHA Dashboard User:{Colors.ENDC} {env_values['WAHA_DASHBOARD_USERNAME']}")
        print(f"{Colors.CYAN}WAHA Dashboard Pass:{Colors.ENDC} {env_values['WAHA_DASHBOARD_PASSWORD']}")

    # Highlight credentials file location
    if os.path.exists(PORTAINER_CREDENTIALS_FILE):
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️  IMPORTANT: Portainer credentials saved to:{Colors.ENDC}")
        print(f"{Colors.GREEN}{Colors.BOLD}    {PORTAINER_CREDENTIALS_FILE}{Colors.ENDC}")
        print(f"{Colors.BLUE}    Run: cat {PORTAINER_CREDENTIALS_FILE}{Colors.ENDC}")

    if os.path.exists(JOIN_TOKEN_FILE):
        print(f"\n{Colors.BOLD}To add worker nodes, run this command on other servers:{Colors.ENDC}")
        with open(JOIN_TOKEN_FILE, 'r') as f:
            print(f"\n    {f.read().strip()}\n")

if __name__ == "__main__":
    main()
