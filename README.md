# FastCaptions

Herramienta profesional para la creación de subtítulos animados y clips virales de forma automatizada utilizando IA (Whisper).

## Características

- **Transcripción Automática**: Utiliza `faster-whisper` para obtener una precisión excepcional.
- **Edición en Tiempo Real**: Editor de texto integrado para corregir palabras y ajustar tiempos.
- **Preview Sincronizado**: Previsualización con audio para ver exactamente cómo quedará el resultado.
- **Estilos Personalizados**: Cambia colores, tamaños y bordes sobre la marcha.
- **Exportación**: Genera archivos `.ass` listos para renderizar.

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/TU_USUARIO/subtitulador.git
   cd subtitulador
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación:
   ```bash
   python subtitulador.py
   ```

## Desarrollo (Tests)

Para ejecutar las pruebas:

```bash
pytest
```

## Requisitos Externos

- **FFmpeg**: Necesario para el procesamiento de video y audio. Asegúrate de tenerlo en el PATH o en la carpeta raíz del proyecto como `ffmpeg.exe` y `ffprobe.exe`.
