import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyodbc
import os
import re
from ttkthemes import ThemedTk

class AutocompleteCombobox(ttk.Combobox):
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=str.lower)
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        self['values'] = self._completion_list

    def autocomplete(self, delta=0):
        if delta:
            self.delete(self.position, tk.END)
        else:
            self.position = len(self.get())

        hits = [elem for elem in self._completion_list if elem.lower().startswith(self.get().lower())]

        if hits != self._hits:
            self._hit_index = 0
            self._hits = hits

        if hits:
            self.delete(0, tk.END)
            self.insert(0, hits[self._hit_index])
            self.select_range(self.position, tk.END)

    def handle_keyrelease(self, event):
        if event.keysym in ("BackSpace", "Left", "Right", "Up", "Down", "Shift_L", "Shift_R"):
            return
        self.autocomplete()

class ModernSQLViewGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Vistas SQL")
        self.root.geometry("1400x900")
        
        # Configurar tema moderno
        self.style = ttk.Style()
        self.style.theme_use('arc')  # Tema oscuro moderno
        self.root.configure(bg='white')
        
        # Colores personalizados
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabel', background='white', foreground='black')
        self.style.configure('TButton', background='#e0e0e0', foreground='black', 
                           borderwidth=1, focusthickness=3, focuscolor='none')
        self.style.map('TButton', background=[('active', '#d0d0d0')])
        self.style.configure('TEntry', fieldbackground='#f0f0f0', foreground='black')
        self.style.configure('TCombobox', fieldbackground='#f0f0f0', foreground='black')
        self.style.configure('Treeview', background='#f0f0f0', foreground='black', 
                           fieldbackground='#f0f0f0')
        self.style.configure('Treeview.Heading', background='#e0e0e0', foreground='black')
        self.style.map('Treeview', background=[('selected', '#0078D7')])
        self.style.configure('TNotebook', background='white', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#e0e0e0', foreground='black',
                           padding=[10, 5], borderwidth=0)
        self.style.map('TNotebook.Tab', background=[('selected', '#0078D7')])
        
        self.connection = None
        self.cursor = None
        self.main_tables = []
        self.related_tables = []
        self.existing_views = []

        self.current_fact_table = None
        self.selected_joins = []
        self.view_name = ""
        self.generated_sql = ""
        self.editing_mode = False

        self.setup_ui()

    def setup_ui(self):
        # Frame principal con padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Pestañas
        self.connection_frame = ttk.Frame(notebook)
        self.builder_frame = ttk.Frame(notebook)
        self.scripts_frame = ttk.Frame(notebook)
        self.editor_frame = ttk.Frame(notebook)

        notebook.add(self.connection_frame, text="🔌 Conexión")
        notebook.add(self.builder_frame, text="🛠 Constructor")
        notebook.add(self.scripts_frame, text="📜 SQL Generado")
        notebook.add(self.editor_frame, text="✏️ Editor")

        self.setup_connection_tab()
        self.setup_builder_tab()
        self.setup_scripts_tab()
        self.setup_editor_tab()

    def setup_connection_tab(self):
        # Frame con padding interno
        frame = ttk.Frame(self.connection_frame, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title = ttk.Label(frame, text="Conexión a SQL Server", font=('Helvetica', 14, 'bold'))
        title.pack(pady=(0, 20))

        # Campos de conexión en un grid
        conn_grid = ttk.Frame(frame)
        conn_grid.pack(fill=tk.X, pady=5)
        
        ttk.Label(conn_grid, text="Servidor:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.server_entry = ttk.Entry(conn_grid, width=40)
        self.server_entry.grid(row=0, column=1, sticky="w", pady=5)
        
        ttk.Label(conn_grid, text="Base de Datos:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.database_entry = ttk.Entry(conn_grid, width=40)
        self.database_entry.grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(conn_grid, text="Usuario:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.user_entry = ttk.Entry(conn_grid, width=40)
        self.user_entry.grid(row=2, column=1, sticky="w", pady=5)
        
        ttk.Label(conn_grid, text="Contraseña:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.password_entry = ttk.Entry(conn_grid, width=40, show="*")
        self.password_entry.grid(row=3, column=1, sticky="w", pady=5)

        # Botón de conexión centrado
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Conectar", command=self.connect_database).pack(pady=10)
        
        # Estado de conexión
        self.connection_status = ttk.Label(frame, text="🔴 Desconectado", foreground="#ff6b6b")
        self.connection_status.pack()

    def setup_builder_tab(self):
        main_frame = ttk.Frame(self.builder_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configuración del grid
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)

        # Panel izquierdo - Tabla Principal
        left_panel = ttk.LabelFrame(main_frame, text=" Tabla Principal ", padding=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(left_panel, text="Tabla Principal:").pack(anchor="w")
        self.main_combo = ttk.Combobox(left_panel, state="readonly")
        self.main_combo.pack(fill=tk.X, pady=(0, 10))
        self.main_combo.bind("<<ComboboxSelected>>", self.load_fact_columns)

        ttk.Label(left_panel, text="Columnas:").pack(anchor="w")
        self.main_columns_tree = ttk.Treeview(left_panel, columns=("column", "include"), 
                                            show="headings", height=15, selectmode="none")
        self.main_columns_tree.heading("column", text="Columna")
        self.main_columns_tree.heading("include", text="Incluir")
        self.main_columns_tree.column("column", width=150)
        self.main_columns_tree.column("include", width=50, anchor="center")
        self.main_columns_tree.pack(fill=tk.BOTH, expand=True)
        
        self.main_columns_tree.tag_configure("checked", foreground="#4CAF50")  # Verde
        self.main_columns_tree.tag_configure("unchecked", foreground="#757575")  # Gris
        self.main_columns_tree.bind("<Button-1>", self.on_fact_column_click)

        # Panel central - Configuración de Joins
        center_panel = ttk.LabelFrame(main_frame, text=" Configurar Join ", padding=10)
        center_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        ttk.Label(center_panel, text="Tabla Relacionada:").pack(anchor="w")
        self.related_combo = AutocompleteCombobox(center_panel)
        self.related_combo.pack(fill=tk.X, pady=(0, 10))
        self.related_combo.bind("<<ComboboxSelected>>", self.load_related_columns)

        ttk.Label(center_panel, text="FK en Principal:").pack(anchor="w")
        self.main_fk_combo = ttk.Combobox(center_panel, state="readonly")
        self.main_fk_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(center_panel, text="PK en Relacionada:").pack(anchor="w")
        self.related_pk_combo = ttk.Combobox(center_panel, state="readonly")
        self.related_pk_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(center_panel, text="Columna Relacionada:").pack(anchor="w")
        self.related_col_combo = ttk.Combobox(center_panel, state="readonly")
        self.related_col_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(center_panel, text="Alias de Columna:").pack(anchor="w")
        self.col_alias_entry = ttk.Entry(center_panel)
        self.col_alias_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(center_panel, text="➕ Agregar a Vista", command=self.add_join).pack(fill=tk.X, pady=10)

        # Panel derecho - Joins configurados
        right_panel = ttk.LabelFrame(main_frame, text=" Joins Configurados ", padding=10)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        self.join_tree = ttk.Treeview(right_panel, columns=("related_table", "main_fk", "related_pk", "related_col", "col_alias"), 
                                    show="headings", height=15)
        self.join_tree.heading("related_table", text="Tabla Relacionada")
        self.join_tree.heading("main_fk", text="FK Fact")
        self.join_tree.heading("related_pk", text="PK Dim")
        self.join_tree.heading("related_col", text="Columna")
        self.join_tree.heading("col_alias", text="Alias")
        
        for col in ("related_table", "main_fk", "related_pk", "related_col", "col_alias"):
            self.join_tree.column(col, width=100, stretch=True)
            
        self.join_tree.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(right_panel, text="🗑️ Eliminar Selección", command=self.remove_join).pack(fill=tk.X, pady=(10, 0))

        # Panel inferior - Nombre de vista y acciones
        bottom_panel = ttk.Frame(main_frame)
        bottom_panel.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        ttk.Label(bottom_panel, text="Nombre de la Vista:").pack(side=tk.LEFT, padx=(0, 10))
        self.view_name_entry = ttk.Entry(bottom_panel, width=40)
        self.view_name_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Button(bottom_panel, text="💾 Crear Vista", command=self.create_view).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_panel, text="📂 Cargar Vista", command=self.load_existing_view).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_panel, text="🔄 Nueva Vista", command=self.reset_builder_view).pack(side=tk.LEFT, padx=5)

    def setup_scripts_tab(self):
        main_frame = ttk.Frame(self.scripts_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Editor SQL con scrollbar
        frame = ttk.Frame(main_frame)
        frame.pack(fill=tk.BOTH, expand=True)
        
        scroll_y = ttk.Scrollbar(frame)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scroll_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.sql_text = tk.Text(frame, wrap=tk.NONE, font=('Consolas', 10), 
                              yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set,
                              bg='#f0f0f0', fg='black', insertbackground='black')
        self.sql_text.pack(fill=tk.BOTH, expand=True)
        
        scroll_y.config(command=self.sql_text.yview)
        scroll_x.config(command=self.sql_text.xview)
        
        # Botones de acción
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="📋 Copiar SQL", command=self.copy_sql).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 Guardar SQL", command=self.save_sql_file).pack(side=tk.LEFT, padx=5)

    def setup_editor_tab(self):
        main_frame = ttk.Frame(self.editor_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel superior - Selección de vista
        top_panel = ttk.Frame(main_frame)
        top_panel.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_panel, text="Vista a editar:").pack(side=tk.LEFT, padx=(0, 10))
        self.view_combo = ttk.Combobox(top_panel, width=40, state="readonly")
        self.view_combo.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(top_panel, text="📂 Cargar Vista", command=self.load_view_for_editing).pack(side=tk.LEFT)
        
        # Panel principal - Editor
        editor_panel = ttk.Frame(main_frame)
        editor_panel.pack(fill=tk.BOTH, expand=True)
        
        # Columnas de Fact
        fact_panel = ttk.LabelFrame(editor_panel, text=" Columnas de Fact ", padding=10)
        fact_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.edit_main_columns_tree = ttk.Treeview(fact_panel, columns=("column", "include"), 
                                                 show="headings", height=20, selectmode="none")
        self.edit_main_columns_tree.heading("column", text="Columna")
        self.edit_main_columns_tree.heading("include", text="Incluir")
        self.edit_main_columns_tree.column("column", width=200)
        self.edit_main_columns_tree.column("include", width=60, anchor="center")
        self.edit_main_columns_tree.pack(fill=tk.BOTH, expand=True)
        
        self.edit_main_columns_tree.tag_configure("checked", foreground="#4CAF50")
        self.edit_main_columns_tree.tag_configure("unchecked", foreground="#757575")
        self.edit_main_columns_tree.bind("<Button-1>", self.on_edit_fact_column_click)
        
        # Columnas de Dimensiones
        dim_panel = ttk.LabelFrame(editor_panel, text=" Columnas de Dimensiones ", padding=10)
        dim_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.edit_related_columns_tree = ttk.Treeview(dim_panel, columns=("column", "include"), 
                                                show="headings", height=20, selectmode="none")
        self.edit_related_columns_tree.heading("column", text="Columna")
        self.edit_related_columns_tree.heading("include", text="Incluir")
        self.edit_related_columns_tree.column("column", width=200)
        self.edit_related_columns_tree.column("include", width=60, anchor="center")
        self.edit_related_columns_tree.pack(fill=tk.BOTH, expand=True)
        
        self.edit_related_columns_tree.tag_configure("checked", foreground="#4CAF50")
        self.edit_related_columns_tree.tag_configure("unchecked", foreground="#757575")
        self.edit_related_columns_tree.bind("<Button-1>", self.on_edit_related_column_click)
        
        # Panel inferior - Nueva dimensión y acciones
        bottom_panel = ttk.Frame(main_frame)
        bottom_panel.pack(fill=tk.X, pady=(10, 0))
        
        # Nueva dimensión
        new_dim_panel = ttk.LabelFrame(bottom_panel, text=" Agregar Nueva Dimensión ", padding=10)
        new_dim_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        dim_grid = ttk.Frame(new_dim_panel)
        dim_grid.pack(fill=tk.X)
        
        ttk.Label(dim_grid, text="Tabla Relacionada:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.new_related_combo = ttk.Combobox(dim_grid, width=20, state="readonly")
        self.new_related_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(dim_grid, text="FK en Principal:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.new_main_fk_combo = ttk.Combobox(dim_grid, width=20, state="readonly")
        self.new_main_fk_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        ttk.Label(dim_grid, text="PK en Relacionada:").grid(row=0, column=4, sticky="e", padx=5, pady=2)
        self.new_related_pk_combo = ttk.Combobox(dim_grid, width=20, state="readonly")
        self.new_related_pk_combo.grid(row=0, column=5, sticky="w", padx=5, pady=2)
        
        ttk.Label(dim_grid, text="Columna:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.new_related_col_combo = ttk.Combobox(dim_grid, width=20, state="readonly")
        self.new_related_col_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(dim_grid, text="Alias:").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        self.new_col_alias_entry = ttk.Entry(dim_grid, width=20)
        self.new_col_alias_entry.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        ttk.Button(dim_grid, text="➕ Agregar", command=self.add_new_dim_field).grid(row=1, column=4, columnspan=2, padx=10, pady=2)
        
        # Acciones SQL
        sql_actions_panel = ttk.Frame(bottom_panel)
        sql_actions_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(sql_actions_panel, text="🔄 Actualizar Vista", command=self.update_view).pack(fill=tk.X, pady=5)
        ttk.Button(sql_actions_panel, text="⚡ Generar SQL", command=self.generate_edited_sql).pack(fill=tk.X, pady=5)
        
        # Editor SQL
        sql_editor_panel = ttk.LabelFrame(bottom_panel, text=" SQL Generado ", padding=10)
        sql_editor_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        scroll_y = ttk.Scrollbar(sql_editor_panel)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scroll_x = ttk.Scrollbar(sql_editor_panel, orient=tk.HORIZONTAL)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.edit_sql_text = tk.Text(sql_editor_panel, wrap=tk.NONE, font=('Consolas', 10), 
                                   height=8, yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set,
                                   bg='#f0f0f0', fg='black', insertbackground='black')
        self.edit_sql_text.pack(fill=tk.BOTH, expand=True)
        
        scroll_y.config(command=self.edit_sql_text.yview)
        scroll_x.config(command=self.edit_sql_text.xview)

    
    def connect_database(self):
        try:
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server_entry.get()};DATABASE={self.database_entry.get()};UID={self.user_entry.get()};PWD={self.password_entry.get()}"
            self.connection = pyodbc.connect(conn_str)
            self.cursor = self.connection.cursor()
            self.connection_status.config(text="🟢 Conectado", foreground="#4CAF50")

            # Load tables
            self.cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
            tables = [r[0] for r in self.cursor.fetchall()]
            self.main_tables = tables
            self.related_tables = tables
            self.main_combo['values'] = tables
            self.related_combo.set_completion_list(tables)
            self.new_related_combo['values'] = tables

            # Load views
            self.cursor.execute("SELECT name FROM sys.views")
            self.existing_views = [r[0] for r in self.cursor.fetchall()]
            self.view_combo['values'] = self.existing_views

        except Exception as e:
            messagebox.showerror("Error de conexión", str(e))

    def get_columns(self, table):
        self.cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}'")
        return [r[0] for r in self.cursor.fetchall()]

    def load_fact_columns(self, _):
        self.current_fact_table = self.main_combo.get()
        columns = self.get_columns(self.current_fact_table)
        self.main_fk_combo['values'] = columns
        self.new_main_fk_combo['values'] = columns
        
        # Load columns into the treeview
        self.main_columns_tree.delete(*self.main_columns_tree.get_children())
        for col in columns:
            self.main_columns_tree.insert("", "end", values=(col, "✓"), tags=("checked",))

    def load_related_columns(self, _):
        related_table = self.related_combo.get()
        columns = self.get_columns(related_table)
        self.related_pk_combo['values'] = columns
        self.related_col_combo['values'] = columns

    def on_fact_column_click(self, event):
        region = self.main_columns_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.main_columns_tree.identify_column(event.x)
            item = self.main_columns_tree.identify_row(event.y)
            
            if column == "#2":  # Checkbox column
                current_values = self.main_columns_tree.item(item, "values")
                new_value = " " if current_values[1] == "✓" else "✓"
                self.main_columns_tree.item(item, values=(current_values[0], new_value), 
                                          tags=("checked" if new_value == "✓" else "unchecked",))
                self.generate_sql()

    def add_join(self):
        join = {
            'related_table': self.related_combo.get(),
            'main_fk': self.main_fk_combo.get(),
            'related_pk': self.related_pk_combo.get(),
            'related_col': self.related_col_combo.get(),
            'col_alias': self.col_alias_entry.get() or f"{self.related_combo.get()}_{self.related_col_combo.get()}"
        }
        if not all([join['related_table'], join['main_fk'], join['related_pk'], join['related_col']]):
            messagebox.showwarning("Campos incompletos", "Completa todos los campos para agregar un JOIN")
            return
        self.selected_joins.append(join)
        self.join_tree.insert("", "end", values=(join['related_table'], join['main_fk'], join['related_pk'], join['related_col'], join['col_alias']))
        self.generate_sql()

    def remove_join(self):
        selected_item = self.join_tree.selection()
        if not selected_item:
            return
        index = self.join_tree.index(selected_item)
        self.join_tree.delete(selected_item)
        if index < len(self.selected_joins):
            del self.selected_joins[index]
        self.generate_sql()

    def generate_sql(self):
        if not self.current_fact_table:
            return

        # Obtener columnas seleccionadas de la tabla fact
        fact_columns = []
        for item in self.main_columns_tree.get_children():
            values = self.main_columns_tree.item(item, "values")
            if values[1] == "✓":
                fact_columns.append(f"f.{values[0]}")

        if not fact_columns:
            messagebox.showwarning("Sin columnas", "Selecciona al menos una columna de la tabla fact")
            return

        select_parts = fact_columns
        joins = []

        for i, j in enumerate(self.selected_joins):
            alias = j['related_table'][:3] + str(i)
            related_col = j['related_col']
            col_alias = j.get('col_alias', f"{j['related_table']}_{related_col}")

            # Si el usuario seleccionó '*', expandimos a todas las columnas
            if related_col == "*":
                try:
                    related_cols = self.get_columns(j['related_table'])
                    for col in related_cols:
                        select_parts.append(f"{alias}.{col} AS [{j['related_table']}_{col}]")
                except Exception as e:
                    messagebox.showerror("Error obteniendo columnas", f"No se pudieron obtener las columnas de {j['related_table']}.\n{e}")
                    return
            else:
                select_parts.append(f"{alias}.{related_col} AS [{col_alias}]")

            joins.append(f"LEFT JOIN {j['related_table']} {alias} ON f.{j['main_fk']} = {alias}.{j['related_pk']}")

        self.generated_sql = (
            "SELECT\n    " + ",\n    ".join(select_parts) +
            f"\nFROM {self.current_fact_table} f\n" +
            "\n".join(joins)
        )

        self.sql_text.delete("1.0", tk.END)
        self.sql_text.insert(tk.END, self.generated_sql)

    def reset_builder_view(self):
        self.current_fact_table = None
        self.selected_joins = []
        self.generated_sql = ""
        self.view_name_entry.delete(0, tk.END)

        # Reset Comboboxes
        self.main_combo.set("")
        self.related_combo.set("")
        self.main_fk_combo.set("")
        self.related_pk_combo.set("")
        self.related_col_combo.set("")
        self.col_alias_entry.delete(0, tk.END)

        # Borrar árboles
        self.main_columns_tree.delete(*self.main_columns_tree.get_children())
        self.join_tree.delete(*self.join_tree.get_children())

        # Borrar texto SQL
        self.sql_text.delete("1.0", tk.END)

        messagebox.showinfo("Nueva Vista", "Constructor reiniciado. Puedes comenzar una nueva vista.")

    def create_view(self):
        view_name = self.view_name_entry.get().strip()
        if not view_name:
            messagebox.showerror("Nombre faltante", "Debes ingresar un nombre para la vista")
            return
        if not hasattr(self, 'generated_sql') or not self.generated_sql:
            self.generate_sql()
        create_sql = f"CREATE OR ALTER VIEW {view_name} AS \n{self.generated_sql}"
        try:
            self.cursor.execute(create_sql)
            self.connection.commit()
            messagebox.showinfo("Vista creada", f"La vista '{view_name}' fue creada exitosamente")
            # Refresh views list
            self.cursor.execute("SELECT name FROM sys.views")
            self.existing_views = [r[0] for r in self.cursor.fetchall()]
            self.view_combo['values'] = self.existing_views
        except Exception as e:
            messagebox.showerror("Error al crear vista", str(e))

    def load_existing_view(self):
        view_name = self.view_name_entry.get().strip()
        if not view_name:
            messagebox.showerror("Nombre faltante", "Especifica el nombre de la vista a cargar")
            return
        try:
            self.cursor.execute(f"SELECT definition FROM sys.sql_modules WHERE object_id = OBJECT_ID('{view_name}')")
            row = self.cursor.fetchone()
            if row:
                self.generated_sql = row[0]
                self.sql_text.delete("1.0", tk.END)
                self.sql_text.insert(tk.END, self.generated_sql)
                messagebox.showinfo("Vista cargada", f"Vista '{view_name}' cargada correctamente (solo lectura de SQL).")
            else:
                messagebox.showwarning("No encontrado", "No se encontró la vista especificada.")
        except Exception as e:
            messagebox.showerror("Error al cargar vista", str(e))

    def copy_sql(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.sql_text.get("1.0", tk.END))
        messagebox.showinfo("Copiado", "El SQL ha sido copiado al portapapeles")

    def save_sql_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("SQL Files", "*.sql"), ("All Files", "*.*")],
            title="Guardar SQL como"
        )
        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write(self.sql_text.get("1.0", tk.END))
                messagebox.showinfo("Guardado", f"Archivo guardado en:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error al guardar", str(e))

     # ========== VIEW EDITOR FUNCTIONS ==========
    def load_view_for_editing(self):
        view_name = self.view_combo.get()
        if not view_name:
            messagebox.showwarning("Selección requerida", "Selecciona una vista para editar")
            return
        
        try:
            # Get view definition
            self.cursor.execute(f"SELECT definition FROM sys.sql_modules WHERE object_id = OBJECT_ID('{view_name}')")
            view_def = self.cursor.fetchone()[0]
            
            # Parse the SQL to extract components
            self.parse_view_sql(view_name, view_def)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la vista: {str(e)}")

    def parse_view_sql(self, view_name, sql):
        # Clear previous data
        self.edit_main_columns_tree.delete(*self.edit_main_columns_tree.get_children())
        self.edit_related_columns_tree.delete(*self.edit_related_columns_tree.get_children())
        self.edit_sql_text.delete("1.0", tk.END)
        
        # Extract the FROM clause to find the fact table
        from_match = re.search(r"FROM\s+([^\s]+)\s+f", sql, re.IGNORECASE)
        if not from_match:
            messagebox.showerror("Error", "No se pudo identificar la tabla principal en la vista")
            return
        
        fact_table = from_match.group(1)
        self.current_fact_table = fact_table
        
        # Get all columns from fact table
        fact_columns = self.get_columns(fact_table)
        
        # Parse SELECT clause to find included columns
        select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            messagebox.showerror("Error", "No se pudo analizar la cláusula SELECT")
            return
        
        select_clause = select_match.group(1)
        included_columns = [col.strip() for col in select_clause.split(",")]
        
        # Process fact columns
        for col in fact_columns:
            col_ref = f"f.{col}"
            included = any(col_ref in c or col == c.split()[0] for c in included_columns)
            self.edit_main_columns_tree.insert("", "end", 
                                             values=(col, "✓" if included else " "),
                                             tags=("checked" if included else "unchecked",))
        
        # Parse JOINs to find dimension columns
        join_matches = re.finditer(r"LEFT JOIN\s+([^\s]+)\s+([^\s]+)\s+ON\s+f\.([^\s]+)\s*=\s*\2\.([^\s]+)", sql)
        self.selected_joins = []
        
        for match in join_matches:
            related_table = match.group(1)
            dim_alias = match.group(2)
            main_fk = match.group(3)
            related_pk = match.group(4)
            
            # Find columns from this dimension that are included in SELECT
            related_columns = self.get_columns(related_table)
            for col in related_columns:
                col_ref = f"{dim_alias}.{col}"
                included = any(col_ref in c or f"{related_table}_{col}" in c for c in included_columns)
                if included:
                    # Extract the alias if it exists
                    col_with_alias = next((c for c in included_columns if col_ref in c or f"{related_table}_{col}" in c), None)
                    alias = None
                    if col_with_alias and " AS " in col_with_alias:
                        alias = col_with_alias.split(" AS ")[1].strip()
                    
                    self.edit_related_columns_tree.insert("", "end",
                                                    values=(f"{related_table}.{col}", "✓", alias),
                                                    tags=("checked",))
            
            # Save join information
            self.selected_joins.append({
                'related_table': related_table,
                'main_fk': main_fk,
                'related_pk': related_pk,
                'related_col': '*',
                'alias': dim_alias
            })
        
        self.edit_sql_text.insert(tk.END, sql)
        self.editing_mode = True
        self.view_name_entry.delete(0, tk.END)
        self.view_name_entry.insert(0, view_name)

    def on_edit_fact_column_click(self, event):
        region = self.edit_main_columns_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.edit_main_columns_tree.identify_column(event.x)
            item = self.edit_main_columns_tree.identify_row(event.y)
            
            if column == "#2":  # Checkbox column
                current_values = self.edit_main_columns_tree.item(item, "values")
                new_value = " " if current_values[1] == "✓" else "✓"
                self.edit_main_columns_tree.item(item, values=(current_values[0], new_value), 
                                              tags=("checked" if new_value == "✓" else "unchecked",))

    def on_edit_related_column_click(self, event):
        region = self.edit_related_columns_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.edit_related_columns_tree.identify_column(event.x)
            item = self.edit_related_columns_tree.identify_row(event.y)
            
            if column == "#2":  # Checkbox column
                current_values = self.edit_related_columns_tree.item(item, "values")
                new_value = " " if current_values[1] == "✓" else "✓"
                self.edit_related_columns_tree.item(item, values=(current_values[0], new_value), 
                                             tags=("checked" if new_value == "✓" else "unchecked",))

    def add_new_dim_field(self):
        related_table = self.new_related_combo.get()
        main_fk = self.new_main_fk_combo.get()
        related_pk = self.new_related_pk_combo.get()
        related_col = self.new_related_col_combo.get()
        col_alias = self.new_col_alias_entry.get() or f"{related_table}_{related_col}"
        
        if not all([related_table, main_fk, related_pk, related_col]):
            messagebox.showwarning("Campos incompletos", "Completa todos los campos para agregar una nueva dimensión")
            return
        
        # Check if this join already exists
        existing_join = next((j for j in self.selected_joins if j['related_table'] == related_table and j['main_fk'] == main_fk and j['related_pk'] == related_pk), None)
        
        if not existing_join:
            # Add new join
            join = {
                'related_table': related_table,
                'main_fk': main_fk,
                'related_pk': related_pk,
                'related_col': related_col,
                'col_alias': col_alias,
                'alias': related_table[:3] + str(len(self.selected_joins))
            }
            self.selected_joins.append(join)
        
        # Add the column to the treeview
        self.edit_related_columns_tree.insert("", "end",
                                        values=(f"{related_table}.{related_col}", "✓", col_alias),
                                        tags=("checked",))
        
        # Clear the form
        self.new_related_col_combo.set('')
        self.new_col_alias_entry.delete(0, tk.END)

    def generate_edited_sql(self):
        if not self.current_fact_table:
            messagebox.showwarning("Sin tabla principal", "No se ha cargado ninguna vista para editar")
            return
        
        # Get selected fact columns
        fact_columns = []
        for item in self.edit_main_columns_tree.get_children():
            values = self.edit_main_columns_tree.item(item, "values")
            if values[1] == "✓":
                fact_columns.append(f"f.{values[0]}")
        
        # Get selected dimension columns
        related_columns = []
        related_tables = {}
        for item in self.edit_related_columns_tree.get_children():
            values = self.edit_related_columns_tree.item(item, "values")
            if values[1] == "✓":
                table, column = values[0].split(".")
                if table not in related_tables:
                    related_tables[table] = []
                alias = values[2] if len(values) > 2 and values[2] else f"{table}_{column}"
                related_tables[table].append((column, alias))
        
        # Build SELECT clause
        select_parts = fact_columns
        
        # Build JOINs and add dimension columns
        joins = []
        for i, j in enumerate(self.selected_joins):
            if j['related_table'] in related_tables:
                alias = j.get('alias', j['related_table'][:3] + str(i))
                for col, col_alias in related_tables[j['related_table']]:
                    select_parts.append(f"{alias}.{col} AS {col_alias}")
                joins.append(f"LEFT JOIN {j['related_table']} {alias} ON f.{j['main_fk']} = {alias}.{j['related_pk']}")
        
        if not select_parts:
            messagebox.showwarning("Sin columnas", "Selecciona al menos una columna")
            return
        
        sql = f"SELECT\n    " + ",\n    ".join(select_parts) + f"\nFROM {self.current_fact_table} f\n" + "\n".join(joins)
        self.edit_sql_text.delete("1.0", tk.END)
        self.edit_sql_text.insert(tk.END, sql)

    def update_view(self):
        view_name = self.view_name_entry.get().strip()
        if not view_name:
            messagebox.showerror("Nombre faltante", "Debes ingresar un nombre para la vista")
            return
        
        # Get the SQL from the editor
        sql = self.edit_sql_text.get("1.0", tk.END).strip()
        if not sql:
            messagebox.showerror("SQL vacío", "No hay SQL para actualizar la vista")
            return
        
        try:
            # Update the view
            update_sql = f"CREATE OR ALTER VIEW {view_name} AS\n{sql}"
            self.cursor.execute(update_sql)
            self.connection.commit()
            messagebox.showinfo("Vista actualizada", f"La vista '{view_name}' fue actualizada exitosamente")
            
            # Refresh views list
            self.cursor.execute("SELECT name FROM sys.views")
            self.existing_views = [r[0] for r in self.cursor.fetchall()]
            self.view_combo['values'] = self.existing_views
            
        except Exception as e:
            messagebox.showerror("Error al actualizar vista", str(e))# ... (copiar aquí todos los demás métodos de SQLViewGenerator)

if __name__ == '__main__':
    root = ThemedTk(theme="arc")  # Ventana con tema oscuro
    app = ModernSQLViewGenerator(root)
    root.mainloop()