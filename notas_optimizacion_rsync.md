# Notas de Optimización del Script de Backup

Este documento detalla las técnicas avanzadas y de nivel profesional implementadas en el script `backup_script.py` para sincronizar archivos y directorios de forma robusta utilizando las capacidades nativas de `rsync`.

## 1. El Problema Original
La versión inicial del script verificaba de forma manual las extensiones de los ficheros para intentar discernir si una ruta era un archivo o un directorio antes de pasársela a `rsync`. Esto es una práctica frágil ("chapucería") ya que los nombres de directorios pueden llevar puntos y los archivos pueden carecer de extensiones.

## 2. Inyección de Listas de Archivos a través de `stdin` (`--files-from=-`)
Para evitar procesar si una ruta es un directorio o un archivo, delegamos la lógica completamente a `rsync`.

Se utiliza el parámetro `--files-from=-`. El guion final (`-`) le indica a `rsync` que no lea la lista de rutas desde un archivo físico en el disco, sino desde su entrada estándar (**stdin**).

### Implementación en Python:
Preparamos una cadena de texto en memoria que contiene todas las rutas, separadas por saltos de línea (`\n`):

```python
files_list = "\n".join(server["directories"]) + "\n"
```

Luego, al ejecutar el comando externo a través del módulo `subprocess`, inyectamos directamente esta cadena de texto mediante el parámetro `input`:

```python
subprocess.run(command, input=files_list, check=True, text=True)
```
De este modo, `rsync` procesa instantáneamente toda la lista de forma nativa.

## 3. Manejo Limpio de Exclusiones con Archivos Temporales
El comando `rsync` puede fallar si intentamos enviarle cientos o miles de patrones de exclusión directamente por la línea de comandos (limitaciones de caracteres de la shell). 

La solución profesional es usar `--exclude-from`, pero para no dejar archivos de configuración "basura" o residuales tras ejecutar el backup, generamos un **archivo temporal que se auto-destruye**.

### Implementación en Python:
Utilizamos la utilidad nativa `tempfile.NamedTemporaryFile` combinada con un gestor de contexto (`with`). 

```python
import tempfile

# mode='w' (modo escritura texto), delete=True (borrar archivo al terminar el bloque)
with tempfile.NamedTemporaryFile(mode='w', delete=True) as exclude_file:
    # 1. Escribimos todas las exclusiones en el archivo
    for pattern in current_exclusions:
        exclude_file.write(f"{pattern}\n")
    
    # 2. Forzamos la escritura al disco físico (importante antes de llamar a rsync)
    exclude_file.flush() 

    # 3. Le pasamos el nombre del fichero temporal a rsync
    command.append(f"--exclude-from={exclude_file.name}")
    
    # 4. Lanzamos el proceso rsync...
    subprocess.run(...)
    
# Cuando Python sale de la indentación del 'with', el archivo se borra automáticamente del sistema.
```

## 4. Orden Crítico de Reglas de Inclusión/Exclusión
Cuando se usa `rsync`, el orden de los filtros es fundamental. El primer patrón que coincide, gana. El orden lógico implementado es:

1. **Excluir lo que no queremos** (`--exclude-from=archivo_temporal`)
2. **Incluir explícitamente archivos ocultos** no excluidos (`--include=.*`)
3. **Incluir todo lo demás** que está en nuestras rutas de origen (`--include=*`)

Con esta arquitectura, el código es escalable, mucho más rápido (un solo comando rsync por servidor) y completamente robusto contra rutas complejas y grandes volúmenes de exclusiones.
