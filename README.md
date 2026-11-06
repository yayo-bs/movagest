# MovaGest

MovaGest es una aplicación web en Flask para gestionar una asociación cultural sin ánimo de lucro. La plataforma está pensada para separar claramente la experiencia de los socios de la gestión administrativa: registro con aprobación, noticias, documentos/actas, talleres, asambleas, cuotas y movimientos financieros.

La aplicación sigue el patrón de Application Factory con blueprints, usa SQLite en desarrollo y un modelo de roles basado en `socio` y `administrador`.

## Descripción

### Funcionalidades actuales

- Autenticación y autorización con Flask-Login.
- Registro de socios con alta pendiente de aprobación y revisión por parte de administración.
- Login, logout y protección de rutas por rol.
- Panel principal para socios y administradores con resumen de noticias, próximas asambleas, talleres y documentos.
- Gestión de noticias y documentos/actas con permisos diferenciados.
- Gestión de convocatorias de asamblea (ordinaria y extraordinaria).
- CRUD de talleres con control de aforo y cancelación de inscripciones.
- Módulo de finanzas con cuotas, movimientos de ingresos/gastos y generación de recibos PDF.
- Registro de la cuenta de la asociación y comprobación de totales por año.
- Registro de actividad visible para administradores.
- Gestión de socios con baja lógica y posibilidad de reactivación.
- Búsqueda, ordenación, filtrado y paginación en los listados que lo implementan.

### Roles de usuario

- Socio: puede iniciar sesión, consultar contenido, ver documentos y actas, ver noticias, consultar asambleas y inscribirse en talleres.
- Administrador: tiene todas las capacidades del socio y además puede crear/editar/eliminar contenido, aprobar altas, gestionar talleres y administrar finanzas.

### Stack tecnológico

- Python + Flask
- Flask-SQLAlchemy + SQLite
- Flask-Login
- Flask-WTF
- python-dotenv
- ReportLab
- pytest
- Jinja2 / HTML / CSS
- Un único archivo JavaScript propio, `app/static/js/navegacion.js`, para la navegación, sin dependencias.

## Instalación

### Requisitos

- Python 3.14 (desarrollado y probado con 3.14.2).
- Git y acceso a la terminal del proyecto.
- Dependencias declaradas en `requirements.txt`.

### Pasos

1. Clona el repositorio y entra en la carpeta del proyecto.
2. Crea y activa un entorno virtual:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

4. Copia `.env.example` a `.env` y ajusta las variables locales:

```powershell
# PowerShell
Copy-Item .env.example .env
# Linux/macOS
cp .env.example .env
```

Flask carga `.env` automáticamente. En desarrollo, estas variables de ejemplo permiten arrancar la aplicación:

```env
FLASK_CONFIG=desarrollo
SECRET_KEY=clave-local-de-ejemplo-no-usar-en-produccion
DATABASE_URL=sqlite:///movagest.db
NOMBRE_ASOCIACION=MovaGest
CARPETA_SUBIDAS=subidas
MAX_CONTENT_LENGTH=10485760
FLASK_DEBUG=false
SESSION_COOKIE_SECURE=false
```

`SECRET_KEY` es obligatoria fuera de desarrollo y pruebas; configura allí una clave privada y aleatoria. `DATABASE_URL` usa SQLite local por defecto. `CARPETA_SUBIDAS` se resuelve respecto a `instance/` si es una ruta relativa y no puede apuntar a `static/`. `MAX_CONTENT_LENGTH` indica el máximo de la petición en bytes (10 MiB por defecto). `FLASK_DEBUG` queda desactivada salvo que se active expresamente. Mantén `SESSION_COOKIE_SECURE=false` en desarrollo HTTP y actívala solo al desplegar detrás de HTTPS; las cookies siempre usan `HttpOnly` y `SameSite=Lax`.

