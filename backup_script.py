#!/usr/bin/env python3

import os
import subprocess
import tempfile
from datetime import datetime, timedelta
import backup_config


class BackupManager:
    """Gestor de backups con rotación diaria/semanal/mensual/anual."""

    def __init__(self):
        self.destination_root = backup_config.BACKUP_DESTINATION
        self.rotation = backup_config.ROTATION
        self.servers = backup_config.SERVERS
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.categories = self.get_active_categories()
        self.exclusions = getattr(backup_config, 'EXCLUSIONS', [])

    def setup_directories(self):
        """Crea la estructura base de carpetas: categoría / servidor."""
        print(f"Verificando directorios en {self.destination_root}...")
        for category in self.rotation.keys():
            for server in self.servers:
                path = os.path.join(self.destination_root, category, server["name"])
                os.makedirs(path, exist_ok=True)

    def get_latest_backup(self, server_name, category):
        """Busca la carpeta de backup más reciente en la categoría dada."""
        server_path = os.path.join(self.destination_root, category, server_name)

        if not os.path.exists(server_path):
            return None

        list_elements = os.listdir(server_path)
        dir_backups = []
        for element in list_elements:
            full_path = os.path.join(server_path, element)
            if os.path.isdir(full_path):
                dir_backups.append(element)

        dir_backups = sorted(dir_backups)

        if not dir_backups:
            return None

        last_backup = dir_backups[-1]
        return os.path.join(server_path, last_backup)

    def get_active_categories(self):
        """Determina qué rotaciones tocan hoy según la fecha."""
        categories = ["daily"]
        now = datetime.now()

        if now.weekday() == 0:
            categories.append("weekly")
        if now.day == 1:
            categories.append("monthly")
        if now.month == 1 and now.day == 1:
            categories.append("yearly")

        return categories

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
        target_dir = os.path.join(self.destination_root, category, server["name"], self.today)
        link_dest = self.get_latest_backup(server["name"], category)

        # Evitamos usar el mismo backup como referencia
        if link_dest and self.today in link_dest:
            link_dest = None

        # Asegurar que el directorio destino base exista
        os.makedirs(target_dir, exist_ok=True)

        print(f"  --> Sincronizando directorios por SSH...")

        # Es necesario incluir la opción -r ya que --files-from anula el comportamiento recursivo de -a
        command = ["rsync", "-avzr", "--numeric-ids", "--delete"]

        # --- ORDEN CRÍTICO DE RSYNC ---
        # El primer patrón que coincide GANA. Orden correcto:
        # 1. --exclude para TODO lo que NO queremos (primero)
        # 2. --include='.*' para otros archivos ocultos (no excluidos)
        # 3. --include='*' para incluir el resto

        current_exclusions = self.exclusions + server.get('extra_exclusions', [])

        with tempfile.NamedTemporaryFile(mode='w', delete=True) as exclude_file:
            # 1. PRIMERO: Escribir TODOS los patrones de exclusión en el archivo temporal
            for pattern in current_exclusions:
                exclude_file.write(f"{pattern}\n")
            exclude_file.flush() # Asegurar que se escriben a disco antes de que rsync lo lea

            command.append(f"--exclude-from={exclude_file.name}")

            # 2. Luego incluir archivos ocultos no excluidos
            command.append("--include=.*")

            # 3. Incluir todo lo demás
            command.append("--include=*")

            # Leer lista de archivos desde stdin
            command.append("--files-from=-")

            command.extend(["-e", f"ssh -p {server['port']}"])

            # --link-dest
            if link_dest:
                command.append(f"--link-dest={link_dest}")

            # Origen y destino
            source_path = f"{server['user']}@{server['ip']}:/"
            dest_path = f"{target_dir}/"

            command.append(source_path)
            command.append(dest_path)

            # Preparar la lista de directorios a respaldar (separada por saltos de línea)
            files_list = "\n".join(server["directories"]) + "\n"

            # Debug: descomenta para ver comando completo
            print(f"      Comando: {' '.join(command)}")

            try:
                subprocess.run(command, input=files_list, check=True, capture_output=True, text=True)
                print(f"      [OK] Finalizado.")
            except subprocess.CalledProcessError as e:
                print(f"      [ERROR] Falló rsync: {e.stderr}")

    def cleanup(self):
        """Elimina backups antiguos que excedan los límites."""
        print(f"\n--- Iniciando limpieza de backups antiguos ---")
        for category, limit in self.rotation.items():
            for server in self.servers:
                server_path = os.path.join(self.destination_root, category, server["name"])

                if not os.path.exists(server_path):
                    continue

                backups = sorted([d for d in os.listdir(server_path)
                                if os.path.isdir(os.path.join(server_path, d))])

                if len(backups) > limit:
                    to_delete = backups[:-limit]
                    for folder in to_delete:
                        full_path = os.path.join(server_path, folder)
                        print(f"  [CLEANUP] Borrando: {category}/{server['name']}/{folder}")
                        subprocess.run(["rm", "-rf", full_path])

    def run(self):
        """Ejecución principal."""
        self.setup_directories()
        active_cats = self.categories
        print(f"--- Iniciando Backup: {self.today} ---")
        print(f"Categorías de hoy: {active_cats}")

        for server in self.servers:
            print(f"\n[Servidor: {server['name']}]")
            self.process_rsync_ssh(server, "daily")
            for cat in active_cats:
                if cat != "daily":
                    self.promote_backup(server["name"], "daily", cat)

        self.cleanup()


if __name__ == "__main__":
    backup = BackupManager()
    backup.run()