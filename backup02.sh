#!/bin/bash

# --- VARIABLES BÁSICAS ---
# Para que funcionen los enlaces duros, las rutas deben ser absolutas
BACKUP_ROOT="/mnt/datos1/scripts/bash/backup/backup_destino"
SERVER_ALIAS="VPS_instancia"
SSH_USER="ubuntu"
SSH_HOST="144.24.194.24"
REMOTE_DIR="/etc"
LOG_FILE="./backup_vps.log" # Para registrar los movimientos de rotación

# --- ⚙️ LÍMITES DE ROTACIÓN (PARAMETRIZADOS) ---
# Número de copias a mantener en cada nivel (Diaria/Semanal/Mensual/Anual)
LIMIT_DAILY=7    # Mantiene DAY.0 hasta DAY.6
LIMIT_WEEKLY=3   # Mantiene WEEK.1 hasta WEEK.3
LIMIT_MONTHLY=3  # Mantiene MONTH.1 hasta MONTH.3
LIMIT_YEARLY=2   # Mantiene YEAR.1 hasta YEAR.2

# Opciones de rsync (Usando Array, ya que funciona)
RSYNC_OPTS=(
    -avz
    --delete
    --numeric-ids
    --rsync-path="sudo rsync"
)

# Directorio base para el servidor
DEST_PATH="$BACKUP_ROOT/$SERVER_ALIAS"

# Crear el directorio base del servidor si no existe
sudo mkdir -p "$DEST_PATH"

# --- 🔄 FUNCIÓN DE ROTACIÓN COMPLETA (Activada por Contador) ---
function rotate_backups {
    echo "--- $(date) - Iniciando rotación parametrizada en $SERVER_ALIAS ---" >> "$LOG_FILE"

    # --- 1. Promociones y Rotación Superior (YEARLY, MONTHLY, WEEKLY) ---
    
    # 1.1. ROTACIÓN ANUAL (Promoción de MONTH.1 a YEAR.1)
    # Límite de Promoción: Si hay 3 copias mensuales (MONTH.1, MONTH.2, MONTH.3), promovemos la más antigua.
    MONTH_COUNT=$(ls -d $DEST_PATH/MONTH.* 2>/dev/null | wc -l)
    if [ "$MONTH_COUNT" -ge "$LIMIT_MONTHLY" ]; then
        echo "--> Ejecutando Rotación Anual (Se alcanzó el límite mensual)..." >> "$LOG_FILE"
        
        # Rotar Anuales: YEAR.1 -> YEAR.2, y eliminar YEAR.2 si se supera el límite.
        if [ -d "$DEST_PATH/YEAR.1" ]; then 
            if [ "$LIMIT_YEARLY" -le 1 ]; then
                sudo rm -rf "$DEST_PATH/YEAR.1"
            else
                sudo rm -rf "$DEST_PATH/YEAR.$LIMIT_YEARLY"
                sudo mv "$DEST_PATH/YEAR.1" "$DEST_PATH/YEAR.2"
            fi
        fi
        
        # Promoción: Mover MONTH.1 (más antigua) a YEAR.1
        if [ -d "$DEST_PATH/MONTH.1" ]; then 
            # cp -al crea una copia por enlaces duros (no gasta espacio)
            sudo cp -al "$DEST_PATH/MONTH.1" "$DEST_PATH/YEAR.1" 
            sudo rm -rf "$DEST_PATH/MONTH.1" # Eliminar la fuente después de la promoción
            
            # Desplazar el resto de mensuales
            for i in $(seq 2 "$LIMIT_MONTHLY"); do
                if [ -d "$DEST_PATH/MONTH.$i" ]; then sudo mv "$DEST_PATH/MONTH.$i" "$DEST_PATH/MONTH.$((i-1))"; fi
            done
        fi
    fi

    # 1.2. ROTACIÓN MENSUAL (Promoción de WEEK.1 a MONTH.1)
    # Límite de Promoción: Si hay 3 copias semanales.
    WEEK_COUNT=$(ls -d $DEST_PATH/WEEK.* 2>/dev/null | wc -l)
    if [ "$WEEK_COUNT" -ge "$LIMIT_WEEKLY" ]; then
        echo "--> Ejecutando Rotación Mensual (Se alcanzó el límite semanal)..." >> "$LOG_FILE"
        
        # Rotar Mensuales: MONTH.1 -> MONTH.2, etc., y eliminar la más antigua.
        if [ -d "$DEST_PATH/MONTH.$LIMIT_MONTHLY" ]; then sudo rm -rf "$DEST_PATH/MONTH.$LIMIT_MONTHLY"; fi
        for i in $(seq "$((LIMIT_MONTHLY - 1))" -1 1); do
            if [ -d "$DEST_PATH/MONTH.$i" ]; then sudo mv "$DEST_PATH/MONTH.$i" "$DEST_PATH/MONTH.$((i+1))"; fi
        done

        # Promoción: Mover WEEK.1 (más antigua) a MONTH.1
        if [ -d "$DEST_PATH/WEEK.1" ]; then 
            sudo cp -al "$DEST_PATH/WEEK.1" "$DEST_PATH/MONTH.1"
            sudo rm -rf "$DEST_PATH/WEEK.1" # Eliminar la fuente después de la promoción
            
            # Desplazar el resto de semanales
            for i in $(seq 2 "$LIMIT_WEEKLY"); do
                if [ -d "$DEST_PATH/WEEK.$i" ]; then sudo mv "$DEST_PATH/WEEK.$i" "$DEST_PATH/WEEK.$((i-1))"; fi
            done
        fi
    fi

    # 1.3. ROTACIÓN SEMANAL (Promoción de DAY.6 a WEEK.1)
    # Límite de Promoción: Si hay 7 copias diarias.
    DAY_COUNT=$(ls -d $DEST_PATH/DAY.* 2>/dev/null | wc -l)
    if [ "$DAY_COUNT" -ge "$LIMIT_DAILY" ]; then
        echo "--> Ejecutando Rotación Semanal (Se alcanzó el límite diario)..." >> "$LOG_FILE"
        
        # Rotar Semanales: WEEK.1 -> WEEK.2, etc., y eliminar la más antigua.
        if [ -d "$DEST_PATH/WEEK.$LIMIT_WEEKLY" ]; then sudo rm -rf "$DEST_PATH/WEEK.$LIMIT_WEEKLY"; fi
        for i in $(seq "$((LIMIT_WEEKLY - 1))" -1 1); do
            if [ -d "$DEST_PATH/WEEK.$i" ]; then sudo mv "$DEST_PATH/WEEK.$i" "$DEST_PATH/WEEK.$((i+1))"; fi
        done
        
        # Promoción: Mover la más antigua de las diarias (DAY.N-1) a WEEK.1
        OLDEST_DAILY_DIR="DAY.$((LIMIT_DAILY - 1))"
        if [ -d "$DEST_PATH/$OLDEST_DAILY_DIR" ]; then 
            sudo mv "$DEST_PATH/$OLDEST_DAILY_DIR" "$DEST_PATH/WEEK.1" 
        fi
    fi

    # --- 2. ROTACIÓN DIARIA (Siempre se ejecuta) ---
    echo "--> Ejecutando Rotación Diaria..." >> "$LOG_FILE"
    
    # 2.1. Eliminar la copia más antigua (si no fue promocionada a WEEK.1)
    OLDEST_DAILY_DIR="DAY.$((LIMIT_DAILY - 1))"
    if [ -d "$DEST_PATH/$OLDEST_DAILY_DIR" ]; then
        sudo rm -rf "$DEST_PATH/$OLDEST_DAILY_DIR"
    fi

    # 2.2. Desplazar las copias (DAY.N-2 -> DAY.N-1, ..., DAY.0 -> DAY.1)
    # Secuencia: (LIMIT_DAILY - 2) down to 0
    for i in $(seq "$((LIMIT_DAILY - 2))" -1 0); do
        if [ -d "$DEST_PATH/DAY.$i" ]; then
            sudo mv "$DEST_PATH/DAY.$i" "$DEST_PATH/DAY.$((i+1))"
        fi
    done
    
    echo "Rotación finalizada." >> "$LOG_FILE"
}