Genera una clave propia con este comando y copia el resultado en `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Para producción, define `FLASK_CONFIG=produccion`, una `SECRET_KEY` segura y las variables adecuadas para la base de datos y el almacenamiento. No copies la clave de ejemplo a un despliegue real.

5. Inicializa la base de datos:

```bash
flask --app run.py init-db
```

Vuelve a ejecutar este comando cuando se añadan tablas nuevas al proyecto.

6. (Opcional) Crea el primer administrador:

```bash
flask --app run.py crear-admin
```

Este comando solicita nombre, apellidos, email y contraseña del primer usuario administrador. Es opcional si se va a utilizar únicamente la cuenta administradora de demostración en un entorno local.

7. (Opcional) Carga el conjunto ficticio para revisar las pantallas:

```bash
flask --app run.py cargar-demo
```

El orden de inicialización es `init-db`, `crear-admin` (opcional) y `cargar-demo`. No hace falta volver a ejecutar `init-db` para cargar la demo, porque no se añaden tablas.

8. Arranca la aplicación desde la raíz del proyecto:

```bash
python run.py
```

### Datos de demostración

`cargar-demo` crea usuarios, noticias, documentos PDF, talleres, asambleas y datos financieros ficticios. El comando es idempotente: una segunda ejecución no duplica el contenido. Para borrar y recrear únicamente las filas identificadas como demo y sus PDF:

```bash
flask --app run.py cargar-demo --reiniciar
```

La contraseña común es **`Danza-MovaDemo-2026!`**:

- Administrador: `junta@demo.example.com`
- Administradora: `coordinacion@demo.example.com`
- Socia: `socia01@demo.example.com`

Estas credenciales son públicas y se deben usar solo en desarrollo o pruebas. Por seguridad, la carga se bloquea con la configuración de producción salvo que se indique expresamente `--forzar`; no uses cuentas ni contraseñas de demostración en un despliegue real.

## Uso

### Ejecutar la aplicación

Una vez arrancada con el comando del paso 8, la aplicación queda disponible por defecto en:

```text
http://127.0.0.1:5000/
```

### Rutas principales

Las rutas se contrastaron con `flask --app run.py routes`.

- **Públicas:** `/` (portada), `/auth/registro` (solicitud de alta), `/auth/login` y `/auth/logout` (POST).
- **Socios (con sesión):** `/inicio`, `/noticias/`, `/documentos/`, `/asambleas/`, `/talleres/`, `/finanzas/mis-cuotas` y `/finanzas/cuotas/<int:id_cuota>/recibo`.
- **Administradores:** `/admin/altas` (gestión de socios: altas, rechazados y bajas, con filtros por estado), `/admin/actividad`, `/finanzas/cuotas`, `/finanzas/cuotas/generar` y `/finanzas/movimientos`.
- **Gestión de contenido por administradores:** noticias: `/noticias/nueva`, `/noticias/<int:id_noticia>/editar` y `/noticias/<int:id_noticia>/borrar`; documentos: `/documentos/nuevo` y `/documentos/<int:id_documento>/borrar`; asambleas: `/asambleas/nueva`, `/asambleas/<int:id_asamblea>/editar` y `/asambleas/<int:id_asamblea>/eliminar`; talleres: `/talleres/nuevo`, `/talleres/<int:id_taller>/editar` y `/talleres/<int:id_taller>/borrar`. Las rutas de borrado/eliminación usan POST. No existe actualmente una ruta para editar documentos.

### Pruebas

Se usa pytest con SQLite en memoria para pruebas aisladas:

```bash
pytest -q
```

También se puede ejecutar un fichero concreto:

```bash
pytest tests/test_auth.py -q
```

## Estructura del proyecto

```text
movagest/
├── app/
│   ├── __init__.py              # Application factory y registro de blueprints
│   ├── comandos.py              # comandos Flask: init-db, crear-admin y cargar-demo
│   ├── config.py                # configuraciones de desarrollo, pruebas y producción
│   ├── demo.py                  # carga y reinicio selectivo de datos de demostración
│   ├── decoradores.py           # protección por rol (solo administradores)
│   ├── extensiones.py          # db, login_manager y csrf
│   ├── asambleas/               # módulo de asambleas
│   │   ├── formularios.py
│   │   ├── consultas.py
│   │   └── rutas.py
│   ├── blueprints/
│   │   ├── admin/
│   │   ├── auth/
│   │   └── main/
│   ├── documentos/              # documentos y actas
│   ├── finanzas/                # cuotas, movimientos y recibos PDF
│   │   ├── operaciones.py       # operaciones compartidas para cuotas
│   │   └── recibos.py           # generación de recibos PDF
│   ├── models/                  # modelos SQLAlchemy
│   │   ├── actividad.py
│   │   ├── asamblea.py
│   │   ├── documento.py
│   │   ├── finanzas.py
│   │   ├── noticia.py
│   │   ├── taller.py
│   │   └── usuario.py
│   ├── noticias/                # noticias y contenido editorial
│   ├── static/
│   │   ├── css/
│   │   ├── img/
│   │   └── js/
│   │       └── navegacion.js    # controles de navegación sin dependencias
│   ├── talleres/                # talleres e inscripciones
│   ├── templates/
│   │   ├── admin/
│   │   ├── asambleas/
│   │   ├── auth/
│   │   ├── documentos/
│   │   ├── finanzas/
│   │   ├── main/
│   │   ├── noticias/
│   │   ├── talleres/
│   │   ├── base.html
│   │   ├── home.html
│   │   └── ...
│   └── utilidades/
│       ├── actividad.py
│       ├── formatos.py
│       └── listados.py
├── instance/
│   ├── movagest.db              # base de datos de desarrollo
│   └── subidas/                 # archivos adjuntos de documentos
├── tests/
│   ├── conftest.py              # fixtures de la app y cliente de pruebas
│   ├── test_seguridad.py        # pruebas de seguridad y permisos
│   └── test_*.py                # suite de validación por módulo
├── .env.example                 # ejemplo de variables de entorno
├── .gitignore
├── pytest.ini
├── README.md
├── requirements.txt
├── run.py
└── ...
```

## Arquitectura y flujo de trabajo

La aplicación se construye con `create_app()` en `app/__init__.py`. Esa factory:

- crea la aplicación Flask,
- carga la configuración según `FLASK_CONFIG`,
- inicializa `db`, `login_manager` y `csrf`,
- registra cada blueprint del proyecto,
- y añade los comandos CLI de inicialización.

Cada módulo tiene una responsabilidad clara:

- `auth`: registro, login y control de sesión.
- `main`: página de inicio y resumen global.
- `admin`: solicitudes de alta, baja y gestión de usuarios.
- `noticias`: contenido informativo.
- `documentos`: archivos y actas.
- `asambleas`: convocatoria y agenda asociativa.
- `talleres`: alta de actividades y gestión de aforo.
- `finanzas`: cuotas, recibos y movimientos.

Esta separación facilita mantener la lógica de negocio en modelos y consultas, y deja las rutas enfocadas en la interacción con el usuario.

## Notas de desarrollo

- La base de datos de desarrollo se guarda en `instance/movagest.db`.
- Los documentos subidos se guardan en `instance/subidas/`.
- En pruebas se usa una base de datos SQLite en memoria y la protección CSRF queda desactivada para aislar el flujo de validación.
- El proyecto sigue la convención de negocio de no registro abierto: cada alta requiere aprobación de un administrador.
- Los talleres tienen plazas limitadas y la inscripción valida estrictamente el aforo y duplicados.
- Las facturas/recibos no se borran: se conservan con su estado y se registran como pagadas o anuladas.

## Estado del proyecto

El proyecto está en desarrollo activo, con una estructura ya organizada por módulos y una capa funcional básica operativa para gestión asociativa, autenticación, contenido y finanzas.
