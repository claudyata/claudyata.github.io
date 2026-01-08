"""
Tab 0 - Validación de Infraestructura

Terminal de validación de tareas INFRA con comandos ejecutables
Autor: Pedro José García Fernández
"""

import streamlit as st
import subprocess
import os
from pathlib import Path
from datetime import datetime


# =========================
# Helpers
# =========================

SAFE_TIMEOUT_SEC = 20
MAX_HISTORY_TERMINAL = 12

def run_cmd(cmd: str, cwd: str):
    """Ejecuta un comando y devuelve (returncode, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=SAFE_TIMEOUT_SEC,
            cwd=cwd
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, (output.strip() if output.strip() else "(sin salida)")
    except subprocess.TimeoutExpired:
        return 124, f"⏱️ Timeout ({SAFE_TIMEOUT_SEC}s)"
    except Exception as e:
        return 1, f"❌ Error: {e}"


def status_badge(code: int):
    if code == 0:
        return "🟢", "✅ OK"
    if code == 124:
        return "🟠", "⏱️ Timeout"
    return "🔴", "❌ Error"


def add_history(cmd: str, cwd: str, code: int, output: str):
    st.session_state.infra_history.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "dir": cwd,
        "cmd": cmd,
        "output": output,
        "code": code
    })


def render_quick_check(title: str, cmd: str, help_text: str = ""):
    """Bloque pequeño de validación con botón y resultado."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if help_text:
            st.caption(help_text)

        colA, colB = st.columns([1, 2])
        with colA:
            run = st.button("▶ Ejecutar", key=f"quick_{title}")
        with colB:
            placeholder = st.empty()

        if run:
            cwd = st.session_state.current_dir
            code, out = run_cmd(cmd, cwd)
            add_history(cmd, cwd, code, out)

            dot, label = status_badge(code)
            # Enseñamos un resumen corto y el detalle en expander
            placeholder.markdown(f"{dot} **{label}** — `{cmd}`")
            with st.expander("Ver salida"):
                st.code(out, language="bash")


# =========================
# Main
# =========================

