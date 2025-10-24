# build.py
import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build_app():
    # Configuración
    app_name = "ProductivityApp"
    icon_path = "Reloj.ico"
    sound_file = "alarm.wav"
    main_script = "widget.py"
    
    # Verificar que existen los archivos necesarios
    if not Path(icon_path).exists():
        print(f"❌ No se encuentra el icono: {icon_path}")
        return
    
    if not Path(sound_file).exists():
        print(f"❌ No se encuentra el archivo de sonido: {sound_file}")
        return
    
    # Comando de PyInstaller
    args = [
        main_script,
        "--onefile",
        "--noconsole",
        f"--icon={icon_path}",
        f"--name={app_name}",
        f"--add-data={icon_path};.",
        f"--add-data={sound_file};.",
        "--hidden-import=PySide6.QtMultimedia",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtCore",
    ]
    
    print("🚀 Compilando aplicación...")
    PyInstaller.__main__.run(args)
    
    # Crear carpeta de distribución con recursos
    dist_dir = Path("dist")
    resources_dir = dist_dir / "resources"
    resources_dir.mkdir(exist_ok=True)
    
    # Copiar archivos adicionales a la carpeta de distribución
    if Path(sound_file).exists():
        shutil.copy2(sound_file, dist_dir / sound_file)
        shutil.copy2(sound_file, resources_dir / sound_file)
    
    print(f"✅ Aplicación compilada en: {dist_dir / app_name}.exe")
    print("📁 Recursos incluidos:")
    print(f"   - {sound_file}")
    print(f"   - {icon_path}")

if __name__ == "__main__":
    build_app()