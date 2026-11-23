MYSQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS proveedores (
        proveedor_id BIGINT NOT NULL AUTO_INCREMENT,
        empresa_id BIGINT NOT NULL,
        nombre VARCHAR(150) NOT NULL,
        nit VARCHAR(30) NOT NULL,
        contacto_nombre VARCHAR(150) NULL,
        contacto_telefono VARCHAR(40) NULL,
        contacto_correo VARCHAR(150) NULL,
        plazo_entrega_dias INT NULL,
        forma_pago VARCHAR(60) NULL,
        pedido_minimo DECIMAL(14,2) NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        PRIMARY KEY (proveedor_id),
        UNIQUE KEY uq_proveedores_empresa_nit (empresa_id, nit),
        KEY idx_proveedores_empresa (empresa_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS proveedor_producto (
        proveedor_id BIGINT NOT NULL,
        producto_id BIGINT NOT NULL,
        principal TINYINT(1) NOT NULL DEFAULT 0,
        precio_compra DECIMAL(14,2) NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        PRIMARY KEY (proveedor_id, producto_id),
        KEY idx_proveedor_producto_producto (producto_id),
        CONSTRAINT fk_proveedor_producto_proveedor
            FOREIGN KEY (proveedor_id) REFERENCES proveedores (proveedor_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

SQLITE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS proveedores (
        proveedor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        nit TEXT NOT NULL,
        contacto_nombre TEXT,
        contacto_telefono TEXT,
        contacto_correo TEXT,
        plazo_entrega_dias INTEGER,
        forma_pago TEXT,
        pedido_minimo NUMERIC,
        activo INTEGER NOT NULL DEFAULT 1,
        UNIQUE (empresa_id, nit)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS proveedor_producto (
        proveedor_id INTEGER NOT NULL REFERENCES proveedores (proveedor_id),
        producto_id INTEGER NOT NULL,
        principal INTEGER NOT NULL DEFAULT 0,
        precio_compra NUMERIC,
        activo INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (proveedor_id, producto_id)
    )
    """,
]
