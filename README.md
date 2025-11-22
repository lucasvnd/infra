# Infrastructure Installer

This repository contains the automated installation scripts for your infrastructure stacks.

## 🚀 How to Host

1.  **Create a GitHub Repository**:
    - Create a new repository (e.g., `infra-installer`).
    - Make it **Public** (easiest) or Private (requires Personal Access Token).

2.  **Upload Files**:
    - Upload all files from this folder to the repository:
        - `Stacks/` (folder)
        - `install.py`
        - `setup.sh`
        - `VPS_setup.md`

3.  **Update `setup.sh`**:
    - Edit `setup.sh` and change the `REPO_URL` variable to match your new repository URL.
    - Example: `REPO_URL="https://github.com/myuser/infra-installer.git"`

## 💻 How to Install (For End Users)

Give your users this single command to run on their VPS:

```bash
curl -sL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/setup.sh | sudo bash
```

*(Replace `YOUR_USERNAME/YOUR_REPO` with your actual path)*

### What this does:
1.  Downloads the `setup.sh` script.
2.  Installs `git` and `python3` if missing.
3.  Clones this repository to `/opt/infra_installer`.
4.  Runs `install.py` to guide the user through the setup.
