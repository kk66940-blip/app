import reflex as rx

config = rx.Config(
    app_name="rab_opname_web",
    app_module="app.app",   # <-- ini penting
    frontend_port=3000,
    backend_port=8000,
)