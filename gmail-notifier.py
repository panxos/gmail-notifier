#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import imaplib
import email
import webbrowser
import getpass
from email.header import decode_header
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox, QInputDialog, QLineEdit, QDialog, QLabel, QVBoxLayout, QPushButton, QGridLayout, QCheckBox
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtGui import QIcon

# Configuración
CONFIG_DIR = os.path.expanduser('~/.config/gmail-notifier')
SETTINGS_PATH = os.path.join(CONFIG_DIR, 'settings.json')

# Asegurarse de que el directorio de configuración existe
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Configuración predeterminada
DEFAULT_SETTINGS = {
    'check_interval': 300,  # Segundos (5 minutos)
    'gmail_url': 'https://mail.google.com',
    'last_check_time': 0,
    'last_uid': 0,
    'username': '',
    'password': ''  # La contraseña se guarda encriptada
}

# Encriptación simple para la contraseña (no es muy segura, pero mejor que texto plano)
def encrypt(text):
    if not text:
        return ""
    result = ""
    for char in text:
        result += chr(ord(char) + 5)
    return result

def decrypt(text):
    if not text:
        return ""
    result = ""
    for char in text:
        result += chr(ord(char) - 5)
    return result

# Cargar configuración
def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
            # Desencriptar contraseña
            if 'password' in settings:
                settings['password'] = decrypt(settings['password'])
            return settings
    return DEFAULT_SETTINGS

# Guardar configuración
def save_settings(settings):
    # Crear una copia para no modificar el original
    settings_to_save = settings.copy()
    # Encriptar contraseña antes de guardar
    if 'password' in settings_to_save:
        settings_to_save['password'] = encrypt(settings_to_save['password'])

    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings_to_save, f)

