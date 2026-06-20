# Troubleshooting

## El bot no inicia

1. Ejecuta `./gabo status`.
2. Verifica `.env`.
3. Verifica que exista `src/attendance_assistant/storage/horario.json`.
4. Prueba en primer plano con:

```bash
./gabo run
```

## Moodle no marca asistencia

- Confirma que estás dentro de la ventana del horario: 10 minutos antes y 30 minutos después del inicio de clase.
- Revisa si Moodle cambió el texto o selectores del módulo de asistencia.
- Prueba `HEADLESS_MODE=False` para ver el navegador.

## No aparecen capturas en el dashboard

Las capturas solo se generan cuando Moodle confirma una asistencia marcada. Si la asistencia no estaba disponible, se registra el evento, pero no habrá captura.

## WhatsApp pide QR otra vez

Vuelve a ejecutar:

```bash
PYTHONPATH=src python -m attendance_assistant.whatsapp.setup_whatsapp
```

## El dashboard no carga

Prueba otro puerto:

```bash
./gabo web --port 9000
```

Si aun así no carga, revisa si otro proceso ocupa el puerto.
