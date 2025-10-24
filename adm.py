import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ==========================
# FUNCIÓN PRINCIPAL DEL PANEL
# ==========================
def abrir_panel_admin():
    for widget in root.winfo_children():
        widget.destroy()

    root.title("Panel de Administración")
    root.geometry("900x500")
    root.configure(bg="#2C2F33")

    # ======== FRAME SUPERIOR ========
    top_frame = tk.Frame(root, bg="#23272A", height=60)
    top_frame.pack(fill="x")

    lbl_logo = tk.Label(top_frame, text="🏢 TecnoStore", bg="#23272A", fg="white", font=("Segoe UI", 12, "bold"))
    lbl_logo.place(x=15, y=18)

    def actualizar_hora():
        hora_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        lbl_fecha.config(text=hora_actual)
        lbl_fecha.after(1000, actualizar_hora)

    lbl_fecha = tk.Label(top_frame, bg="#23272A", fg="#99AAB5", font=("Segoe UI", 10))
    lbl_fecha.place(x=650, y=20)
    actualizar_hora()

    btn_logout = ttk.Button(top_frame, text="Cerrar sesión", command=volver_a_login)
    btn_logout.place(x=780, y=18)

    # ======== FRAME IZQUIERDO (MENÚ) ========
    side_frame = tk.Frame(root, bg="#2C2F33", width=180)
    side_frame.pack(fill="y", side="left")

    main_frame = tk.Frame(root, bg="#40444B")
    main_frame.pack(fill="both", expand=True)

    # ======== FUNCIONES DE CONTENIDO ========

    def mostrar_bienvenida():
        for w in main_frame.winfo_children():
            w.destroy()
        lbl_bienvenida = tk.Label(
            main_frame,
            text="Bienvenido al panel del administrador 👋",
            bg="#40444B", fg="white", font=("Segoe UI", 14, "bold")
        )
        lbl_bienvenida.pack(pady=40)

    def mostrar_consulta_tareas():
        for w in main_frame.winfo_children():
            w.destroy()

        lbl_titulo = tk.Label(main_frame, text="📋 Consulta de Tareas", bg="#40444B", fg="white", font=("Segoe UI", 13, "bold"))
        lbl_titulo.pack(pady=20)

        frame_form = tk.Frame(main_frame, bg="#40444B")
        frame_form.pack(pady=10)

        # Tipo de consulta
        lbl_tipo = tk.Label(frame_form, text="Tipo de consulta:", bg="#40444B", fg="white", font=("Segoe UI", 11))
        lbl_tipo.grid(row=0, column=0, sticky="e", padx=5, pady=5)

        combo_tipo = ttk.Combobox(frame_form, values=["Usuario", "ID Usuario", "Nombre Usuario"], width=25)
        combo_tipo.grid(row=0, column=1, padx=5, pady=5)
        combo_tipo.set("Usuario")

        # Fecha desde
        lbl_desde = tk.Label(frame_form, text="Fecha desde:", bg="#40444B", fg="white", font=("Segoe UI", 11))
        lbl_desde.grid(row=1, column=0, sticky="e", padx=5, pady=5)

        entry_desde = ttk.Entry(frame_form, width=28)
        entry_desde.grid(row=1, column=1, padx=5, pady=5)
        entry_desde.insert(0, "dd/mm/aaaa")

        # Fecha hasta
        lbl_hasta = tk.Label(frame_form, text="Fecha hasta:", bg="#40444B", fg="white", font=("Segoe UI", 11))
        lbl_hasta.grid(row=2, column=0, sticky="e", padx=5, pady=5)

        entry_hasta = ttk.Entry(frame_form, width=28)
        entry_hasta.grid(row=2, column=1, padx=5, pady=5)
        entry_hasta.insert(0, "dd/mm/aaaa")

        # Botón consultar
        btn_consultar = ttk.Button(frame_form, text="Consultar", command=lambda: messagebox.showinfo("Consulta", "Consulta realizada correctamente"))
        btn_consultar.grid(row=3, column=0, columnspan=2, pady=15)

    def mostrar_prueba2():
        for w in main_frame.winfo_children():
            w.destroy()
        lbl = tk.Label(main_frame, text="📊 Aquí irá el módulo 2", bg="#40444B", fg="white", font=("Segoe UI", 13))
        lbl.pack(pady=40)

    def mostrar_prueba3():
        for w in main_frame.winfo_children():
            w.destroy()
        lbl = tk.Label(main_frame, text="⚙️ Configuración (en desarrollo)", bg="#40444B", fg="white", font=("Segoe UI", 13))
        lbl.pack(pady=40)

    # ======== BOTONES DEL MENÚ ========
    menu_items = [
        ("Consulta tareas", mostrar_consulta_tareas),
        ("Prueba 2", mostrar_prueba2),
        ("Prueba 3", mostrar_prueba3)
    ]

    for texto, funcion in menu_items:
        btn = ttk.Button(side_frame, text=texto, command=funcion)
        btn.pack(fill="x", padx=10, pady=8)

    mostrar_bienvenida()


# ==========================
# LOGIN
# ==========================
def verificar_codigo():
    codigo_ingresado = entry_codigo.get().strip()
    codigo_correcto = "0023"
    if codigo_ingresado == codigo_correcto:
        abrir_panel_admin()
    else:
        messagebox.showwarning("Error", "Ingrese código de administrador válido (4 dígitos).")


def volver_a_login():
    for widget in root.winfo_children():
        widget.destroy()
    crear_login()


def crear_login():
    root.title("Login Administrador")
    root.geometry("400x250")
    root.configure(bg="#2C2F33")

    lbl_titulo = ttk.Label(root, text="🔒 Acceso de Administrador", font=("Segoe UI", 14, "bold"))
    lbl_titulo.pack(pady=30)

    lbl_codigo = ttk.Label(root, text="Ingrese su código de acceso:")
    lbl_codigo.pack()

    global entry_codigo
    entry_codigo = ttk.Entry(root, width=20, justify="center", font=("Segoe UI", 11))
    entry_codigo.pack(pady=10)
    entry_codigo.focus()

    btn_verificar = ttk.Button(root, text="Verificar", command=verificar_codigo)
    btn_verificar.pack(pady=15)


# ==========================
# INICIO DEL PROGRAMA
# ==========================
root = tk.Tk()
style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", background="#7289DA", foreground="white", font=("Segoe UI", 10, "bold"))
style.map("TButton", background=[("active", "#5B6EAE")])

crear_login()
root.mainloop()