# Diálogo para configurar la cuenta
class ConfigDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Configurar Gmail Notifier')
        self.setMinimumWidth(400)

        layout = QGridLayout()

        # Campos de entrada
        layout.addWidget(QLabel('Correo electrónico:'), 0, 0)
        self.username_input = QLineEdit(self.settings.get('username', ''))
        layout.addWidget(self.username_input, 0, 1)

        layout.addWidget(QLabel('Contraseña de aplicación:'), 1, 0)
        self.password_input = QLineEdit(self.settings.get('password', ''))
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input, 1, 1)

        # Información sobre contraseña de aplicación
        info_label = QLabel(
            'Nota: Debes usar una "Contraseña de aplicación" específica para Gmail.\n'
            '1. Ve a tu cuenta de Google > Seguridad\n'
            '2. Activa la verificación en dos pasos si no la tienes\n'
            '3. Busca "Contraseñas de aplicaciones"\n'
            '4. Genera una nueva para "Correo" > "Otra (Gmail Notifier)"'
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label, 2, 0, 1, 2)

        # Intervalo de verificación
        layout.addWidget(QLabel('Verificar cada (minutos):'), 3, 0)
        self.interval_input = QLineEdit(str(self.settings.get('check_interval', 300) // 60))
        layout.addWidget(self.interval_input, 3, 1)

        # Autoarranque
        self.autostart_checkbox = QCheckBox('Iniciar automáticamente con el sistema')
        desktop_file = os.path.expanduser('~/.config/autostart/gmail-notifier.desktop')
        self.autostart_checkbox.setChecked(os.path.exists(desktop_file))
        layout.addWidget(self.autostart_checkbox, 4, 0, 1, 2)

        # Botones
        button_layout = QVBoxLayout()
        save_button = QPushButton('Guardar')
        save_button.clicked.connect(self.save_config)
        cancel_button = QPushButton('Cancelar')
        cancel_button.clicked.connect(self.reject)
        test_button = QPushButton('Probar conexión')
        test_button.clicked.connect(self.test_connection)

        button_layout.addWidget(test_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout, 5, 0, 1, 2)

        self.setLayout(layout)

    def save_config(self):
        # Validar datos
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, 'Error', 'Debes introducir un correo y contraseña válidos')
            return

        try:
            interval = int(self.interval_input.text()) * 60  # Convertir a segundos
            if interval < 60:
                interval = 60  # Mínimo 1 minuto
        except ValueError:
            interval = 300  # 5 minutos por defecto

        # Guardar configuración
        self.settings['username'] = username
        self.settings['password'] = password
        self.settings['check_interval'] = interval

        # Configurar autoarranque
        desktop_file = os.path.expanduser('~/.config/autostart/gmail-notifier.desktop')
        if self.autostart_checkbox.isChecked():
            # Crear archivo .desktop para autoarranque
            os.makedirs(os.path.dirname(desktop_file), exist_ok=True)
            script_path = os.path.abspath(sys.argv[0])

            with open(desktop_file, 'w') as f:
                f.write(f"""[Desktop Entry]
Name=Gmail Notifier
Comment=Notificador de Gmail para KDE
Exec={script_path}
Icon=gmail
Terminal=false
Type=Application
Categories=Network;Email;
StartupNotify=true
X-GNOME-Autostart-enabled=true
""")
        else:
            # Eliminar archivo .desktop si existe
            if os.path.exists(desktop_file):
                os.remove(desktop_file)

        self.accept()

    def test_connection(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, 'Error', 'Debes introducir un correo y contraseña válidos')
            return

        try:
            # Intentar conectar a Gmail con IMAP
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(username, password)
            mail.select('inbox')
            mail.close()
            mail.logout()

            QMessageBox.information(self, 'Conexión exitosa', 'La conexión con Gmail se ha establecido correctamente.')
        except Exception as e:
            QMessageBox.critical(self, 'Error de conexión', f'No se pudo conectar a Gmail: {str(e)}')

# Clase para verificar correos en un hilo separado
class GmailChecker(QObject):
    new_emails_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.running = True

    def check_emails(self):
        username = self.settings.get('username', '')
        password = self.settings.get('password', '')

        if not username or not password:
            self.error_signal.emit("Configuración incompleta. Por favor, configura tu cuenta de Gmail.")
            return []

        try:
            # Conectar a Gmail con IMAP
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(username, password)
            mail.select('inbox')

            # Buscar correos no leídos
            status, messages = mail.search(None, 'UNSEEN')

            if status != 'OK':
                mail.close()
                mail.logout()
                return []

            email_data = []

            # Obtener IDs de mensajes no leídos
            message_ids = messages[0].split()

            # Verificar los últimos 10 correos no leídos como máximo
            for msg_id in message_ids[-10:]:
                status, msg_data = mail.fetch(msg_id, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])')

                if status != 'OK':
                    continue

                # Decodificar el mensaje
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Obtener remitente y asunto con manejo mejorado de codificación
                subject = self._decode_header_safely(msg['Subject'])
                sender = self._decode_header_safely(msg['From'])

                # Filtrar solo el nombre del remitente si está disponible
                if '<' in sender:
                    sender_name = sender.split('<')[0].strip()
                    sender = sender_name if sender_name else sender

                email_data.append({
                    'id': msg_id.decode(),
                    'subject': subject,
                    'sender': sender
                })

            mail.close()
            mail.logout()

            return email_data

        except Exception as e:
            error_msg = f"Error al verificar correos: {str(e)}"
            self.error_signal.emit(error_msg)
            return []

    def _decode_header_safely(self, header):
        """Decodifica los encabezados de correo de manera segura manejando diferentes codificaciones."""
        if not header:
            return ""
        
        try:
            # Intentar decodificar usando email.header.decode_header
            decoded_parts = decode_header(header)
            result = ""
            
            for decoded_text, charset in decoded_parts:
                # Si es bytes, decodificar con la codificación correcta o fallback a alternativas
                if isinstance(decoded_text, bytes):
                    if charset:
                        try:
                            # Intentar con la codificación especificada
                            part = decoded_text.decode(charset)
                        except (UnicodeDecodeError, LookupError):
                            # Si falla, intentar con UTF-8
                            try:
                                part = decoded_text.decode('utf-8')
                            except UnicodeDecodeError:
                                # Si UTF-8 falla, intentar con latin-1 (siempre funciona pero puede mostrar caracteres incorrectos)
                                part = decoded_text.decode('latin-1')
                    else:
                        # Sin codificación especificada, intentar UTF-8 primero
                        try:
                            part = decoded_text.decode('utf-8')
                        except UnicodeDecodeError:
                            # Fallback a latin-1
                            part = decoded_text.decode('latin-1')
                else:
                    # Ya es un string
                    part = decoded_text
                    
                result += part
                
            return result
            
        except Exception:
            # Si todo falla, devolver un valor predeterminado
            return "[Codificación no soportada]"

    def run(self):
        last_check_time = self.settings.get('last_check_time', 0)
        check_interval = self.settings.get('check_interval', 300)

        while self.running:
            current_time = time.time()

            # Verificar si es hora de comprobar nuevos correos
            if current_time - last_check_time >= check_interval:
                emails = self.check_emails()

                if emails:
                    self.new_emails_signal.emit(emails)

                # Actualizar el tiempo de la última verificación
                self.settings['last_check_time'] = current_time
                save_settings(self.settings)
                last_check_time = current_time

            # Esperar un poco antes de la siguiente iteración
            time.sleep(10)  # Verificar cada 10 segundos si es hora de comprobar correos

