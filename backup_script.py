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
        # self.categories = ["daily", "weekly", "monthly", "yearly"]
        self.categories = self.get_active_categories()
        self.exclusions = getattr(backup_config, 'EXCLUSIONS', [])
    
    def setup_directories(self):
        """Crea la estructura base de carpetas: categoría / servidor"""
        print(f"Verificando directorios en {self.destination_root}...")
        for category in self.rotation.keys():
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

    # Obtiene las categorias que tocan hoy (daily, weekly, mounthly, anualy)
    def get_active_categories(self):
        """Determina qué rotaciones tocan hoy según la fecha."""
        categories = ["daily"]
        now = datetime.now()
        
        if now.weekday() == 0: categories.append("weekly")
        if now.day == 1: categories.append("monthly")
        if now.month == 1 and now.day == 1: categories.append("yearly")
            
        return categories
    
    # Crea un enlace duro local desde una categoría a otra.
    def promote_backup(self, server_name, source_cat, target_cat):
        """Copia local instantánea usando enlaces duros entre categorías."""
        source_dir = os.path.join(self.destination_root, source_cat, server_name, self.today)     
        target_dir = os.path.join(self.destination_root, target_cat, server_name, self.today)
        print(f"  --> Promoviendo backup de {source_cat} a {target_cat}...")
 
        if not os.path.exists(source_dir):
            print(f"      [SKIP] No hay origen para promocionar a {target_cat}")
            return

        print(f"  --> Promocionando localmente a {target_cat}...")
        os.makedirs(target_dir, exist_ok=True)

        promo_command = [
            "rsync", "-av", "--link-dest", source_dir, f"{source_dir}/", target_dir
        ]
        
        try:
            subprocess.run(promo_command, check=True, capture_output=True)
            print(f"      [OK] Promoción finalizada.")
        except subprocess.CalledProcessError as e:
            print(f"      [ERROR] Fallo al promocionar: {e}")

    def process_rsync_ssh(self, server, category):
        """Sincronización principal desde el servidor remoto."""
        # Directorio destino para este backup
        target_dir = os.path.join(self.destination_root, category, server["name"], self.today)
        # Obtener el último backup para usar como referencia
        link_dest = self.get_latest_backup(server["name"], category)
        
        # Evitamos usar el mismo backup como referencia
        if link_dest and self.today in link_dest:
            link_dest = None

        for remote_dir in server["directories"]:
            local_dir = os.path.join(target_dir, remote_dir.lstrip('/'))
            os.makedirs(local_dir, exist_ok=True)
            
            print(f"  --> Sincronizando {remote_dir} por SSH...")

            command = [
                "rsync", "-avz", "--numeric-ids", "--delete",
                "-e", f"ssh -p {server['port']}"
            ]
            # Aplicamos las exclusiones desde la variable de clase
            for pattern in self.exclusions:
                command.append(f"--exclude={pattern}")

            if link_dest:
                reference_path = os.path.join(link_dest, remote_dir.lstrip('/'))
                if os.path.exists(reference_path):
                    command.append(f"--link-dest={reference_path}")

            command.append(f"{server['user']}@{server['ip']}:{remote_dir}/")
            command.append(local_dir)

            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
                print(f"      [OK] Finalizado.")
            except subprocess.CalledProcessError as e:
                print(f"      [ERROR] Falló rsync: {e.stderr}")

    def cleanup(self):
        print(f"\n--- Iniciando limpieza de backups antiguos ---")
        # Recorremos cada categoría (daily, weekly...) y su límite (7, 4...)
        for category, limit in self.rotation.items():
            for server in self.servers:
                # Ruta: /backups/daily/vps_instancia/
                server_path = os.path.join(self.destination_root, category, server["name"])
                
                if not os.path.exists(server_path): continue
                
                # Cogemos solo directorios (fechas) y los ordenamos (Viejo -> Nuevo)
                backups = sorted([d for d in os.listdir(server_path) 
                                if os.path.isdir(os.path.join(server_path, d))])
                
                # Si hay más de los permitidos...
                if len(backups) > limit:
                    # Seleccionamos los que sobran (desde el principio hasta el límite)
                    to_delete = backups[:-limit]
                    for folder in to_delete:
                        full_path = os.path.join(server_path, folder)
                        print(f"  [CLEANUP] Borrando backup antiguo: {category}/{server['name']}/{folder}")
                        # Borrado físico
                        subprocess.run(["rm", "-rf", full_path])

    def run(self):
        """Ejecución principal."""
        self.setup_directories()
        active_cats = self.categories
        print(f"--- Iniciando Backup: {self.today} ---")
        print(f"Categorías de hoy: {active_cats}")

        for server in self.servers:
            print(f"\n[Servidor: {server['name']}]")
            # 1. Backup por red a 'daily'
            self.process_rsync_ssh(server, "daily")
            # 2. Promoción local a otras categorías (weekly, etc)
            for cat in active_cats:
                if cat != "daily":
                    self.promote_backup(server["name"], "daily", cat)
        # Limpieza de backups antiguos
        self.cleanup()

if __name__ == "__main__":
    backup = BackupManager()
    backup.run()
