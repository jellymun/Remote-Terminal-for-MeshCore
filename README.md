# RemoteTerm for MeshCore

> CHANGE (2026-08-28): The project now includes an optional web-based login flow (form + JWT cookie session) to replace site-wide HTTP Basic authentication for browser access. This was added on branch `feature/web-login-form` to avoid browser/EDGE CIS policy blocks on Basic auth. See the `app/auth.py` backend endpoints (`POST /api/login`, `POST /api/logout`, `GET /api/me`) and the frontend login page at `frontend/src/pages/Login.tsx`.

Backend server + browser interface for MeshCore mesh radio networks, providing a rich, web-based power-user management and messaging system through a companion radio.

Connect your radio over Serial, TCP, or BLE, and then you can:

* Send and receive DMs and channel messages
* Cache all received packets, decrypting as you gain keys
* Run multiple Python bots that can analyze messages and respond to DMs and channels
* Monitor unlimited contacts and channels (radio limits don't apply -- packets are decrypted server-side)
* Access your radio remotely over your network or VPN
* Search for hashtag channel names for channels you don't have keys for yet
* Forward packets, messages, and automatic repeater telemetry to MQTT, Home Assistant, LetsMesh, MeshRank, SQS, Apprise, etc.
* Use the more recent 1.14+ firmwares which support multibyte pathing
* Visualize the mesh as a map or node set, view repeater stats, and more!

For advanced setup and troubleshooting see [README_ADVANCED.md](README_ADVANCED.md). If you plan to contribute, read [CONTRIBUTING.md](CONTRIBUTING.md).

**Warning:** This app is for trusted environments only. _Do not put this on an untrusted network, or open it to the public._ You can optionally set `MESHCORE_BASIC_AUTH_USERNAME` and `MESHCORE_BAS[...]

![Screenshot of the application's web interface](app_screenshot.png)

> [!WARNING]
> RemoteTerm does *full* management of the radio, meaning that once a radio is connected to RemoteTerm, all contacts/channels will be imported and offloaded to RemoteTerm and the contacts actually[...]

## Requirements

- Python 3.11+
- Node.js LTS or current (20, 22, 24, 25) if you're not using a prebuilt release
- [UV](https://astral.sh/uv) package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- MeshCore radio connected via USB serial, TCP, or BLE

<details>
<summary>Finding your serial port</summary>

```bash
#######
# Linux
#######
ls /dev/ttyUSB* /dev/ttyACM*

#######
# macOS
#######
ls /dev/cu.usbserial-* /dev/cu.usbmodem*

###########
# Windows
###########
# In PowerShell:
Get-CimInstance Win32_SerialPort | Select-Object DeviceID, Caption

######
# WSL2
######
# Run this in an elevated PowerShell (not WSL) window
winget install usbipd
# restart console
# then find device ID
usbipd list
# make device shareable
usbipd bind --wsl --busid 3-8 # (or whatever the right ID is)
# attach device to WSL (run this each time you plug in the device)
usbipd attach --wsl --busid 3-8
# device will appear in WSL as /dev/ttyUSB0 or /dev/ttyACM0
```
</details>

## Install Path 1: Clone And Build

**This approach is recommended over Docker due to intermittent serial communications issues I've seen on \*nix systems.**

```bash
git clone https://github.com/jkingsman/Remote-Terminal-for-MeshCore.git
cd Remote-Terminal-for-MeshCore

uv sync
cd frontend && npm install && npm run build && cd ..

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Access the app at http://localhost:8000. Once the backend is running, the interactive API docs are available at http://localhost:8000/docs.

Source checkouts expect a normal frontend build in `frontend/dist`.

> [!TIP]
> Running on lightweight hardware, or just don't want to build the frontend locally? From a cloned checkout, run `python3 scripts/setup/fetch_prebuilt_frontend.py` to fetch and unpack a prebuilt f[...]

> [!NOTE]
> On Linux, you can also install RemoteTerm as a persistent `systemd` service that starts on boot and restarts automatically on failure:
>
> ```bash
> bash scripts/setup/install_service.sh
> ```
>
> For the full service workflow and post-install operations, see [README_ADVANCED.md](README_ADVANCED.md).

## Install Path 2: Docker

> **Warning:** Docker has had reports intermittent issues with serial event subscriptions. The native method above is more reliable.

Local Docker builds are architecture-native by default. On Apple Silicon Macs and ARM64 Linux hosts such as Raspberry Pi, `docker compose build` / `docker compose up --build` will produce an ARM6[...]

For serial-device passthrough, use rootful Docker. In practice that usually means starting the stack with `sudo docker compose ...` unless your Docker daemon is already configured for rootful acc[...]

Create a local `docker-compose.yml` in one of two ways:

1. Copy the example file and edit it by hand:

```bash
cp docker-compose.example.yml docker-compose.yml
```

2. Or generate one interactively:

```bash
bash scripts/setup/install_docker.sh
```

> The interactive generator enables a self-signed (snakeoil) TLS certificate by default. If you accept the default, the app will be served over HTTPS and the generated compose file will include c[...]

Your local `docker-compose.yml` is gitignored so future pulls don't overwrite your Docker settings.

The guided Docker flow can collect BLE settings, but BLE access from Docker still needs manual compose customization such as Bluetooth passthrough and possibly privileged mode or host networking.[...]

Then customize the local compose file for your transport and launch:

```bash
sudo docker compose up # add -d for background once you validate it's working
```

The database is stored in `./data/` (bind-mounted), so the container shares the same database as the native app.

To rebuild after pulling updates:

```bash
sudo docker compose pull
sudo docker compose up -d
```

> If you switched to a local build (`build: .` instead of `image:`), use `sudo docker compose up -d --build` instead — `pull` only fetches remote images.

The example file and setup script default to the published Docker Hub image. To build locally from your checkout instead, replace:

```yaml
image: docker.io/jkingsman/remoteterm-meshcore:latest
```

with:

```yaml
build: .
```

Then run:

```bash
sudo docker compose up -d --build
```

The container runs as root by default for maximum serial passthrough compatibility across host setups. On Linux, if you switch between native and Docker runs, `./data` can end up root-owned. If y[...]

To stop:

```bash
sudo docker compose down
```

## Install Path 3: Arch Linux (AUR)

A [`remoteterm-meshcore`](https://aur.archlinux.org/packages/remoteterm-meshcore) package is available in the AUR. Install it with an AUR helper or build it manually:

```bash
# with an AUR helper
yay -S remoteterm-meshcore

# or manually
git clone https://aur.archlinux.org/remoteterm-meshcore.git
cd remoteterm-meshcore
makepkg -si
```

Configure your radio connection, then start the service:

```bash
sudo vi /etc/remoteterm-meshcore/remoteterm.env
sudo systemctl enable --now remoteterm-meshcore
```

Access the app at http://localhost:8000.

## Standard Environment Variables

Only one transport may be active at a time. If multiple are set, the server will refuse to start.

| Variable | Default | Description |
|----------|---------|-------------|
| `MESHCORE_SERIAL_PORT` | (auto-detect) | Serial port path |
| `MESHCORE_SERIAL_BAUDRATE` | 115200 | Serial baud rate |
| `MESHCORE_TCP_HOST` | | TCP host (mutually exclusive with serial/BLE) |
| `MESHCORE_TCP_PORT` | 5000 | TCP port |
| `MESHCORE_BLE_ADDRESS` | | BLE device address (mutually exclusive with serial/TCP) |
| `MESHCORE_BLE_PIN` | | BLE PIN (required when BLE address is set) |
| `MESHCORE_LOG_LEVEL` | INFO | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MESHCORE_DATABASE_PATH` | `data/meshcore.db` | SQLite database path |
| `MESHCORE_DISABLE_BOTS` | false | Disable bot system entirely (blocks execution and config; an intermediate security precaution, but not as good as basic auth) |
| `MESHCORE_BASIC_AUTH_USERNAME` | | Optional app-wide HTTP Basic auth username; must be set together with `MESHCORE_BASIC_AUTH_PASSWORD` |
| `MESHCORE_BASIC_AUTH_PASSWORD` | | Optional app-wide HTTP Basic auth password; must be set together with `MESHCORE_BASIC_AUTH_USERNAME` |
| `MESHCORE_VAPID_SUBJECT` | `mailto:noreply@meshcore.local` | Subject (`sub`) claim for Web Push VAPID tokens; must be a `mailto:` or `https:` contact. Apple's push service rejects the default `[...]

Common launch patterns:

```bash
# Serial (explicit port)
MESHCORE_SERIAL_PORT=/dev/ttyUSB0 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# TCP
MESHCORE_TCP_HOST=192.168.1.100 MESHCORE_TCP_PORT=5000 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# BLE
MESHCORE_BLE_ADDRESS=AA:BB:CC:DD:EE:FF MESHCORE_BLE_PIN=123456 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows (PowerShell), set environment variables as a separate statement:

```powershell
$env:MESHCORE_SERIAL_PORT="COM8" # or your COM port
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> [!WARNING]
> **Windows + MQTT fanout:** Python's default Windows event loop (ProactorEventLoop) is not compatible with the MQTT libraries used by RemoteTerm. If you configure any MQTT integration, add `--lo[...]
>
> ```powershell
> uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop none
> > ```
>
>If you forget, the app will start normally but MQTT connections will fail and you'll see a toast in the UI with this same guidance.

If you enable Basic Auth, protect the app with HTTPS. HTTP Basic credentials are not safe on plain HTTP. Also note that the app's permissive CORS policy is a deliberate trusted-network tradeoff, [...]

## Where To Go Next

- Advanced setup, troubleshooting, HTTPS, systemd, remediation variables, and debug logging: [README_ADVANCED.md](README_ADVANCED.md)
- Home Assistant-specific guidance and entity/sensor naming schemes: [README_HA.md](README_HA.md)
- Contributing, tests, linting, E2E notes, and important AGENTS files: [CONTRIBUTING.md](CONTRIBUTING.md)
- Live API docs after the backend is running: http://localhost:8000/docs

## Acknowledgements

- Thanks to the original project and its contributors (original repository: https://github.com/jkingsman/Remote-Terminal-for-MeshCore). This branch includes modifications to add a web-based login flow for environments where HTTP Basic is restricted.

## Disclaimer

This is developed with very heavy agentic assistance -- there is no warranty of fitness for any purpose. It's been lovingly guided by an engineer with a passion for clean code and good tests, but[...]

If extending, have your LLM read the three `AGENTS.md` files: `./AGENTS.md`, `./frontend/AGENTS.md`, and `./app/AGENTS.md`.
