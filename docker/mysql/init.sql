-- Crea una base de datos y un usuario por microservicio.
-- Cada usuario solo tiene permisos sobre su propia base.
-- MySQL ejecuta este archivo solo la primera vez (volumen vacio);
-- para volver a ejecutarlo: docker compose down -v
-- Claves de desarrollo (iguales al nombre del usuario).

-- Gateway (usuarios, roles, tiendas web)
CREATE DATABASE IF NOT EXISTS gateway_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'gateway'@'%' IDENTIFIED BY 'gateway';
GRANT ALL PRIVILEGES ON gateway_db.* TO 'gateway'@'%';

-- Inventario
CREATE DATABASE IF NOT EXISTS inventario_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'inventario'@'%' IDENTIFIED BY 'inventario';
GRANT ALL PRIVILEGES ON inventario_db.* TO 'inventario'@'%';

-- Reposicion
CREATE DATABASE IF NOT EXISTS reposicion_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'reposicion'@'%' IDENTIFIED BY 'reposicion';
GRANT ALL PRIVILEGES ON reposicion_db.* TO 'reposicion'@'%';

-- Proveedores
CREATE DATABASE IF NOT EXISTS proveedores_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'proveedores'@'%' IDENTIFIED BY 'proveedores';
GRANT ALL PRIVILEGES ON proveedores_db.* TO 'proveedores'@'%';

-- Reportes
CREATE DATABASE IF NOT EXISTS reportes_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'reportes'@'%' IDENTIFIED BY 'reportes';
GRANT ALL PRIVILEGES ON reportes_db.* TO 'reportes'@'%';

-- Configuracion
CREATE DATABASE IF NOT EXISTS configuracion_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'configuracion'@'%' IDENTIFIED BY 'configuracion';
GRANT ALL PRIVILEGES ON configuracion_db.* TO 'configuracion'@'%';

-- Ventas
CREATE DATABASE IF NOT EXISTS ventas_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'ventas'@'%' IDENTIFIED BY 'ventas';
GRANT ALL PRIVILEGES ON ventas_db.* TO 'ventas'@'%';

-- Balance Diario
CREATE DATABASE IF NOT EXISTS balance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'balance'@'%' IDENTIFIED BY 'balance';
GRANT ALL PRIVILEGES ON balance_db.* TO 'balance'@'%';

FLUSH PRIVILEGES;
