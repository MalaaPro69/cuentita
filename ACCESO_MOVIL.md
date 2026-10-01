# Acceso desde el celular

## 1. Instalar Cloudflare Tunnel

En PowerShell como administrador:

```powershell
winget install Cloudflare.cloudflared
```

Cierra y vuelve a abrir PowerShell después de la instalación.

## 2. Abrir la aplicación y el túnel

Desde la carpeta `Cuentita` ejecuta:

```powershell
.\iniciar_tunel.ps1
```

El script inicia FastAPI y muestra una URL pública parecida a:

```text
https://algo.trycloudflare.com
```

## 3. Entrar desde el celular

Abre en el navegador del teléfono:

```text
https://algo.trycloudflare.com/login
```

Registra una cuenta o inicia sesión con una cuenta existente.

## Importante

- La computadora debe permanecer encendida mientras uses la aplicación.
- La ventana del túnel debe permanecer abierta.
- La URL temporal cambia cada vez que se inicia el túnel.
- Para cerrar el acceso remoto, cierra la ventana donde corre `cloudflared`.
- El archivo `.env` contiene credenciales privadas y no debe compartirse ni subirse a Git.
