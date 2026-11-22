from datetime import datetime, timedelta, timezone


def ahora():
    return datetime.now(timezone.utc)


def para_bd(momento):
    return momento.strftime("%Y-%m-%d %H:%M:%S")


def iso(momento):
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


def desde_epoch(segundos):
    return datetime.fromtimestamp(segundos, tz=timezone.utc)


def en_minutos(minutos):
    return ahora() + timedelta(minutes=minutos)
