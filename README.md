# Backup scripts

Repositorio con scripts para realizar copias de seguridad remotas y locales.

## Resumen

Este repositorio contiene un orquestador en Python (`backup_script.py`) que realiza backups por SSH/rsycn de las rutas listadas en la configuración (`backup_config.py`). El flujo principal es:

- Conectarse por SSH a cada servidor definido en `backup_config.SERVERS`.
- Sincronizar directorios remotos con `rsync` a una estructura local en `BACKUP_DESTINATION` organizada por categoría (`daily`, `weekly`, `monthly`, `yearly`) y por servidor.
- Usar `--link-dest` (enlaces duros) para economizar espacio entre backups y promover backups de `daily` a otras categorías según corresponda.
- Eliminar backups antiguos según los límites definidos en `ROTATION`.

## Archivos importantes

- `backup_config.py`: Variables de configuración principales: `BACKUP_DESTINATION`, `ROTATION`, `EXCLUSIONS` y `SERVERS`.
- `backup_script.py`: Script principal que realiza la sincronización, promoción (hardlink via rsync) y limpieza.

## Requisitos

- Python 3.8+ (o la versión instalada en el sistema).
- `rsync` instalado en la máquina local.
- `ssh` (cliente) configurado y con acceso a los servidores remotos listados.
- Permisos de escritura en la ruta indicada por `BACKUP_DESTINATION`.

Nota: El script no instala dependencias por sí mismo; solo requiere utilidades del sistema (`rsync`, `ssh`).

## Configuración (en `backup_config.py`)

- `BACKUP_DESTINATION`: ruta local donde se guardan las copias.
- `ROTATION`: diccionario con los límites de retención por categoría (ej. `"daily": 7`).
- `EXCLUSIONS`: lista de patrones pasados a `rsync --exclude`.
- `SERVERS`: lista de diccionarios con `name`, `ip`, `port`, `user` y `directories` (lista de rutas remotas a sincronizar).

Ejemplo de servidor en `backup_config.py`:

```py
{
		"name": "vps_instancia",
		"ip": "1.2.3.4",
		"port": 22,
		"user": "root",
		"directories": ["/etc", "/root/.ssh"]
}
```

Recomendación: no incluir secretos en `backup_config.py`. Para claves privadas SSH, use el agente SSH o archivos `~/.ssh` con permisos adecuados.

## Comportamiento del script (`backup_script.py`)

- Crea la estructura de directorios en `BACKUP_DESTINATION` por categoría y servidor.
- Para cada servidor y cada directorio remoto, ejecuta `rsync -avz --numeric-ids --delete -e "ssh -p <port>"` hacia `BACKUP_DESTINATION/<category>/<server>/<YYYY-MM-DD>/<remote_path>`.
- Añade `--exclude` por cada entrada en `EXCLUSIONS`.
- Si hay un backup previo, intenta usar `--link-dest` apuntando al backup anterior para crear hardlinks y ahorrar espacio.
- Tras completar `daily`, si hoy corresponde (por ejemplo, lunes para `weekly`, día 1 para `monthly`, 1 de enero para `yearly`), promociona (`rsync --link-dest`) la copia `daily` a la categoría correspondiente.
- Finalmente ejecuta limpieza: borra carpetas más antiguas manteniendo el número definido en `ROTATION` (usa `rm -rf` internamente).

## Ejecución

Ejecutar de forma manual:

```bash
python3 backup_script.py
```

Para guardar salida y errores en ficheros de log:

```bash
python3 backup_script.py >> backup.log 2>> errores.txt
```

## Seguridad y riesgos

- `backup_script.py` ejecuta `rsync` y puede invocar `rm -rf` durante la limpieza. Verifique la configuración antes de ejecutar en producción.
- Asegúrese de que las rutas en `SERVERS[*]["directories"]` sean correctas y que el usuario `user` tenga permisos de lectura en los servidores remotos.
- No incluya secretos o contraseñas en `backup_config.py`. Use claves SSH con passphrases y `ssh-agent`.

## Cron / Programación (ejemplo)

Ejemplo para ejecutar diariamente a las 02:30 y rotar logs:

```cron
30 2 * * * cd /mnt/datos1/scripts/python/backup && /usr/bin/python3 backup_script.py >> backup.log 2>> errores.txt