def render(ctx):
    st.header("Épico 10: Infraestructura y Setup")

    # Estado inicial
    if "infra_history" not in st.session_state:
        st.session_state.infra_history = []
    if "current_dir" not in st.session_state:
        st.session_state.current_dir = str(Path.home())

    # Barra superior
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.info(f"📁 **Directorio actual:** `{st.session_state.current_dir}`")
    with col2:
        if st.button("🏠 Home", key="btn_home_infra"):
            st.session_state.current_dir = str(Path.home())
            st.rerun()
    with col3:
        if st.button("🧹 Limpiar pantalla", key="btn_clear_screen"):
            # no borra historial, solo evita "ruido"
            st.session_state.infra_screen_only = True
            st.rerun()
    with col4:
        if st.button("🗑️ Limpiar historial", key="btn_clear_infra"):
            st.session_state.infra_history = []
            st.rerun()

    st.markdown("---")

    # Modo demo vs avanzado
    mode = st.radio(
        "Modo",
        ["🎬 Demo", "🧪 Shell"],
        horizontal=True
    )

    # =========================
    # MODO DEMO: 5 checks clave
    # =========================
    if mode.startswith("🎬"):
        st.subheader("Validaciones rápidas")

        c1, c2, c3 = st.columns(3)
        with c1:
            render_quick_check(
                "INFRA-10 · Jetson detectado",
                "cat /proc/device-tree/model",
                "Verifica el hardware real (Jetson AGX Orin)."
            )
        with c2:
            render_quick_check(
                "INFRA-20 · CUDA disponible",
                "nvcc --version | head -n 5",
                "Confirma toolchain CUDA (JetPack)."
            )
        with c3:
            render_quick_check(
                "INFRA-30 · Ollama OK",
                "ollama --version",
                "Servicio/model runtime local."
            )

        c4, c5, c6 = st.columns(3)
        with c4:
            render_quick_check(
                "INFRA-30 · Modelos instalados",
                "ollama list | head -n 20",
                "Lista corta para no saturar pantalla."
            )
        with c5:
            render_quick_check(
                "INFRA-40 · MinIO activo",
                "systemctl is-active minio",
                "Data Lake local (Medallion)."
            )
        with c6:
            render_quick_check(
                "INFRA-50 · GPU estado",
                "timeout 2s tegrastats --interval 500",
                "Snapshot rápido de uso real en Jetson."
            )

        st.markdown("---")
        st.caption("💡 Tip demo: ejecuta 3 checks (Jetson/CUDA/Ollama) y enlaza con que el sistema está listo para RAG.")

    # =========================
    # MODO AVANZADO: tu terminal
    # =========================
    else:
        st.subheader("Terminal de validación (modo avanzado)")

        with st.form(key="infra_command_form", clear_on_submit=True):
            colA, colB = st.columns([5, 1])
            with colA:
                comando = st.text_input(
                    "Comando:",
                    placeholder="Ej: uname -m, systemctl status minio, ollama list",
                    label_visibility="collapsed"
                )
            with colB:
                ejecutar = st.form_submit_button("▶️ Ejecutar", use_container_width=True, type="primary")

        comando_ejecutar = comando if ejecutar and comando else None

        if comando_ejecutar:
            # Manejar cd
            if comando_ejecutar.strip().startswith("cd "):
                new_dir = comando_ejecutar.strip()[3:].strip()
                if new_dir.startswith("~"):
                    new_dir = str(Path.home()) + new_dir[1:]
                elif new_dir == "":
                    new_dir = str(Path.home())
                if not new_dir.startswith("/"):
                    new_dir = os.path.join(st.session_state.current_dir, new_dir)
                new_dir = os.path.normpath(new_dir)

                if os.path.isdir(new_dir):
                    st.session_state.current_dir = new_dir
                    add_history(comando_ejecutar, st.session_state.current_dir, 0, f"📁 Cambiado a: {new_dir}")
                else:
                    add_history(comando_ejecutar, st.session_state.current_dir, 1, f"❌ Directorio no encontrado: {new_dir}")

            else:
                cwd = st.session_state.current_dir
                code, out = run_cmd(comando_ejecutar, cwd)
                add_history(comando_ejecutar, cwd, code, out)

            st.rerun()

    # =========================
    # OUTPUT "terminal" principal
    # =========================
    st.markdown("---")
    st.markdown("### 📺 Output")

    history = st.session_state.infra_history
    if history:
        show_last = history[-MAX_HISTORY_TERMINAL:]
        terminal_content = ""
        for entry in show_last:
            dot, _ = status_badge(entry["code"])
            prompt = f"{dot} claudia@jetson:{entry['dir']}$"
            terminal_content += f"{prompt} {entry['cmd']}\n{entry['output']}\n\n"

        st.code(terminal_content, language="bash")

        # ✅ SOLUCIÓN: Historial completo SIN expanders anidados
        with st.expander(f"📜 Historial completo ({len(history)} comandos)"):
            for i, entry in enumerate(reversed(history), start=1):
                dot, label = status_badge(entry["code"])
                st.markdown(f"**#{len(history)-i+1}** · {entry['time']} · {dot} {label}")
                st.code(f"{entry['dir']}$ {entry['cmd']}", language="bash")
                
                # ✅ CAMBIO: Usar checkbox en lugar de expander anidado
                show_output = st.checkbox(
                    "Mostrar salida completa",
                    key=f"show_output_infra_{i}",
                    value=False
                )
                
                if show_output:
                    st.code(entry["output"], language="bash")
                
                st.markdown("---")

    else:
        st.info("👋 Ejecuta validaciones para registrar resultados aquí.")

    # =========================
    # INFO final
    # =========================
    st.markdown("---")
    with st.expander("ℹ️ Tareas INFRA Completadas"):
        st.markdown("""
| Código | Título | Estado |
|--------|--------|--------|
| 🔍 INFRA-10 | Requisitos y validación de hardware | ✅ Finalizado |
| 🐧 INFRA-20 | JetPack 6, CUDA, cuDNN | ✅ Finalizado |
| 🐳 INFRA-30 | Docker + Ollama + Python/Jupyter | ✅ Finalizado |
| 🗄️ INFRA-40 | Data Lake local (MinIO + Medallion) | ✅ Finalizado |
| 🎮 INFRA-50 | Validación rendimiento GPU | ✅ Finalizado |
""")