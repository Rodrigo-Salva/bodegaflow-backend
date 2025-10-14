# Usamos imagen oficial de Python
FROM python:3.12-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiar requirements y luego instalar
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copiar todo el proyecto al contenedor
COPY . .

# Exponer puerto
EXPOSE 8080

# Comando por defecto al levantar el contenedor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8090"]
