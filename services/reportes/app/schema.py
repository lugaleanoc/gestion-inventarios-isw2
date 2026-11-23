MYSQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS cache_reportes (
        cache_id BIGINT NOT NULL AUTO_INCREMENT,
        empresa_id BIGINT NOT NULL,
        tipo_reporte VARCHAR(40) NOT NULL,
        parametros_hash CHAR(64) NOT NULL,
        datos LONGTEXT NOT NULL,
        fuentes_no_disponibles VARCHAR(255) NOT NULL DEFAULT '',
        generado_en DATETIME NOT NULL,
        expira_en DATETIME NOT NULL,
        PRIMARY KEY (cache_id),
        UNIQUE KEY uq_cache_reporte (empresa_id, tipo_reporte, parametros_hash),
        KEY idx_cache_expira (expira_en)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

SQLITE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS cache_reportes (
        cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        tipo_reporte TEXT NOT NULL,
        parametros_hash TEXT NOT NULL,
        datos TEXT NOT NULL,
        fuentes_no_disponibles TEXT NOT NULL DEFAULT '',
        generado_en TEXT NOT NULL,
        expira_en TEXT NOT NULL,
        UNIQUE (empresa_id, tipo_reporte, parametros_hash)
    )
    """,
]