# Clase principal para la aplicación
class GmailNotifier:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Cargar configuración
        self.settings = load_settings()

        # Verificar si se necesita configuración
        if not self.settings.get('username') or not self.settings.get('password'):
            self.show_config_dialog()

        # Crear el icono de la bandeja del sistema
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(self.get_icon())
        self.tray_icon.setToolTip('Gmail Notifier')

        # Crear el menú del icono
        self.menu = QMenu()

        self.open_gmail_action = QAction('Abrir Gmail')
        self.open_gmail_action.triggered.connect(self.open_gmail)
        self.menu.addAction(self.open_gmail_action)

        self.check_now_action = QAction('Verificar ahora')
        self.check_now_action.triggered.connect(self.check_now)
        self.menu.addAction(self.check_now_action)

        self.config_action = QAction('Configuración')
        self.config_action.triggered.connect(self.show_config_dialog)
        self.menu.addAction(self.config_action)

        self.menu.addSeparator()

        self.quit_action = QAction('Salir')
        self.quit_action.triggered.connect(self.quit)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self.tray_activated)

        # Iniciar el hilo de verificación de correos
        self.checker_thread = QThread()
        self.gmail_checker = GmailChecker(self.settings)
        self.gmail_checker.moveToThread(self.checker_thread)

        self.checker_thread.started.connect(self.gmail_checker.run)
        self.gmail_checker.new_emails_signal.connect(self.on_new_emails)
        self.gmail_checker.error_signal.connect(self.on_error)

        # Mostrar el icono en la bandeja
        self.tray_icon.show()

        # Iniciar el hilo
        self.checker_thread.start()

    def get_icon(self):
        # Busca el icono de Gmail en varias ubicaciones comunes
        icon_paths = [
            '/usr/share/icons/hicolor/scalable/apps/gmail.svg',
            '/usr/share/icons/hicolor/48x48/apps/gmail.png',
            '/usr/share/icons/breeze/apps/48/gmail.svg',
            '/usr/share/pixmaps/gmail.png'
        ]

        for path in icon_paths:
            if os.path.exists(path):
                return QIcon(path)

        # Si no encuentra el icono, usar un icono del sistema
        return QIcon.fromTheme('mail-unread')

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.open_gmail()

    def open_gmail(self):
        webbrowser.open(self.settings.get('gmail_url', 'https://mail.google.com'))

    def check_now(self):
        # Esta función solo actualiza el tiempo de la última verificación
        # para forzar una verificación inmediata en el siguiente ciclo
        self.settings['last_check_time'] = 0
        save_settings(self.settings)

    def show_config_dialog(self):
        dialog = ConfigDialog(self.settings)
        if dialog.exec_():
            # Si el diálogo se acepta, guardar la configuración
            self.settings = dialog.settings
            save_settings(self.settings)

    def on_new_emails(self, emails):
        if not emails:
            return

        # Mostrar notificación para el correo más reciente
        newest_email = emails[0]
        self.tray_icon.showMessage(
            f"Nuevo correo de {newest_email['sender']}",
            newest_email['subject'],
            QSystemTrayIcon.Information,
            5000  # Mostrar por 5 segundos
        )

    def on_error(self, error_msg):
        self.tray_icon.showMessage(
            "Error en Gmail Notifier",
            error_msg,
            QSystemTrayIcon.Warning,
            5000
        )

    def quit(self):
        # Detener el hilo
        self.gmail_checker.running = False
        self.checker_thread.quit()
        self.checker_thread.wait()

        # Salir de la aplicación
        self.app.quit()

    def run(self):
        return self.app.exec_()

# Función principal
def main():
    # Verificar que existe el directorio de configuración
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Iniciar la aplicación
    notifier = GmailNotifier()
    sys.exit(notifier.run())

if __name__ == '__main__':
    main()
