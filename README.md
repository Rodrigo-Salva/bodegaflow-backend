# Bodegaflow — Backend

Bodegaflow es una API REST profesional para la gestión integral de bodegas (usuarios, catálogo, inventario, compras y ventas), construida con Django y Django REST Framework. Este README está diseñado para ser visual, claro y listo para publicarse en GitHub.

---

## Índice
- [Visión general](#-visión-general)
- [Stack tecnológico](#️-stack-tecnológico)
- [Arquitectura](#️-arquitectura--estructura-de-carpetas)
- [Inicio rápido](#-inicio-rápido-local)
- [Autenticación y permisos](#-autenticación-y-permisos)
- [Flujo de inventario y ventas](#-flujo-clave-ventas-e-inventario)
- [Endpoints principales](#-endpoints-principales-resumen)
- [Variables de entorno](#️-variables-de-entorno-esenciales)
- [Cómo contribuir](#-cómo-contribuir)
- [Contacto](#-contacto)

---

## ✅ Visión general

Bodegaflow ofrece una API REST moderna para:
- Gestión de usuarios y roles.
- Catálogo de productos y categorías.
- Control de inventario (entradas/salidas, stock).
- Gestión de ventas y compras con líneas y totales.
- Reportes básicos (ventas por rango, productos bajo stock).

Diseñado para ser consumido por aplicaciones web o móviles, con autenticación mediante JWT y enfoque en transacciones atómicas para la integridad del stock.

---

## ⚙️ Stack tecnológico

- **Python 3.10+**
- **Django**
- **Django REST Framework**
- **djangorestframework-simplejwt** (JWT)
- **PostgreSQL** (recomendado)
- **Redis** (cache / broker) — opcional
- **Celery** (tareas asíncronas) — opcional
- **Docker / docker-compose** — opcional
- **GitHub Actions** (CI sugerido)

---

## 🏛️ Arquitectura — Estructura de carpetas
```
📁 bodegaflow-backend/
├─ 📁 .github/
│  └─ 📁 workflows/              # Configuraciones CI (GitHub Actions)
├─ 📁 config/
│  ├─ 📄 asgi.py
│  ├─ 📄 wsgi.py
│  └─ 📁 settings/
│     ├─ 📄 base.py              # Ajustes comunes
│     ├─ 📄 development.py       # Settings para desarrollo
│     └─ 📄 production.py        # Settings para producción
├─ 📁 apps/                      # Aplicaciones Django por dominio
│  ├─ 📁 users/
│  │  ├─ 📄 models.py            # User, Profile, Roles
│  │  ├─ 📄 serializers.py
│  │  ├─ 📄 views.py             # ViewSets / Endpoints de users
│  │  └─ 📄 urls.py
│  ├─ 📁 products/
│  │  ├─ 📄 models.py            # Product, Category, SKU
│  │  ├─ 📄 serializers.py
│  │  ├─ 📄 views.py
│  │  └─ 📄 urls.py
│  ├─ 📁 inventory/
│  │  ├─ 📄 models.py            # InventoryMovement, Stock
│  │  ├─ 📄 serializers.py
│  │  ├─ 📄 views.py
│  │  └─ 📄 urls.py
│  ├─ 📁 sales/
│  │  ├─ 📄 models.py            # Sale, SaleLine
│  │  ├─ 📄 serializers.py       # Validación de líneas y totales
│  │  ├─ 📄 views.py             # Crear venta: transacción + ajuste stock
│  │  └─ 📄 urls.py
│  └─ 📁 purchases/
│     ├─ 📄 models.py            # Purchase, PurchaseLine
│     ├─ 📄 serializers.py
│     ├─ 📄 views.py             # Registrar compras y entradas de stock
│     └─ 📄 urls.py
├─ 📁 core/
│  ├─ 📄 urls.py                 # Router principal y documentación API
│  └─ 📄 utils.py                # Utilidades (help functions)
├─ 📁 static/                    # Archivos estáticos
├─ 📁 media/                     # Archivos subidos (prod: S3 opcional)
├─ 📁 docker/                    # Dockerfiles / compose (opcional)
├─ 📄 manage.py
├─ 📄 requirements.txt
├─ 📄 .env.example               # Ejemplo de variables de entorno
└─ 📄 README.md                  # Este archivo
```

### Diagrama de arquitectura
```mermaid
flowchart LR
Client[Cliente Web/Mobile]
Nginx[Nginx/Proxy/TLS]
Gunicorn[Gunicorn/uWSGI]
Django[Django REST API]
Auth[(JWT Auth)]
Users[Users App]
Products[Products App]
Inventory[Inventory App]
Sales[Sales App]
Purchases[Purchases App]
Postgres[(PostgreSQL)]
Redis[(Redis)]
Celery[Celery Workers]

Client -->|HTTPS| Nginx
Nginx --> Gunicorn
Gunicorn --> Django
Django --> Auth
Django --> Users
Django --> Products
Django --> Inventory
Django --> Sales
Django --> Purchases
Django --> Postgres
Django --> Redis
Celery --> Redis
Celery --> Postgres
Django -->|enqueue| Celery
```

**Descripción de flujo:**
- El cliente (web/mobile) consume la API (Django REST) protegida por JWT.
- Al crear ventas/compras, la app usa transacciones atómicas y señales/funciones para actualizar stock y registrar movimientos en inventory.
- Para trabajos pesados o notificaciones, Django encola tareas en Celery (broker: Redis).

**Notas de diseño:**
- ViewSets + Routers para CRUD.
- Serializers con validación y manejo de relaciones anidadas (p. ej. líneas de venta).
- Signals o transacciones atómicas para ajustar stock en ventas/compras.
- Permisos basados en roles (is_staff / is_superuser / permisos por objeto).

---

## 🚀 Inicio rápido (local)

### 1) Clonar el repositorio
```bash
git clone https://github.com/Rodrigo-Salva/bodegaflow-backend.git
cd bodegaflow-backend
```

### 2) Crear entorno virtual e instalar dependencias
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

### 3) Configurar variables de entorno

Copia `.env.example` a `.env` y ajusta los valores (SECRET_KEY, DATABASE_URL, etc.)

### 4) Ejecutar migraciones y crear superusuario
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Docker (opcional)

Si existe `docker-compose.yml`:
```bash
docker-compose up --build
```

---

## 🔐 Autenticación y permisos

- **Autenticación:** JWT (access + refresh tokens)
- **Endpoints públicos:** registro y obtención de token
- **Rutas protegidas:** crear/editar/eliminar recursos (requieren `Authorization: Bearer <access_token>`)
- **Recomendación:** usar roles/permisos personalizados para separar operadores, administradores y contabilidad

### Ejemplo de header de autenticación:
```
Authorization: Bearer <ACCESS_TOKEN>
```

---

## 🔁 Flujo clave: ventas e inventario

### Al crear una venta:
1. Validar stock disponible por producto
2. Abrir transacción atómica
3. Crear la venta y sus líneas
4. Registrar movimiento(s) de inventario (salida)
5. Actualizar stock en la tabla de productos o stock

### Al registrar una compra:
1. Registrar entrada de inventario
2. Aumentar stock disponible

**Recomendación:** Usar tests y transacciones para evitar condiciones de carrera.

---

## 🧩 Endpoints principales (resumen)

Ajusta rutas según tu `urls.py`. Ejemplos:

### Auth
- `POST /api/auth/register/` — Registro de usuario
- `POST /api/auth/token/` — Obtener tokens (access + refresh)
- `POST /api/auth/token/refresh/` — Refrescar access token

### Usuarios
- `GET /api/users/` — Listar usuarios
- `GET /api/users/{id}/` — Detalle de usuario
- `PUT/PATCH/DELETE /api/users/{id}/` — Actualizar/eliminar usuario

### Productos
- `GET /api/products/` — Listar productos
- `POST /api/products/` — Crear producto
- `GET/PUT/PATCH/DELETE /api/products/{id}/` — Detalle/actualizar/eliminar producto

### Inventario
- `GET /api/inventory/` — Listar movimientos de inventario
- `POST /api/inventory/` — Registrar movimiento (entrada/salida)
- `GET /api/inventory/stock/` — Consultar stock actual

### Ventas
- `GET /api/sales/` — Listar ventas
- `POST /api/sales/` — Crear venta (con líneas)
- `GET /api/sales/{id}/` — Detalle de venta

### Compras
- `GET /api/purchases/` — Listar compras
- `POST /api/purchases/` — Registrar compra

### Ejemplos con cURL

**Obtener token:**
```bash
curl -X POST https://tu-api.example.com/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"tu_password"}'
```

**Crear producto (requiere autenticación):**
```bash
curl -X POST https://tu-api.example.com/api/products/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Vino Tinto","sku":"VIN-001","price":12.5,"stock":100}'
```

---

## 🛠️ Variables de entorno esenciales

- `SECRET_KEY` — Clave secreta de Django
- `DEBUG` — True/False (False en producción)
- `ALLOWED_HOSTS` — Lista de hosts permitidos
- `DATABASE_URL` — URL de conexión a PostgreSQL  
  O por separado: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `SIMPLE_JWT` settings — Tiempos de expiración de tokens (opcional)
- `REDIS_URL` — URL de Redis (si se usa)
- `CELERY_BROKER_URL` — URL del broker para Celery (si se usa)
- `DEFAULT_FROM_EMAIL`, `EMAIL_*` — Configuración de email (si se envían correos)

### Ejemplo de archivo `.env`:
```env
SECRET_KEY=tu_clave_secreta_super_segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://bodega:password@localhost:5432/bodegaflow
REDIS_URL=redis://localhost:6379/0
```

---

## 🤝 Cómo contribuir

1. **Fork** del repositorio → Crear rama `feature/mi-cambio`
2. Realizar cambios y añadir **tests**
3. Asegurar **formato de código:** PEP8, usar black/isort
4. Crear **Pull Request** hacia `main` con descripción clara
5. Incluir **migraciones** si corresponde

### Checklist para PRs:
- [ ] Código formateado (black/isort)
- [ ] Tests añadidos/actualizados
- [ ] Documentación actualizada (README / API_DOCS)
- [ ] Commits con mensajes claros
- [ ] Migraciones incluidas (si aplica)

---

## 📬 Contacto

**Mantenedor:** Rodrigo-Salva  
**Repositorio:** [https://github.com/Rodrigo-Salva/bodegaflow-backend]([https://github.com/Rodrigo-Salva/bodegaflow-backend](https://github.com/Rodrigo-Salva/bodegaflow-backend/)

---

**¡Gracias por usar Bodegaflow! 🚀🍷**
