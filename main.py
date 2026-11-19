import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database
import utils

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class NexaPOSApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        database.setup_database()

        self.title("NexaPOS Pro — Enterprise Billing, Inventory & Analytics")
        self.geometry("1280x760")
        self.minsize(1150, 680)

        self.current_user = None
        self.cart = []
        self.selected_inv_id = None
        self.clock_job = None

        self._configure_treeview_style()
        self.show_login_screen()

    def _configure_treeview_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background="#1f242d",
            foreground="#e6edf3",
            fieldbackground="#1f242d",
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Custom.Treeview.Heading",
            background="#2b313c",
            foreground="#58a6ff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", "#1f6feb")],
            foreground=[("selected", "#ffffff")],
        )

    # =========================================================================
    # SECURE LOGIN SCREEN (ANY NAME + 1234 OR DB CREDENTIALS)
    # =========================================================================
    def show_login_screen(self):
        if self.clock_job:
            self.after_cancel(self.clock_job)
            self.clock_job = None

        for w in self.winfo_children():
            w.destroy()

        bg = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=0)
        bg.pack(fill="both", expand=True)

        card = ctk.CTkFrame(
            bg,
            width=420,
            height=470,
            corner_radius=16,
            fg_color="#161b22",
            border_width=1,
            border_color="#30363d",
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(
            card,
            text="NEXAPOS PRO",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#58a6ff",
        ).pack(pady=(36, 4))

        ctk.CTkLabel(
            card,
            text="Secure Enterprise Login",
            font=ctk.CTkFont(size=13),
            text_color="#8b949e",
        ).pack(pady=(0, 24))

        self.login_user = ctk.CTkEntry(
            card,
            placeholder_text="Enter Your Name (e.g. Dhammadeepa)",
            width=310,
            height=42,
        )
        self.login_user.pack(pady=8)

        self.login_pass = ctk.CTkEntry(
            card,
            placeholder_text="Password (1234)",
            show="*",
            width=310,
            height=42,
        )
        self.login_pass.pack(pady=8)
        self.login_pass.bind("<Return>", lambda e: self._attempt_login())

        self.login_role = ctk.CTkOptionMenu(
            card,
            values=["Admin", "Cashier"],
            width=310,
            height=38,
            fg_color="#21262d",
        )
        self.login_role.set("Admin")
        self.login_role.pack(pady=8)

        ctk.CTkButton(
            card,
            text="LOGIN TO SYSTEM",
            width=310,
            height=44,
            corner_radius=8,
            fg_color="#1f6feb",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._attempt_login,
        ).pack(pady=(18, 12))

        ctk.CTkLabel(
            card,
            text="Quick Access: Enter Any Name  |  Password: 1234",
            font=ctk.CTkFont(size=11),
            text_color="#3fb950",
            justify="center",
        ).pack(pady=(6, 0))

    def _attempt_login(self):
        name = self.login_user.get().strip()
        password = self.login_pass.get().strip()
        role = self.login_role.get()

        if not name:
            messagebox.showwarning("Name Required", "Please enter your name to login!")
            return

        if password == "1234":
            self.current_user = {"username": name, "role": role}
            self._build_main_layout()
            self.show_dashboard()
            self._update_clock()
        else:
            user = database.authenticate_user(name, password)
            if user:
                self.current_user = user
                self._build_main_layout()
                self.show_dashboard()
                self._update_clock()
            else:
                messagebox.showerror("Access Denied", "Invalid Password! Use '1234' to login.")

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.current_user = None
            self.cart.clear()
            self.show_login_screen()

    # =========================================================================
    # MAIN LAYOUT & SIDEBAR
    # =========================================================================
    def _build_main_layout(self):
        for w in self.winfo_children():
            w.destroy()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=235, corner_radius=0, fg_color="#161b22")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="NEXAPOS PRO",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#58a6ff",
        ).grid(row=0, column=0, padx=20, pady=(24, 2))

        role_color = "#3fb950" if self.current_user["role"] == "Admin" else "#d29922"
        ctk.CTkLabel(
            self.sidebar,
            text=f"{self.current_user['username'].upper()}  ({self.current_user['role']})",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=role_color,
        ).grid(row=1, column=0, padx=20, pady=(0, 22))

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "  Dashboard & Charts", self.show_dashboard),
            ("pos", "  POS Terminal", self.show_pos),
            ("inventory", "  Inventory Manager", self.show_inventory),
            ("sales", "  Sales & Invoices", self.show_sales),
        ]

        for idx, (key, text, cmd) in enumerate(nav_items, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#21262d",
                font=ctk.CTkFont(size=13, weight="bold"),
                command=cmd,
            )
            btn.grid(row=idx, column=0, padx=14, pady=4, sticky="ew")
            self.nav_buttons[key] = btn

        if self.current_user["role"] == "Admin":
            ctk.CTkButton(
                self.sidebar,
                text="Backup Database",
                height=34,
                corner_radius=8,
                fg_color="#21262d",
                hover_color="#30363d",
                command=self._backup_db,
            ).grid(row=7, column=0, padx=16, pady=(6, 6), sticky="ew")

        self.lbl_clock = ctk.CTkLabel(
            self.sidebar, text="", font=ctk.CTkFont(size=11), text_color="#8b949e"
        )
        self.lbl_clock.grid(row=8, column=0, padx=16, pady=(4, 6))

        self.theme_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Dark Mode",
            command=self._toggle_theme,
            onvalue="Dark",
            offvalue="Light",
        )
        self.theme_switch.select()
        self.theme_switch.grid(row=9, column=0, padx=20, pady=(2, 10))

        ctk.CTkButton(
            self.sidebar,
            text="Logout",
            height=34,
            corner_radius=8,
            fg_color="#da3633",
            hover_color="#b62324",
            command=self._logout,
        ).grid(row=10, column=0, padx=16, pady=(0, 18), sticky="ew")

        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1117")
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)

    def _backup_db(self):
        path = database.backup_database()
        messagebox.showinfo("Backup Successful", f"Database safely backed up to:\n{path}")

    def _set_active_nav(self, active_key):
        for key, btn in self.nav_buttons.items():
            btn.configure(fg_color="#1f6feb" if key == active_key else "transparent")

    def _clear_main_area(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    def _toggle_theme(self):
        ctk.set_appearance_mode(self.theme_switch.get())

    def _update_clock(self):
        if self.current_user and hasattr(self, "lbl_clock") and self.lbl_clock.winfo_exists():
            self.lbl_clock.configure(text=datetime.now().strftime("%Y-%m-%d  |  %I:%M:%S %p"))
            self.clock_job = self.after(1000, self._update_clock)

    # =========================================================================
    # 1. DASHBOARD & QUICK RESTOCK
    # =========================================================================
    def show_dashboard(self):
        self._set_active_nav("dashboard")
        self._clear_main_area()

        container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=22, pady=20)
        container.grid_columnconfigure((0, 1, 2, 3), weight=1)
        container.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            container,
            text=f"Welcome back, {self.current_user['username']}!  —  Analytics Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#e6edf3",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 16))

        kpis = database.get_dashboard_kpis()
        is_admin = self.current_user["role"] == "Admin"
        profit_display = f"LKR {kpis['profit']:,.2f}" if is_admin else "Restricted (Admin)"

        cards_info = [
            ("Total Revenue", f"LKR {kpis['revenue']:,.2f}", "#1f6feb", None),
            ("Net Profit", profit_display, "#238636", None),
            ("Total Invoices", str(kpis["orders"]), "#8957e5", None),
            (
                "Low Stock Alerts",
                f"{kpis['low_stock']} Items",
                "#da3633" if kpis["low_stock"] > 0 else "#238636",
                self._open_restock_popup,
            ),
        ]

        for col, (title, value, accent, action) in enumerate(cards_info):
            card = ctk.CTkFrame(
                container,
                corner_radius=12,
                fg_color="#161b22",
                border_width=1,
                border_color="#30363d",
            )
            card.grid(row=1, column=col, padx=8, pady=(0, 16), sticky="ew")
            ctk.CTkFrame(card, height=4, fg_color=accent, corner_radius=2).pack(
                fill="x", padx=12, pady=(10, 6)
            )
            ctk.CTkLabel(
                card, text=title, font=ctk.CTkFont(size=12), text_color="#8b949e"
            ).pack(anchor="w", padx=14)
            ctk.CTkLabel(
                card, text=value, font=ctk.CTkFont(size=19, weight="bold")
            ).pack(anchor="w", padx=14, pady=(2, 8))
            if action and kpis["low_stock"] > 0:
                ctk.CTkButton(
                    card,
                    text="Quick Restock (+10)",
                    height=24,
                    font=ctk.CTkFont(size=11),
                    fg_color="#da3633",
                    hover_color="#b62324",
                    command=action,
                ).pack(fill="x", padx=14, pady=(0, 10))
            else:
                ctk.CTkLabel(card, text="", height=10).pack()

        charts_frame = ctk.CTkFrame(container, fg_color="transparent")
        charts_frame.grid(row=2, column=0, columnspan=4, sticky="nsew")
        charts_frame.grid_columnconfigure((0, 1), weight=1)
        charts_frame.grid_rowconfigure(0, weight=1)

        # Chart 1: Daily Revenue & Net Profit
        c1 = ctk.CTkFrame(
            charts_frame,
            corner_radius=12,
            fg_color="#161b22",
            border_width=1,
            border_color="#30363d",
        )
        c1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        days, revs, profs = database.get_daily_sales_chart_data()
        fig1 = Figure(figsize=(5.5, 4), dpi=100, facecolor="#161b22")
        ax1 = fig1.add_subplot(111)
        ax1.set_facecolor("#161b22")
        ax1.plot(days, revs, marker="o", color="#58a6ff", linewidth=2.5, label="Revenue")
        if is_admin:
            ax1.plot(days, profs, marker="s", color="#3fb950", linewidth=2.5, label="Net Profit")
        ax1.set_title(
            "Daily Revenue vs Net Profit (LKR)",
            color="#e6edf3",
            fontsize=11,
            fontweight="bold",
            pad=10,
        )
        ax1.tick_params(colors="#8b949e", labelsize=8)
        for s in ax1.spines.values():
            s.set_color("#30363d")
        ax1.grid(color="#21262d", linestyle="--", linewidth=0.7)
        ax1.legend(
            facecolor="#161b22", edgecolor="#30363d", labelcolor="#e6edf3", fontsize=8
        )
        fig1.tight_layout()
        FigureCanvasTkAgg(fig1, master=c1).get_tk_widget().pack(
            fill="both", expand=True, padx=10, pady=10
        )

        # Chart 2: Stock by Category
        c2 = ctk.CTkFrame(
            charts_frame,
            corner_radius=12,
            fg_color="#161b22",
            border_width=1,
            border_color="#30363d",
        )
        c2.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        cats, stocks = database.get_category_stock_chart_data()
        fig2 = Figure(figsize=(5.5, 4), dpi=100, facecolor="#161b22")
        ax2 = fig2.add_subplot(111)
        ax2.set_facecolor("#161b22")
        colors = ["#58a6ff", "#a371f7", "#3fb950", "#d29922", "#f85149"]
        ax2.bar(cats, stocks, color=colors[: len(cats)], width=0.55)
        ax2.set_title(
            "Inventory Units by Category",
            color="#e6edf3",
            fontsize=11,
            fontweight="bold",
            pad=10,
        )
        ax2.tick_params(colors="#8b949e", labelsize=8)
        for s in ax2.spines.values():
            s.set_color("#30363d")
        ax2.grid(axis="y", color="#21262d", linestyle="--", linewidth=0.7)
        fig2.tight_layout()
        FigureCanvasTkAgg(fig2, master=c2).get_tk_widget().pack(
            fill="both", expand=True, padx=10, pady=10
        )

    def _open_restock_popup(self):
        win = ctk.CTkToplevel(self)
        win.title("Low Stock Quick Restock")
        win.geometry("500x380")
        win.grab_set()

        ctk.CTkLabel(
            win, text="Low Stock Products", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=14)
        scroll = ctk.CTkScrollableFrame(win, fg_color="#161b22")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        def refresh_list():
            for w in scroll.winfo_children():
                w.destroy()
            items = database.get_low_stock_products()
            if not items:
                ctk.CTkLabel(
                    scroll,
                    text="All products are sufficiently stocked!",
                    text_color="#3fb950",
                ).pack(pady=20)
                self.show_dashboard()
                return
            for p in items:
                row = ctk.CTkFrame(scroll, fg_color="#21262d", corner_radius=8)
                row.pack(fill="x", pady=5, padx=6)
                ctk.CTkLabel(
                    row,
                    text=f"{p['name']} (Stock: {p['stock']})",
                    font=ctk.CTkFont(size=13),
                ).pack(side="left", padx=12, pady=10)
                ctk.CTkButton(
                    row,
                    text="+10 Restock",
                    width=95,
                    height=28,
                    fg_color="#238636",
                    command=lambda pid=p["id"]: [
                        database.restock_product(pid, 10),
                        refresh_list(),
                        self.show_dashboard(),
                    ],
                ).pack(side="right", padx=10, pady=8)

        refresh_list()

    # =========================================================================
    # 2. LIVE POS TERMINAL
    # =========================================================================
    def show_pos(self):
        self._set_active_nav("pos")
        self._clear_main_area()

        container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=18)
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=2)
        container.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            container, text="POS Billing Terminal", font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        left = ctk.CTkFrame(
            container, corner_radius=12, fg_color="#161b22", border_width=1, border_color="#30363d"
        )
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        sbar = ctk.CTkFrame(left, fg_color="transparent")
        sbar.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        sbar.grid_columnconfigure(0, weight=1)

        self.pos_search_entry = ctk.CTkEntry(
            sbar, placeholder_text="Search by Name, SKU or Category...", height=36
        )
        self.pos_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.pos_search_entry.bind("<KeyRelease>", lambda e: self._load_pos_products())

        self.pos_qty_entry = ctk.CTkEntry(sbar, width=65, height=36)
        self.pos_qty_entry.insert(0, "1")
        self.pos_qty_entry.grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            sbar,
            text="+ Add to Cart",
            width=115,
            height=36,
            fg_color="#1f6feb",
            command=self._add_selected_to_cart,
        ).grid(row=0, column=2)

        cols = ("ID", "SKU", "Product Name", "Price (LKR)", "Stock")
        self.pos_tree = ttk.Treeview(left, columns=cols, show="headings", style="Custom.Treeview")
        for c, w in zip(cols, [45, 95, 220, 100, 65]):
            self.pos_tree.heading(c, text=c)
            self.pos_tree.column(c, width=w, anchor="center" if c != "Product Name" else "w")
        self.pos_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.pos_tree.bind("<Double-1>", lambda e: self._add_selected_to_cart())
        self._load_pos_products()

        right = ctk.CTkFrame(
            container, corner_radius=12, fg_color="#161b22", border_width=1, border_color="#30363d"
        )
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        cf = ctk.CTkFrame(right, fg_color="transparent")
        cf.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        cf.grid_columnconfigure(0, weight=1)
        self.pos_customer = ctk.CTkEntry(cf, placeholder_text="Customer Name (Optional)", height=34)
        self.pos_customer.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.pos_payment = ctk.CTkOptionMenu(
            cf, values=["Cash", "Card", "Bank Transfer"], width=125, height=34
        )
        self.pos_payment.grid(row=0, column=1)

        ccols = ("Item", "Qty", "Price", "Total")
        self.cart_tree = ttk.Treeview(
            right, columns=ccols, show="headings", style="Custom.Treeview", height=10
        )
        for c, w in zip(ccols, [160, 45, 80, 90]):
            self.cart_tree.heading(c, text=c)
            self.cart_tree.column(c, width=w, anchor="center" if c != "Item" else "w")
        self.cart_tree.grid(row=1, column=0, sticky="nsew", padx=12)

        cb = ctk.CTkFrame(right, fg_color="transparent")
        cb.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        ctk.CTkButton(
            cb,
            text="Remove Item",
            fg_color="#da3633",
            hover_color="#b62324",
            width=110,
            height=30,
            command=self._remove_cart_item,
        ).pack(side="left")
        ctk.CTkButton(
            cb,
            text="Clear Cart",
            fg_color="#30363d",
            hover_color="#484f58",
            width=100,
            height=30,
            command=self._clear_cart,
        ).pack(side="right")

        dt = ctk.CTkFrame(right, fg_color="#0d1117", corner_radius=8)
        dt.grid(row=3, column=0, sticky="ew", padx=12, pady=6)
        dt.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(dt, text="Discount %:").grid(row=0, column=0, padx=8, pady=8)
        self.pos_discount = ctk.CTkEntry(dt, width=60)
        self.pos_discount.insert(0, "0")
        self.pos_discount.grid(row=0, column=1, padx=4, pady=8, sticky="w")
        self.pos_discount.bind("<KeyRelease>", lambda e: self._refresh_cart_ui())

        ctk.CTkLabel(dt, text="Tax %:").grid(row=0, column=2, padx=8, pady=8)
        self.pos_tax = ctk.CTkEntry(dt, width=60)
        self.pos_tax.insert(0, "2")
        self.pos_tax.grid(row=0, column=3, padx=4, pady=8, sticky="w")
        self.pos_tax.bind("<KeyRelease>", lambda e: self._refresh_cart_ui())

        self.lbl_pos_summary = ctk.CTkLabel(
            right,
            text="Subtotal: LKR 0.00  |  Total: LKR 0.00",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#3fb950",
        )
        self.lbl_pos_summary.grid(row=4, column=0, pady=10)

        ctk.CTkButton(
            right,
            text="COMPLETE SALE & PRINT QR PDF INVOICE",
            height=46,
            corner_radius=10,
            fg_color="#238636",
            hover_color="#2ea043",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._checkout,
        ).grid(row=5, column=0, sticky="ew", padx=12, pady=(4, 14))
        self._refresh_cart_ui()

    def _load_pos_products(self):
        for r in self.pos_tree.get_children():
            self.pos_tree.delete(r)
        self.pos_products_cache = database.get_all_products(self.pos_search_entry.get().strip())
        for p in self.pos_products_cache:
            self.pos_tree.insert(
                "",
                "end",
                values=(p["id"], p["sku"], p["name"], f"{p['sell_price']:,.2f}", p["stock"]),
            )

    def _add_selected_to_cart(self):
        sel = self.pos_tree.selection()
        if not sel:
            return
        try:
            qty = int(self.pos_qty_entry.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Enter a positive integer.")
            return
        pid = self.pos_tree.item(sel[0])["values"][0]
        p = next((x for x in self.pos_products_cache if x["id"] == pid), None)
        if not p:
            return
        existing = next((c for c in self.cart if c["id"] == pid), None)
        if (existing["qty"] if existing else 0) + qty > p["stock"]:
            messagebox.showerror("Out of Stock", f"Only {p['stock']} units available!")
            return
        if existing:
            existing["qty"] += qty
        else:
            self.cart.append(
                {
                    "id": p["id"],
                    "name": p["name"],
                    "qty": qty,
                    "sell_price": p["sell_price"],
                    "cost_price": p["cost_price"],
                }
            )
        self._refresh_cart_ui()

    def _remove_cart_item(self):
        sel = self.cart_tree.selection()
        if sel:
            self.cart.pop(self.cart_tree.index(sel[0]))
            self._refresh_cart_ui()

    def _clear_cart(self):
        self.cart.clear()
        self._refresh_cart_ui()

    def _refresh_cart_ui(self):
        for r in self.cart_tree.get_children():
            self.cart_tree.delete(r)
        sub = sum(i["qty"] * i["sell_price"] for i in self.cart)
        for i in self.cart:
            self.cart_tree.insert(
                "",
                "end",
                values=(
                    i["name"][:24],
                    i["qty"],
                    f"{i['sell_price']:,.0f}",
                    f"{i['qty']*i['sell_price']:,.2f}",
                ),
            )
        try:
            d, t = float(self.pos_discount.get() or 0), float(self.pos_tax.get() or 0)
        except ValueError:
            d, t = 0.0, 0.0
        tot = (sub - sub * d / 100.0) * (1 + t / 100.0)
        self.lbl_pos_summary.configure(text=f"Subtotal: LKR {sub:,.2f}   |   Total: LKR {tot:,.2f}")

    def _checkout(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add items to cart first.")
            return
        try:
            d, t = float(self.pos_discount.get() or 0), float(self.pos_tax.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid Input", "Discount & Tax must be numbers.")
            return
        sale_data = database.record_sale(
            self.pos_customer.get().strip(), self.cart, d, t, self.pos_payment.get()
        )
        pdf_path = utils.generate_pdf_invoice(sale_data)
        self.cart.clear()
        self.pos_customer.delete(0, "end")
        self._refresh_cart_ui()
        self._load_pos_products()
        messagebox.showinfo(
            "Sale Completed",
            f"Invoice {sale_data['invoice_no']} created with QR Code!\nSaved: {pdf_path}",
        )

    # =========================================================================
    # 3. INVENTORY MANAGER (ROLE PROTECTED)
    # =========================================================================
    def show_inventory(self):
        self._set_active_nav("inventory")
        self._clear_main_area()
        is_admin = self.current_user["role"] == "Admin"

        container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=18)
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(container, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            top, text="Inventory Management", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left")
        if is_admin:
            ctk.CTkButton(
                top,
                text="Export Inventory Excel (.xlsx)",
                fg_color="#238636",
                command=lambda: utils.export_inventory_to_excel(database.get_all_products()),
            ).pack(side="right")

        tcard = ctk.CTkFrame(
            container, corner_radius=12, fg_color="#161b22", border_width=1, border_color="#30363d"
        )
        tcard.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        tcard.grid_columnconfigure(0, weight=1)
        tcard.grid_rowconfigure(0, weight=1)

        cols = ("ID", "SKU", "Name", "Category", "Cost", "Sell Price", "Stock", "Status")
        self.inv_tree = ttk.Treeview(tcard, columns=cols, show="headings", style="Custom.Treeview")
        for c, w in zip(cols, [40, 85, 175, 95, 75, 80, 55, 85]):
            self.inv_tree.heading(c, text=c)
            self.inv_tree.column(c, width=w, anchor="center" if c != "Name" else "w")
        self.inv_tree.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.inv_tree.bind("<<TreeviewSelect>>", self._on_inv_select)

        fcard = ctk.CTkFrame(
            container, corner_radius=12, fg_color="#161b22", border_width=1, border_color="#30363d"
        )
        fcard.grid(row=1, column=1, sticky="nsew")
        ctk.CTkLabel(
            fcard, text="Product Details", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(16, 10))

        self.inv_entries = {}
        for key, ph in [
            ("sku", "SKU Code"),
            ("name", "Product Name"),
            ("category", "Category"),
            ("cost_price", "Cost Price"),
            ("sell_price", "Sell Price"),
            ("stock", "Stock Qty"),
            ("min_stock", "Min Stock Alert"),
        ]:
            ent = ctk.CTkEntry(fcard, placeholder_text=ph, height=34)
            ent.pack(fill="x", padx=16, pady=6)
            self.inv_entries[key] = ent

        bbox = ctk.CTkFrame(fcard, fg_color="transparent")
        bbox.pack(fill="x", padx=16, pady=14)
        state = "normal" if is_admin else "disabled"
        ctk.CTkButton(bbox, text="Add New", fg_color="#1f6feb", state=state, command=self._inv_add).pack(
            fill="x", pady=4
        )
        ctk.CTkButton(
            bbox, text="Update Selected", fg_color="#d29922", state=state, command=self._inv_update
        ).pack(fill="x", pady=4)
        ctk.CTkButton(
            bbox, text="Delete Selected", fg_color="#da3633", state=state, command=self._inv_delete
        ).pack(fill="x", pady=4)
        ctk.CTkButton(bbox, text="Clear Form", fg_color="#30363d", command=self._inv_clear).pack(
            fill="x", pady=4
        )
        if not is_admin:
            ctk.CTkLabel(
                fcard, text="View-Only Mode (Cashier)", text_color="#d29922", font=ctk.CTkFont(size=11)
            ).pack()

        self._load_inventory_table()

    def _load_inventory_table(self):
        for r in self.inv_tree.get_children():
            self.inv_tree.delete(r)
        self.inv_cache = database.get_all_products()
        for p in self.inv_cache:
            st = "LOW STOCK" if p["stock"] <= p["min_stock"] else "IN STOCK"
            self.inv_tree.insert(
                "",
                "end",
                values=(
                    p["id"],
                    p["sku"],
                    p["name"],
                    p["category"],
                    f"{p['cost_price']:,.0f}",
                    f"{p['sell_price']:,.0f}",
                    p["stock"],
                    st,
                ),
            )

    def _on_inv_select(self, event):
        sel = self.inv_tree.selection()
        if not sel:
            return
        pid = self.inv_tree.item(sel[0])["values"][0]
        p = next((x for x in self.inv_cache if x["id"] == pid), None)
        if not p:
            return
        self.selected_inv_id = p["id"]
        for k in self.inv_entries:
            self.inv_entries[k].delete(0, "end")
            self.inv_entries[k].insert(0, str(p[k]))

    def _inv_clear(self):
        self.selected_inv_id = None
        for e in self.inv_entries.values():
            e.delete(0, "end")

    def _inv_add(self):
        try:
            v = {k: e.get().strip() for k, e in self.inv_entries.items()}
            database.add_product(
                v["sku"],
                v["name"],
                v["category"],
                v["cost_price"],
                v["sell_price"],
                v["stock"],
                v["min_stock"] or 5,
            )
            self._load_inventory_table()
            self._inv_clear()
            messagebox.showinfo("Success", "Product added!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _inv_update(self):
        if not self.selected_inv_id:
            return
        try:
            v = {k: e.get().strip() for k, e in self.inv_entries.items()}
            database.update_product(
                self.selected_inv_id,
                v["sku"],
                v["name"],
                v["category"],
                v["cost_price"],
                v["sell_price"],
                v["stock"],
                v["min_stock"] or 5,
            )
            self._load_inventory_table()
            self._inv_clear()
            messagebox.showinfo("Updated", "Product updated!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _inv_delete(self):
        if self.selected_inv_id and messagebox.askyesno("Delete", "Delete selected product?"):
            database.delete_product(self.selected_inv_id)
            self._load_inventory_table()
            self._inv_clear()

    # =========================================================================
    # 4. SALES HISTORY + PAST INVOICE VIEWER & REPRINT PDF
    # =========================================================================
    def show_sales(self):
        self._set_active_nav("sales")
        self._clear_main_area()

        container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=18)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(container, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            top,
            text="Sales History (Double-Click any Invoice to View & Reprint PDF)",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")
        if self.current_user["role"] == "Admin":
            ctk.CTkButton(
                top,
                text="Export Sales Excel (.xlsx)",
                fg_color="#238636",
                command=lambda: utils.export_sales_to_excel(database.get_all_sales()),
            ).pack(side="right")

        tcard = ctk.CTkFrame(
            container, corner_radius=12, fg_color="#161b22", border_width=1, border_color="#30363d"
        )
        tcard.grid(row=1, column=0, sticky="nsew")
        tcard.grid_columnconfigure(0, weight=1)
        tcard.grid_rowconfigure(0, weight=1)

        cols = (
            "Invoice No",
            "Customer",
            "Subtotal",
            "Discount",
            "Tax",
            "Grand Total",
            "Net Profit",
            "Payment",
            "Date",
        )
        self.sales_tree = ttk.Treeview(tcard, columns=cols, show="headings", style="Custom.Treeview")
        for c, w in zip(cols, [135, 135, 90, 75, 70, 100, 95, 95, 140]):
            self.sales_tree.heading(c, text=c)
            self.sales_tree.column(c, width=w, anchor="center" if c != "Customer" else "w")
        self.sales_tree.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.sales_tree.bind("<Double-1>", self._open_invoice_viewer)

        is_admin = self.current_user["role"] == "Admin"
        for s in database.get_all_sales():
            prof_str = f"{s['profit']:,.2f}" if is_admin else "Hidden"
            self.sales_tree.insert(
                "",
                "end",
                values=(
                    s["invoice_no"],
                    s["customer_name"],
                    f"{s['subtotal']:,.2f}",
                    f"{s['discount']:,.2f}",
                    f"{s['tax']:,.2f}",
                    f"{s['total']:,.2f}",
                    prof_str,
                    s["payment_method"],
                    s["sale_date"],
                ),
            )

    def _open_invoice_viewer(self, event):
        sel = self.sales_tree.selection()
        if not sel:
            return
        inv_no = self.sales_tree.item(sel[0])["values"][0]
        sale_data = database.get_sale_details_by_invoice(inv_no)
        if not sale_data:
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Invoice Details — {inv_no}")
        win.geometry("560x420")
        win.grab_set()

        ctk.CTkLabel(
            win,
            text=f"Invoice: {inv_no}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#58a6ff",
        ).pack(pady=(14, 2))
        ctk.CTkLabel(
            win,
            text=f"Customer: {sale_data['customer_name']}  |  Payment: {sale_data['payment_method']}  |  {sale_data['sale_date']}",
            font=ctk.CTkFont(size=11),
            text_color="#8b949e",
        ).pack(pady=(0, 10))

        cols = ("Product", "Qty", "Unit Price", "Line Total")
        tree = ttk.Treeview(win, columns=cols, show="headings", style="Custom.Treeview", height=8)
        for c, w in zip(cols, [220, 50, 100, 110]):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="center" if c != "Product" else "w")
        tree.pack(fill="both", expand=True, padx=16, pady=6)

        for item in sale_data["items"]:
            tree.insert(
                "",
                "end",
                values=(
                    item["name"],
                    item["qty"],
                    f"{item['sell_price']:,.2f}",
                    f"{item['line_total']:,.2f}",
                ),
            )

        ctk.CTkLabel(
            win,
            text=f"Grand Total: LKR {sale_data['total']:,.2f}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#3fb950",
        ).pack(pady=8)
        ctk.CTkButton(
            win,
            text="Reprint QR PDF Invoice",
            height=38,
            fg_color="#238636",
            hover_color="#2ea043",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: utils.generate_pdf_invoice(sale_data),
        ).pack(pady=(0, 16))


if __name__ == "__main__":
    app = NexaPOSApp()
    app.mainloop()