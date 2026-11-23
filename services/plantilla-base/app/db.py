import sqlite3

from flask import current_app, g

from .schema import MYSQL_DDL, SQLITE_DDL


class DBNoDisponible(Exception):
    pass


def errores_integridad():
    errores = [sqlite3.IntegrityError]
    try:
        import pymysql

        errores.append(pymysql.err.IntegrityError)
    except ImportError:
        pass
    return tuple(errores)


def _conectar(cfg):
    if cfg["driver"] == "sqlite":
        conn = sqlite3.connect(cfg["path"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    import pymysql

    try:
        return pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["name"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=5,
        )
    except pymysql.MySQLError as exc:
        raise DBNoDisponible(str(exc)) from exc


class Conexion:
    def __init__(self, conn, driver):
        self.conn = conn
        self.driver = driver

    def _sql(self, sql):
        return sql.replace("%s", "?") if self.driver == "sqlite" else sql

    def filas(self, sql, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(self._sql(sql), tuple(params))
            return [dict(fila) for fila in cur.fetchall()]
        finally:
            cur.close()

    def fila(self, sql, params=()):
        filas = self.filas(sql, params)
        return filas[0] if filas else None

    def ejecutar(self, sql, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(self._sql(sql), tuple(params))
            return cur.lastrowid
        finally:
            cur.close()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def cerrar(self):
        self.conn.close()


def get_db():
    if "db" not in g:
        cfg = current_app.config["DB"]
        g.db = Conexion(_conectar(cfg), cfg["driver"])
    return g.db


def cerrar_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.cerrar()


def crear_tablas(cfg):
    ddl = SQLITE_DDL if cfg["driver"] == "sqlite" else MYSQL_DDL
    conn = _conectar(cfg)
    try:
        cur = conn.cursor()
        for sentencia in ddl:
            cur.execute(sentencia)
        cur.close()
        conn.commit()
    except Exception as exc:
        if cfg["driver"] == "sqlite":
            raise
        raise DBNoDisponible(str(exc)) from exc
    finally:
        conn.close()
