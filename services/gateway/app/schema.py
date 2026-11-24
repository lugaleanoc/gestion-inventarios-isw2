MYSQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario_id BIGINT NOT NULL AUTO_INCREMENT,
        empresa_id BIGINT NOT NULL,
        nombre VARCHAR(150) NOT NULL,
        correo VARCHAR(150) NOT NULL,
        contrasena_hash VARCHAR(255) NOT NULL,
        rol VARCHAR(30) NOT NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (usuario_id),
        UNIQUE KEY uq_usuarios_correo (correo),
        KEY idx_usuarios_empresa (empresa_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS codigos_recuperacion (
        codigo_id BIGINT NOT NULL AUTO_INCREMENT,
        usuario_id BIGINT NOT NULL,
        codigo_hash CHAR(64) NOT NULL,
        expira_en DATETIME NOT NULL,
        usado TINYINT(1) NOT NULL DEFAULT 0,
        PRIMARY KEY (codigo_id),
        UNIQUE KEY uq_codigos_hash (codigo_hash),
        KEY idx_codigos_usuario (usuario_id),
        CONSTRAINT fk_codigos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (usuario_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tiendas_web (
        tienda_id BIGINT NOT NULL AUTO_INCREMENT,
        empresa_id BIGINT NOT NULL,
        nombre VARCHAR(150) NOT NULL,
        cliente_id VARCHAR(40) NOT NULL,
        clave_secreta_hash VARCHAR(255) NOT NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (tienda_id),
        UNIQUE KEY uq_tiendas_cliente (cliente_id),
        KEY idx_tiendas_empresa (empresa_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tokens_revocados (
        jti VARCHAR(64) NOT NULL,
        expira_en DATETIME NOT NULL,
        fecha_revocacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (jti),
        KEY idx_tokens_expira (expira_en)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

SQLITE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario_id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        correo TEXT NOT NULL UNIQUE,
        contrasena_hash TEXT NOT NULL,
        rol TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1,
        fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS codigos_recuperacion (
        codigo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios (usuario_id),
        codigo_hash TEXT NOT NULL UNIQUE,
        expira_en TEXT NOT NULL,
        usado INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tiendas_web (
        tienda_id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        cliente_id TEXT NOT NULL UNIQUE,
        clave_secreta_hash TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1,
        fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tokens_revocados (
        jti TEXT PRIMARY KEY,
        expira_en TEXT NOT NULL,
        fecha_revocacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]
