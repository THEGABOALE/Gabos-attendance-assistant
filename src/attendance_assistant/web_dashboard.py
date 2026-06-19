import html
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from attendance_assistant.config.settings import config
from attendance_assistant.core.reporting import build_dashboard_data


def _badge(status: str) -> str:
    labels = {
        "marked": "✅ Marcada",
        "not_available": "⚠️ No disponible",
        "error": "❌ Error",
    }
    return labels.get(status, status)


def render_dashboard() -> str:
    data = build_dashboard_data()
    courses = "".join(
        f"""
        <tr>
            <td>{html.escape(row['name'])}</td>
            <td>{row['marked']}</td>
            <td>{row['scheduled_so_far']}</td>
            <td>{row['scheduled_total']}</td>
            <td>{'N/A' if row['percentage'] is None else str(row['percentage']) + '%'}</td>
        </tr>
        """
        for row in data["courses"]
    ) or "<tr><td colspan='5'>Todavía no hay datos del semestre.</td></tr>"

    today_events = "".join(
        f"""
        <article class="event">
            <div><strong>{html.escape(event.get('course', ''))}</strong> <span>{_badge(event.get('status', ''))}</span></div>
            <small>{html.escape(event.get('timestamp', ''))}</small>
            <p>{html.escape(event.get('message', ''))}</p>
            {_screenshot_link(event)}
        </article>
        """
        for event in data["today_events"]
    ) or "<p class='muted'>Aún no hay revisiones registradas hoy.</p>"

    recent_events = "".join(
        f"<li><strong>{html.escape(event.get('date', ''))}</strong> · {html.escape(event.get('course', ''))} · {_badge(event.get('status', ''))}</li>"
        for event in data["recent_events"][:12]
    ) or "<li>No hay historial reciente.</li>"

    return f"""<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="60">
    <title>Attendance Assistant · Resumen</title>
    <style>
        :root {{ color-scheme: dark; font-family: Inter, system-ui, -apple-system, sans-serif; }}
        body {{ margin: 0; background: #020617; color: #e5e7eb; }}
        main {{ max-width: 1100px; margin: 0 auto; padding: 32px; }}
        header {{ display: flex; justify-content: space-between; gap: 16px; align-items: start; margin-bottom: 24px; }}
        h1 {{ margin: 0; font-size: 34px; }}
        .muted {{ color: #94a3b8; }}
        .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 24px 0; }}
        .card, .event, table {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 18px; box-shadow: 0 20px 60px #0005; }}
        .card {{ padding: 18px; }}
        .card b {{ display: block; font-size: 30px; margin-top: 8px; }}
        section {{ margin-top: 28px; }}
        table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
        th, td {{ text-align: left; padding: 14px 16px; border-bottom: 1px solid #1e293b; }}
        th {{ color: #93c5fd; background: #111827; }}
        .event {{ padding: 16px; margin-bottom: 12px; }}
        .event span {{ color: #86efac; margin-left: 8px; }}
        a {{ color: #93c5fd; }}
        @media (max-width: 850px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} header {{ display: block; }} }}
    </style>
</head>
<body>
<main>
    <header>
        <div>
            <h1>Attendance Assistant</h1>
            <p class="muted">Resumen local de Moodle/UAM Virtual. Actualiza automáticamente cada 60 segundos.</p>
        </div>
        <div class="muted">Generado: {html.escape(data['generated_at'])}<br>Semestre: {data['semester']['start']} → {data['semester']['end']}</div>
    </header>

    <div class="grid">
        <div class="card">Asistencias marcadas<b>{data['totals']['marked']}</b></div>
        <div class="card">Sesiones hasta hoy<b>{data['totals']['scheduled_so_far']}</b></div>
        <div class="card">Sesiones del semestre<b>{data['totals']['scheduled_total']}</b></div>
        <div class="card">Cursos monitoreados<b>{data['totals']['courses']}</b></div>
    </div>

    <section>
        <h2>Hoy</h2>
        {today_events}
    </section>

    <section>
        <h2>Progreso por materia</h2>
        <table>
            <thead><tr><th>Materia</th><th>Marcadas</th><th>Esperadas hasta hoy</th><th>Total semestre</th><th>% estimado</th></tr></thead>
            <tbody>{courses}</tbody>
        </table>
    </section>

    <section>
        <h2>Historial reciente</h2>
        <ul>{recent_events}</ul>
    </section>
</main>
</body>
</html>"""


def _screenshot_link(event: dict) -> str:
    screenshot = event.get("screenshot")
    if not screenshot:
        return ""
    href = "/file/" + html.escape(screenshot)
    return f'<p><a href="{href}" target="_blank" rel="noreferrer">Ver captura de confirmación</a></p>'


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_html(render_dashboard())
            return
        if parsed.path == "/api/summary":
            self._send_json(build_dashboard_data())
            return
        if parsed.path.startswith("/file/"):
            self._send_file(parsed.path.removeprefix("/file/"))
            return
        self.send_error(404, "Ruta no encontrada")

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, content: str) -> None:
        payload = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, relative_path: str) -> None:
        requested = (config.BASE_DIR / unquote(relative_path)).resolve()
        screenshots_root = config.SCREENSHOTS_DIR.resolve()
        if not requested.is_file() or screenshots_root not in requested.parents:
            self.send_error(404, "Archivo no encontrado")
            return

        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        payload = requested.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Dashboard disponible en http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard detenido.")
    finally:
        server.server_close()
