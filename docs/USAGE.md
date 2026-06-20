# Uso operativo de Attendance Assistant

Esta guía resume qué comando usar según lo que quieras hacer.

## Arranque rápido

```bash
source .venv/bin/activate
./gabo status
./gabo start
./gabo web
```

## Modos de operación

### GUI

Útil para configuración inicial, cargar horario y operar sin recordar comandos.

```bash
PYTHONPATH=src python src/gui/app.py
```

### CLI

Útil para uso diario y automatización.

```bash
./gabo start
./gabo stop
./gabo status
```

### Dashboard web

Útil para revisar resumen diario y avance del semestre.

```bash
./gabo web
```

Luego abre `http://127.0.0.1:8765`.

## Cuándo usar cada comando

| Situación | Comando recomendado |
| --- | --- |
| Quiero saber si el bot está corriendo | `./gabo status` |
| Quiero dejar el bot activo durante el día | `./gabo start` |
| Quiero apagar el bot | `./gabo stop` |
| Quiero ver logs en terminal mientras corre | `./gabo run` |
| Quiero probar Moodle una vez | `./gabo check-now` |
| Quiero cargar/cambiar horario | `./gabo schedule horario.json` |
| Quiero ver resumen y capturas | `./gabo web` |

## Recomendación de uso

Para uso normal, inicia el bot una vez al día con `./gabo start` y revisa el dashboard con `./gabo web`. Usa `./gabo run` solo para depurar porque se queda ocupando la terminal.
