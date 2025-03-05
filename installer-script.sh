#!/bin/bash

# Colores para los mensajes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1;37m'
NC='\033[0m' # Sin color
CHECK_MARK="${GREEN}✓${NC}"
CROSS_MARK="${RED}✗${NC}"

# Definir rutas
SCRIPT_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/gmail-notifier"
DESKTOP_FILE="$HOME/.config/autostart/gmail-notifier.desktop"
SCRIPT_PATH="$SCRIPT_DIR/gmail-notifier"
VENV_DIR="$CONFIG_DIR/venv"

# Mostrar banner
show_banner() {
    cat << EOF
╔═════════════════════════════════════════════════════════╗
║                ⚡ GMAIL NOTIFIER PARA KDE ⚡             ║
║                                                         ║
║          _____                _ _                       ║
║         / ____|              (_) |                      ║
║        | |  __  _ __ ___   __ _| |                      ║
║        | | |_ || '_ \` _ \\ / _\` | |                      ║
║        | |__| || | | | | | (_| | |                      ║
║         \\_____||_| |_| |_|\\__,_|_|                      ║
║                                                         ║
║  ┌─────────┐  ┌─────────┐  ┌─────────┐                  ║
║  │ Google  │  │Workspace│  │  KDE    │                  ║
║  │ Monitor │  │ Notifier│  │ System  │                  ║
║  └─────────┘  └─────────┘  └─────────┘                  ║
║                                                         ║
║  📬 Monitorea tu correo de Google Workspace            ║
║  🔔 Notificaciones en la bandeja del sistema           ║
║  🚀 Sin necesidad de tener un cliente de correo abierto ║
║  🔒 Autenticación directa con contraseña de aplicación  ║
║  🛠️ Github: https://github.com/panxos                  ║
║  👨‍💻 Developed by: P4NX0S © 2025 - CHILE               ║
║                                                         ║
╚═════════════════════════════════════════════════════════╝
EOF
}

# Mostrar ayuda
show_help() {
    cat << EOF
${CYAN}USO:${NC}
  $0 [OPCIÓN]

${CYAN}DESCRIPCIÓN:${NC}
  Script de instalación/desinstalación para Gmail Notifier.
  Monitorea automáticamente tu correo de Google Workspace y muestra notificaciones.

${CYAN}OPCIONES:${NC}
  Sin argumentos     Instala Gmail Notifier en el sistema
  -h, --help         Muestra este mensaje de ayuda
  -r, --remove       Desinstala Gmail Notifier del sistema
  -u, --uninstall    Alias para --remove

${CYAN}EJEMPLOS:${NC}
  $0                 Instala Gmail Notifier
  $0 --help          Muestra este mensaje de ayuda
  $0 --remove        Desinstala Gmail Notifier

${CYAN}NOTAS:${NC}
  - Se usa un entorno virtual de Python para evitar conflictos con el sistema
  - Necesitas una contraseña de aplicación para tu cuenta de Google
  - Puedes encontrar el ícono de la aplicación en la bandeja del sistema
EOF
}

# Función de desinstalación
uninstall() {
    echo -e "${YELLOW}===== Desinstalando Gmail Notifier =====${NC}"
    
    # Comprobar si está en ejecución y terminarlo
    if pgrep -f "gmail-notifier" > /dev/null; then
        echo -e "${BLUE}Deteniendo el proceso Gmail Notifier...${NC}"
        pkill -f "gmail-notifier"
    fi
    
    # Eliminar archivos y directorios
    echo -e "${BLUE}Eliminando archivos...${NC}"
    
    # Eliminar scripts
    if [ -f "$SCRIPT_PATH" ]; then
        rm "$SCRIPT_PATH"
        echo -e "  ${CHECK_MARK} Script wrapper eliminado"
    else
        echo -e "  ${CROSS_MARK} Script wrapper no encontrado"
    fi
    
    if [ -f "$CONFIG_DIR/gmail-notifier.py" ]; then
        rm "$CONFIG_DIR/gmail-notifier.py"
        echo -e "  ${CHECK_MARK} Script principal eliminado"
    else
        echo -e "  ${CROSS_MARK} Script principal no encontrado"
    fi
    
    # Eliminar archivo desktop
    if [ -f "$DESKTOP_FILE" ]; then
        rm "$DESKTOP_FILE"
        echo -e "  ${CHECK_MARK} Archivo de autoarranque eliminado"
    else
        echo -e "  ${CROSS_MARK} Archivo de autoarranque no encontrado"
    fi
    
    # Eliminar directorio de configuración
    if [ -d "$CONFIG_DIR" ]; then
        echo -e "${YELLOW}¿Deseas eliminar todos los datos de configuración incluyendo tus credenciales? (s/n)${NC}"
        read -r DELETE_CONFIG
        
        if [[ "$DELETE_CONFIG" =~ ^[Ss]$ ]]; then
            rm -rf "$CONFIG_DIR"
            echo -e "  ${CHECK_MARK} Directorio de configuración eliminado"
        else
            echo -e "  ${CHECK_MARK} Directorio de configuración conservado en $CONFIG_DIR"
            
            # Eliminar solo el entorno virtual
            if [ -d "$VENV_DIR" ]; then
                rm -rf "$VENV_DIR"
                echo -e "  ${CHECK_MARK} Entorno virtual eliminado"
            else
                echo -e "  ${CROSS_MARK} Entorno virtual no encontrado"
            fi
        fi
    else
        echo -e "  ${CROSS_MARK} Directorio de configuración no encontrado"
    fi
    
    echo -e "${GREEN}Desinstalación completada. Gmail Notifier ha sido eliminado del sistema.${NC}"
    
    # Mostrar el banner al finalizar
    echo
    show_banner
    
    exit 0
}

# Función de instalación
install() {
    # Verificar dependencias del sistema
    echo -e "${BLUE}Verificando dependencias del sistema...${NC}"
    echo

    DEPS=("python" "python-virtualenv" "python-pyqt5")
    MISSING=()
    
    # Cabecera de la tabla
    printf "  %-20s %-10s\n" "Dependencia" "Estado"
    printf "  %-20s %-10s\n" "------------" "------"

    for dep in "${DEPS[@]}"; do
        if pacman -Q "$dep" &> /dev/null; then
            printf "  %-20s ${CHECK_MARK} %s\n" "$dep" "Instalado"
        else
            printf "  %-20s ${CROSS_MARK} %s\n" "$dep" "No encontrado"
            MISSING+=("$dep")
        fi
    done
    
    echo

    if [ ${#MISSING[@]} -ne 0 ]; then
        echo -e "${RED}Se requiere instalar las siguientes dependencias:${NC}"
        for dep in "${MISSING[@]}"; do
            echo -e "  - $dep"
        done
        
        echo -e "${BLUE}¿Deseas instalar estas dependencias ahora? (s/n)${NC}"
        read -r INSTALL_DEPS
        
        if [[ "$INSTALL_DEPS" =~ ^[Ss]$ ]]; then
            echo -e "${BLUE}Instalando dependencias...${NC}"
            sudo pacman -S --needed "${MISSING[@]}"
            if [ $? -ne 0 ]; then
                echo -e "${RED}Error al instalar dependencias. Abortando.${NC}"
                exit 1
            fi
            echo -e "${GREEN}Dependencias instaladas correctamente.${NC}"
        else
            echo -e "${RED}Las dependencias son necesarias para continuar. Abortando.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Todas las dependencias están instaladas.${NC}"
    fi

    # Crear directorios de instalación
    echo -e "${BLUE}Creando directorios de instalación...${NC}"
    mkdir -p "$SCRIPT_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Copiar el script principal al directorio de configuración
    echo -e "${BLUE}Copiando script principal...${NC}"
    cp gmail-notifier.py "$CONFIG_DIR/gmail-notifier.py"
    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Script principal copiado a $CONFIG_DIR/gmail-notifier.py"
    else
        echo -e "  ${CROSS_MARK} Error al copiar el script principal"
        echo -e "${RED}Asegúrate de que el archivo gmail-notifier.py existe en el directorio actual.${NC}"
        exit 1
    fi
    
    # Crear un entorno virtual
    echo -e "${BLUE}Creando entorno virtual para dependencias de Python...${NC}"
    python -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Entorno virtual creado en $VENV_DIR"
    else
        echo -e "  ${CROSS_MARK} Error al crear el entorno virtual"
        echo -e "${RED}Verifica que python-virtualenv está instalado correctamente.${NC}"
        exit 1
    fi
    
    # Instalar dependencias en el entorno virtual
    echo -e "${BLUE}Instalando dependencias en el entorno virtual...${NC}"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install PyQt5
    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Dependencias instaladas correctamente"
    else
        echo -e "  ${CROSS_MARK} Error al instalar dependencias en el entorno virtual"
        exit 1
    fi
    
    # Crear wrapper script
    echo -e "${BLUE}Creando script de inicio...${NC}"
    cat > "$SCRIPT_PATH" << EOF
#!/bin/bash
source "$VENV_DIR/bin/activate"
python "$CONFIG_DIR/gmail-notifier.py"
EOF
    
    chmod +x "$SCRIPT_PATH"
    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Script wrapper creado en $SCRIPT_PATH"
    else
        echo -e "  ${CROSS_MARK} Error al crear el script wrapper"
        exit 1
    fi

    # Crear archivo .desktop para el inicio automático
    echo -e "${BLUE}Creando archivo .desktop para autoarranque...${NC}"
    mkdir -p "$HOME/.config/autostart"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Gmail Notifier
Comment=Notificador de Gmail para KDE
Exec=$SCRIPT_PATH
Icon=gmail
Terminal=false
Type=Application
Categories=Network;Email;
StartupNotify=true
X-GNOME-Autostart-enabled=true
EOF

    if [ $? -eq 0 ]; then
        echo -e "  ${CHECK_MARK} Archivo .desktop creado en $DESKTOP_FILE"
    else
        echo -e "  ${CROSS_MARK} Error al crear el archivo .desktop"
        exit 1
    fi

    echo -e "${GREEN}¡Instalación completada correctamente!${NC}"
    echo
    
    # Información sobre contraseñas de aplicación
    cat << EOF
${YELLOW}===========================================================${NC}
  ${BOLD}IMPORTANTE: Sobre las contraseñas de aplicación${NC}
  
  Gmail Notifier necesita una "Contraseña de aplicación" para funcionar:
  
  1. Ve a tu cuenta de Google > Seguridad
  2. Activa la "Verificación en dos pasos" si no la tienes
  3. Busca "Contraseñas de aplicaciones"
  4. Crea una nueva contraseña para "Correo" > "Otra"
     (nombrándola "Gmail Notifier")
  
  Esta contraseña específica te permitirá conectarte de forma
  segura sin utilizar tu contraseña principal de Google.
${YELLOW}===========================================================${NC}
EOF

    echo -e "${BLUE}¿Deseas iniciar Gmail Notifier ahora? (s/n)${NC}"
    read -r START_NOW

    if [[ "$START_NOW" =~ ^[Ss]$ ]]; then
        echo -e "${BLUE}Iniciando Gmail Notifier...${NC}"
        nohup "$SCRIPT_PATH" >/dev/null 2>&1 &
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Gmail Notifier está ejecutándose en la bandeja del sistema.${NC}"
            echo -e "${BLUE}Se abrirá una ventana para configurar tu cuenta.${NC}"
        else
            echo -e "${RED}Error al iniciar Gmail Notifier.${NC}"
            echo -e "${YELLOW}Intenta ejecutarlo manualmente con el comando 'gmail-notifier'${NC}"
        fi
    else
        echo -e "${BLUE}Puedes iniciar Gmail Notifier más tarde ejecutando:${NC}"
        echo -e "  ${GREEN}gmail-notifier${NC}"
    fi
    
    # Mostrar el banner al finalizar
    echo
    show_banner
}

# Comprobar los argumentos
case "$1" in
    -h|--help)
        show_banner
        echo
        show_help
        ;;
    -r|--remove|-u|--uninstall)
        show_banner
        echo
        uninstall
        ;;
    *)
        show_banner
        echo
        install
        ;;
esac