# --- EJECUCIÓN DEL BACKUP ---

# 1. Ejecutar la rotación (mueve la copia de ayer, DAY.0, a DAY.1)
rotate_daily

# 2. Preparar la opción --link-dest (enlaza con la copia de ayer, ahora en DAY.1)
LINK_DEST_OPT=""
if [ -d "$DEST_PATH/DAY.1" ]; then
    # Usamos la ruta absoluta para --link-dest (fundamental para rsync)
    LINK_DEST_OPT="--link-dest=$DEST_PATH/DAY.1" 
    echo "Usando DAY.1 como referencia de enlaces duros." >> "$LOG_FILE"
fi

# 3. Preparar el directorio de destino actual (DAY.0)
echo "Creando directorio de destino: $TODAY_DIR" >> "$LOG_FILE"
sudo mkdir -p "$TODAY_DIR"

echo "Iniciando copia de $SSH_USER@$SSH_HOST:$REMOTE_DIR..." >> "$LOG_FILE"

# 4. Comando rsync (¡Ahora con LINK_DEST_OPT!)
# NOTA IMPORTANTE: Si copias /etc, debes añadir una barra / al final del origen remoto
# para evitar crear /etc/etc en el destino.
# En este caso, rsync es inteligente y lo hace bien, pero se suele recomendar:
# rsync ... "$SSH_USER@$SSH_HOST:$REMOTE_DIR/" "$TODAY_DIR"

sudo rsync "${RSYNC_OPTS[@]}" $LINK_DEST_OPT "$SSH_USER@$SSH_HOST:$REMOTE_DIR" "$TODAY_DIR"

# Verificación
if [ $? -eq 0 ]; then
    echo "✅ Copia de seguridad completada con éxito." >> "$LOG_FILE"
else
    echo "❌ ERROR: La copia de seguridad falló." >> "$LOG_FILE"
fi