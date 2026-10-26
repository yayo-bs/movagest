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

### Roles de usuario

- Socio: puede iniciar sesión, consultar contenido, ver documentos y actas, ver noticias, consultar asambleas y inscribirse en talleres.
- Administrador: tiene todas las capacidades del socio y además puede crear/editar/eliminar contenido, aprobar altes, gestionar talleres y administrar finanzas.

### Stack tecnológico

- Python + Flask
- Flask-SQLAlchemy + SQLite
- Flask-Login
- Flask-WTF
- ReportLab
- pytest
- Jinja2 / HTML / CSS

## Instalación

### Requisitos

- Python 3.x con entorno virtual activo.
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

4. Configura las variables de entorno. El proyecto carga automáticamente un archivo `.env` si existe. Un ejemplo válido es:

```env
FLASK_CONFIG=desarrollo
SECRET_KEY=tu_clave_secreta
DATABASE_URL=sqlite:///movagest.db
```

La aplicación usa `app/config.py` para leer estas variables y construir la configuración. Si no se define ninguna, se aplican valores por defecto para desarrollo.

5. Inicializa la base de datos:

```bash
flask --app run.py init-db
```

6. Crea el primer administrador:

```bash
flask --app run.py crear-admin
```

Este comando solicita nombre, apellidos, email y contraseña del primer usuario administrador.

## Uso

### Ejecutar la aplicación

```bash
python run.py
```

La aplicación queda disponible por defecto en:

```text
http://127.0.0.1:5000/
```

### Rutas principales

- `/` y `/inicio`: portada pública y panel de inicio autenticado.
- `/registro`: alta de socio con aprobación.
- `/login` y `/logout`: autenticación.
- `/altas`: revisión de solicitudes de alta por administración.
- `/noticias`: listado y detalle de noticias.
- `/documentos`: listado, descarga y gestión de documentos/actas.
- `/talleres`: listado, detalle, inscripción y cancelación de talleres.
- `/asambleas`: acceso a convocatorias y gestión por parte de administración.
- `/movimientos` y `/cuotas`: finanzas de la asociación.

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
│   ├── comandos.py              # comandos Flask: init-db y crear-admin
│   ├── config.py                # configuración de desarrollo y testing
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
│   ├── models/                  # modelos SQLAlchemy
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
│       ├── formatos.py
│       └── listados.py
├── instance/
│   ├── movagest.db              # base de datos de desarrollo
│   └── subidas/                 # archivos adjuntos de documentos
├── tests/
│   ├── conftest.py              # fixtures de la app y cliente de pruebas
│   └── test_*.py                # suite de validación por módulo
├── .env                         # variables de entorno locales
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
