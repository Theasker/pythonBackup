
# Directorio raíz donde se guardarán todos los backups
BACKUP_DESTINATION = "/mnt/datos1/backup/backupVPS"

ROTATION = {
    "daily": 7,
    "weekly": 4,
    "monthly": 6,
    "yearly": 2
}

EXCLUSIONS = [
    # --- Control de Versiones (Muy recomendado excluir) ---
    ".git",                # Historial de Git (puede pesar gigas)
    ".gitignore",
    ".gitattributes",
    ".hg",                 # Mercurial
    ".svn",                # SVN

    # --- Node.js / Javascript ---
    "node_modules",        # Dependencias (se regeneran con npm install)
    "bower_components",
    "npm-debug.log*",
    "yarn-debug.log*",
    "yarn-error.log*",
    ".npm",                # Cache de npm

    # --- Python ---
    "__pycache__",         # Bytecode compilado
    "*.py[cod]",           # Archivos .pyc, .pyo, .pyd
    "*$py.class",
    "venv",                # Entornos virtuales
    ".venv",
    "env",
    ".pytest_cache",
    ".ipynb_checkpoints",

    # --- PHP ---
    "vendor",              # Dependencias de Composer
    "composer.phar",
    ".phpunit.result.cache",
    "storage/framework/cache",
    "storage/framework/sessions",

    # --- Archivos Temporales y Logs ---
    "*.log",               # Todos los archivos de log
    "tmp/",
    "temp/",
    "cache/",
    ".cache",

    # --- Editores y Sistema ---
    ".DS_Store",           # macOS
    "Thumbs.db",           # Windows
    ".vscode",             # Configuración VS Code
    ".idea",               # Configuración PyCharm/IntelliJ
    "*.swp",               # Archivos temporales de Vim/editores
    ".devcontainer/",

    # --- Directorios excluidos ---
    "minecraftServer/data*",
    "localstack/aws",
    "openclaw/*",
    "webtop/data/.mozilla",
    "webtop/data/.dbus",
    "webtop/data/.XDG",
]

SERVERS = [
    # {
    #     "name": "vps_instancia",
    #     "ip": "144.24.194.24",
    #     "port": 22,
    #     "user": "root",
    #     "directories": [
    #         "/root/.ssh",
    #         "/etc",
    #         "/home/ubuntu/.ssh",
    #         "/home/ubuntu/docker",
    #         "/home/ubuntu/.config",
    #         "/home/ubuntu/src",
    #         "/home/ubuntu/duckdns",
    #         "/home/ubuntu/.bashrc",
    #         "/home/ubuntu/.profile",
    #     ],
    #     "extra_exclusions": []
    # },
    # {
    #     "name": "vps_laflordeargon",
    #     "ip": "129.151.232.173",
    #     "port": 22,
    #     "user": "root",
    #     "directories": [
    #         "/root/.ssh",
    #         "/etc",
    #         "/home/ubuntu/.ssh",
    #         "/home/ubuntu/docker",
    #         "/home/ubuntu/.config",
    #         "/home/ubuntu/.bashrc",
    #         "/home/ubuntu/.profile",
    #     ],
    #     "extra_exclusions": []
    # },
    # {
    #     "name": "vps_podereuropeo",
    #     "ip": "129.151.225.48",
    #     "port": 22,
    #     "user": "root",
    #     "directories": [
    #         "/root/.ssh",
    #         "/etc",
    #         "/home/ubuntu/.ssh",
    #         "/home/ubuntu/docker",
    #         "/home/ubuntu/src",
    #         "/home/ubuntu/duckdns",
    #         "/home/ubuntu/.bashrc",
    #         "/home/ubuntu/.profile",
    #         "/home/ubuntu/.config",
    #         "/home/ubuntu/docker/openclaw/docker-compose.yml"
    #     ],
    #     "extra_exclusions": ["minecraftServer/data*"]
    # },
    {
        "name": "192.168.1.69",
        "ip": "192.168.1.69",
        "port": 22,
        "user": "root",
        "directories": [
            # "/root/.ssh", 
            # "/home/theasker/.ssh",
            # "/etc",
            # "/mnt/datos1/scripts/bash",
            # "/mnt/datos1/scripts/conky",
            # # "/mnt/datos1/scripts/docker/PRO/Immich",
            "/mnt/datos1/scripts/docker/PRO/honeygain.sh",
            "/mnt/datos1/scripts/telegram",
            "/home/theasker/.bash_profile",
            "/home/theasker/.bashrc",
            "/home/theasker/.zshrc",
			"/home/theasker/.config/xfce4",
            "/home/theasker/.config/Thunar",
            "/home/theasker/.config/conky",
            "/home/theasker/.config/rclone",
            "/home/theasker/.config/zellij",
            "/home/theasker/.config/user-dirs.dirs",
            "/home/theasker/.config/kitty",
		],
        "extra_exclusions": []
    }
]
