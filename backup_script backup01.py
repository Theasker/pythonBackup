import os
import subprocess
from datetime import datetime, timedelta
import backup_config

class BackupManager:
    # Carga de la configuración (constructor)
    def __init__(self):
        self.destination_root = backup_config.BACKUP_DESTINATION
        self.rotation = backup_config.ROTATION
        self.servers = backup_config.SERVERS
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.categories = self.get_active_categories()
    
    def setup_directories(self):
        # Crea la estructura de carpetas: categoría / servidor / fecha
        #categories = ["daily", "weekly", "monthly", "yearly"]
        print(f"Creando directorios en {self.destination_root}")
        categories = self.rotation.keys()
        # Creo los directorios de las rotaciones
        for category in categories:
            for server in self.servers:
                path = os.path.join(self.destination_root, category, server["name"])
                os.makedirs(path, exist_ok=True)
    
    def get_latest_backup(self, server_name, category):
        # Busca la carpeta de backup más reciente en la categoría dada 
        #   para usarla como referencia de enlaces duros.

        # 1. Construimos la ruta donde deberían estar los backups de este servidor        
        server_path = os.path.join(self.destination_root, category, server_name)
        
        # 2. Verificamos que existe el path "<path_destino>/<categoria>/<nombre_servidor>"
        if not os.path.exists(server_path):
            return None
        
        # 3. Obtenemos los directorios (que son fechas yyyy-mm-dd) y las ordenamos
        # backups = sorted([d for d in os.listdir(server_path) if os.path.isdir(os.path.join(server_path, d))])
        listElements = os.listdir(server_path)
        dirBackups = []
        for element in listElements:
            fullPath = os.path.join(server_path, element)
            if os.path.isdir(fullPath):
                dirBackups.append(element)
        
        # Como usamos formato YYYY-MM-DD, el orden alfabético coincide con el cronológico.
        dirBackups = sorted(dirBackups)

        # 4. Si no hay directorios, no hay backup previo
        if not dirBackups:
            return None
        
        # 5. Tomamos el último de la lista (el más reciente)
        lastBackup = dirBackups[-1]

        # 6. Devolvemos la ruta completa hacia ese backup anterior
        return os.path.join(server_path, lastBackup)

    def run(self):
        self.setup_directories()
        # Revisamos si hay que realizar algún otro backup (weekly, monthly, yearly)
        active_cats = self.get_active_categories()
        print(f"--- Iniciando proceso de Backup: {self.today} ---")
        print(f"Categorías activas hoy: {active_cats}")

        # Recorremos los servidores
        for server in self.servers:
            print(f"\n[Servidor: {server['name']}]")
            
            # 1. Definimos categoría y rutas
            for category in active_cats:
            
                target_dir = os.path.join(self.destination_root, category, server["name"], self.today)
                print(f"  - Ruta destino: {target_dir}")
                
                # 2. Buscamos el backup anterio para enlaces duros
                link_dest = self.get_latest_backup(server["name"], category)
                print(f"  - Ruta enlace duro: {link_dest}")

                # 3. Recorremos los directorios de cada servidor
                for remote_dir in server["directories"]:
                    # Creamos una carpeta local para este directorio específico
                    local_dir = os.path.join(target_dir, remote_dir.lstrip('/'))
                    os.makedirs(local_dir, exist_ok=True)
                    
                    print(f"  --> Copiando {remote_dir}...")

                    # Construimos el comando rsync
                    # rsync necesita la ruta completa del link_dest para los enlaces duros
                    # IMPORTANTE: link_dest debe ser una ruta absoluta para rsync
                    
                    # Construcción del comando rsync con preservación de identidad numérica
                    command = [
                        "rsync", 
                        "-avz",                # 'a' preserva permisos/dueños, 'v' verboso, 'z' comprime
                        "--numeric-ids",       # VITAL: Mantiene los IDs de usuario originales sin mapearlos
                        "--delete", 
                        "-e", f"ssh -p {server['port']}"
                    ]

                    # Si hay backup previo, añadimos el enlace duro para ahorrar espacio
                    if link_dest:
                        reference_path = os.path.join(link_dest, remote_dir.lstrip('/'))
                        if os.path.exists(reference_path):
                            command.append(f"--link-dest={reference_path}")
                    
                    # AÑADIMOS EL ORIGEN Y EL DESTINO 
                    source = f"{server['user']}@{server['ip']}:{remote_dir}/"
                    command.append(source)
                    command.append(local_dir)
                    print(f"Command: {command}")

                    try:
                        # Ejecutamos rsync
                        subprocess.run(command, check=True)
                        print(f"      [OK] Finalizado.")
                    except subprocess.CalledProcessError as e:
                        print(f"      [ERROR] Error en rsync: {e}")

                if category != "daily":
                    self.promote_backup(server["name"], "daily", category)                


    # Obtiene las categorias que tocan hoy (daily, weekly, mounthly, anualy)
    def get_active_categories(self):
        categories = ["daily"] # Siempre activo
        now = datetime.now()
        
        # Si hoy es lunes (weekday 0), activamos semanal
        if now.weekday() == 0:
            categories.append("weekly")
        
        # Si hoy es día 1 del mes, activamos mensual
        if now.day == 1:
            categories.append("monthly")
            
        # Si hoy es 1 de enero, activamos anual
        if now.month == 1 and now.day == 1:
            categories.append("yearly")
            
        return categories
    
    # Crea un enlace duro local desde una categoría a otra.
    def promote_backup(self, server_name, source_cat, target_cat):
        source_dir = os.path.join(self.destination_root, source_cat, server_name, self.today)
        target_dir = os.path.join(self.destination_root, target_cat, server_name, self.today)

        if not os.path.exists(source_dir):
            print(f"      [SKIP] No hay origen para promocionar a {target_cat}")
            return

        print(f"  --> Promocionando a {target_cat}...")
        os.makedirs(target_dir, exist_ok=True)

        # Usamos rsync localmente para crear los enlaces duros
        # Esto no descarga nada de internet, solo vincula archivos en el disco
        promo_command = [
            "rsync", "-av", "--link-dest", source_dir, f"{source_dir}/", target_dir
        ]
        
        try:
            subprocess.run(promo_command, check=True, capture_output=True)
            print(f"      [OK] Promocionado a {target_cat}")
        except subprocess.CalledProcessError as e:
            print(f"      [ERROR] Fallo al promocionar: {e}")

backup = BackupManager()
# print(f"Categorias activas: {backup.get_active_categories()}")
backup.run()
