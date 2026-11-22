MYSQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS ejemplos (
        ejemplo_id BIGINT NOT NULL AUTO_INCREMENT,
        empresa_id BIGINT NOT NULL,
        nombre VARCHAR(150) NOT NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        PRIMARY KEY (ejemplo_id),
        KEY idx_ejemplos_empresa (empresa_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

SQLITE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS ejemplos (
        ejemplo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1
    )
    """,
]
