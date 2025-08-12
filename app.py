from flask import Flask, render_template, session, redirect, url_for, request, flash
import json
import os
from tecnoprices_order import place_order

# Coeficientes de financiación
COEF_6 = 1.32117
COEF_12 = 1.65

# --- Formato de moneda ---
def ars(n):
    try:
        return f"${int(round(n)):,}".replace(",", ".")
    except Exception:
        return str(n)

# --- Descripciones cortas por CPU ---
def describe_cpu(cpu_name: str) -> str:
    n = (cpu_name or "").lower()
    if "4600g" in n:
        return "Con el Ryzen 5 4600G vas a poder disfrutar juegos como Fortnite, Valorant, LoL o CS2 en buena calidad sin placa de video dedicada, además de estudiar, trabajar y crear contenido básico."
    if "5600g" in n or "5600gt" in n:
        return "El Ryzen 5 5600G ofrece un excelente balance: gaming eSports fluido sin GPU dedicada y rendimiento sólido para estudio y trabajo."
    if "5700g" in n:
        return "El Ryzen 7 5700G brinda potencia extra para multitarea, edición liviana y juegos eSports con gráficos integrados."
    if "8700g" in n:
        return "El Ryzen 7 8700G incorpora gráficos integrados muy capaces (RDNA3), ideal para eSports y creadores que recién empiezan."
    if any(x in n for x in ["9600x", "5700x", "5800xt", "5900x", "9700x", "9900x", "9950x", "9800x3d", "9950x3d"]):
        return "Procesador ideal para gaming exigente con placa de video dedicada, edición y streaming con excelente rendimiento multicore."
    return "Equipo equilibrado para jugar títulos populares, estudiar, trabajar y crear sin complicaciones."

def describe_mother(mother_name: str) -> str:
    n = (mother_name or "").lower()
    if "a520" in n:
        return "Mother con chipset A520: plataforma confiable para uso diario y gaming eSports, con posibilidad de upgrades moderados."
    if "b450" in n:
        return "Mother B450: excelente relación precio/rendimiento, permite upgrades a Ryzen de mayor gama."
    if "b550" in n:
        return "Mother B550: preparada para upgrades, buen soporte de memorias y almacenamiento NVMe."
    return "Mother estable y compatible, lista para futuras actualizaciones."

# --- Generador del texto de venta ---
def build_marketing_text(build, contado, total_6, cuota_6, total_12, cuota_12) -> str:
    cpu = build.get("CPU", {})
    mb  = build.get("MOTHER", {})
    cpu_name = cpu.get("nombre", "Procesador a confirmar") if isinstance(cpu, dict) else "Procesador a confirmar"
    mb_name  = mb.get("nombre", "Motherboard a confirmar") if isinstance(mb, dict) else "Motherboard a confirmar"
    cpu_line = f"🧠 Procesador: {cpu_name}. "
    cpu_desc = describe_cpu(cpu_name)
    mb_line  = f"🧩 Motherboard: {mb_name}. "
    mb_desc  = describe_mother(mb_name)
    text = f"""🎮 ¡PC lista para jugar, estudiar y trabajar! 🎮
🚀 Rendimiento equilibrado y preparada para crecer.

Mirá sus componentes:

• {cpu_line}{cpu_desc}
• {mb_line}{mb_desc}

Además, te la entregamos con:
• 🛠️ Armado profesional
• 🪟 Windows 10/11 activado
• 📦 Paquete Office
• 📶 Adaptador WiFi
• 🚚 Envío e instalación a domicilio en Mar del Plata

🛡️ ¡6 MESES DE GARANTÍA TOTAL! 🛡️

💰 PRECIOS:
• 💵 Contado/Transferencia: {ars(contado)}
• 💳 6 cuotas fijas: total {ars(total_6)} → {ars(cuota_6)} c/u
• 💳 12 cuotas fijas: total {ars(total_12)} → {ars(cuota_12)} c/u

📍 Podés retirarla y probarla en nuestro local.
🏠 En MDP te la llevamos, la instalamos ¡y recién ahí la pagás!

Recomendada para adolescentes y adultos que buscan una PC versátil para juegos populares, clases online, ofimática y creación básica de contenido.
"""
    return text

app = Flask(__name__)
app.secret_key = "cambia_esto_por_un_secreto_seguro"

# Orden del wizard
CATEGORIES_FLOW = ["CPU", "MOTHER", "RAM", "SSD", "GPU", "FUENTE", "GABINETE"]
# Categorías que aceptan múltiples ítems
MULTI_CATEGORIES = {"RAM", "SSD"}

def compute_subtotal(build):
    total = 0
    for _, val in (build or {}).items():
        if isinstance(val, list):
            total += sum(int(it.get("precio", 0)) for it in val if isinstance(it, dict))
        elif isinstance(val, dict):
            total += int(val.get("precio", 0))
    return total

@app.context_processor
def inject_globals():
    return {
        "categories": CATEGORIES_FLOW,
        "build": session.get("build", {}),
        "subtotal": session.get("subtotal", 0),
    }

# --- Utilidades ---
def load_stock():
    try:
        with open("stock.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def next_category(current):
    idx = CATEGORIES_FLOW.index(current)
    return CATEGORIES_FLOW[idx + 1] if idx < len(CATEGORIES_FLOW) - 1 else None

def prev_category(current):
    idx = CATEGORIES_FLOW.index(current)
    return CATEGORIES_FLOW[idx - 1] if idx > 0 else None

def save_item_to_stock(category, item):
    category = category.strip().upper()
    filepath = "stock.json"
    data = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except json.JSONDecodeError: data = {}
    if category not in data:
        data[category] = []
    item_norm = {
        "nombre": str(item.get("nombre", "")).strip(),
        "codigo": str(item.get("codigo", "")).strip(),
        "precio": int(item.get("precio", 0)),
        "stock": int(item.get("stock", 0))
    }
    replaced = False
    for i, it in enumerate(data[category]):
        if str(it.get("codigo")) == item_norm["codigo"]:
            data[category][i] = item_norm
            replaced = True
            break
    if not replaced:
        data[category].append(item_norm)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return replaced

def delete_item_from_stock(category: str, codigo: str) -> bool:
    category = category.strip().upper()
    path = "stock.json"
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except json.JSONDecodeError: data = {}
    if category not in data:
        return False
    items = data.get(category, [])
    new_items = [it for it in items if str(it.get("codigo")) != str(codigo)]
    removed = len(new_items) < len(items)
    if removed:
        data[category] = new_items
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    return removed

@app.template_filter("stock_class")
def stock_class_filter(stock_value):
    if stock_value == 0:
        return "badge badge-out-of-stock"
    if 1 <= stock_value <= 3:
        return "badge badge-low-stock"
    if stock_value > 3:
        return "badge badge-in-stock"
    return "badge badge-muted"

@app.template_filter("compact_lines")
def compact_lines(items):
    """
    Agrupa una lista de items (dict con nombre, codigo, precio) por 'codigo'
    y devuelve [{'nombre','precio','cantidad','total'}] ordenado por nombre.
    Ignora elementos que no sean dict.
    """
    groups = {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        code = str(it.get("codigo", "")) or it.get("nombre", "")
        g = groups.setdefault(code, {
            "nombre": it.get("nombre", ""),
            "precio": int(it.get("precio", 0)),
            "cantidad": 0
        })
        g["cantidad"] += 1
    out = []
    for g in groups.values():
        total = g["precio"] * g["cantidad"]
        out.append({**g, "total": total})
    out.sort(key=lambda x: x["nombre"])
    return out


# --- Rutas ---
@app.route("/manual", methods=["GET", "POST"])
def manual():
    suggested_categories = ["CPU", "MOTHER", "GPU", "RAM", "SSD", "FUENTE", "GABINETE", "OTRA"]
    if request.method == "POST":
        categoria = request.form.get("categoria", "OTRA").strip().upper()
        nombre = request.form.get("nombre", "").strip()
        codigo = request.form.get("codigo", "").strip()
        precio = request.form.get("precio", "0").strip()
        stock = request.form.get("stock", "0").strip()
        if not nombre or not codigo:
            flash("Debe completar NOMBRE y CÓDIGO.", "error")
            return redirect(url_for("manual"))
        try:
            precio_int = int(precio)
            stock_int = int(stock)
        except ValueError:
            flash("Precio y Stock deben ser números enteros.", "error")
            return redirect(url_for("manual"))
        updated = save_item_to_stock(
            categoria,
            {"nombre": nombre, "codigo": codigo, "precio": precio_int, "stock": stock_int}
        )
        flash(
            f"Componente {'ACTUALIZADO' if updated else 'AGREGADO'} en {categoria}: {nombre} (código {codigo}).",
            "success"
        )
        return redirect(url_for("manual"))
    return render_template("manual.html", suggested_categories=suggested_categories)

@app.route("/place-order")
def place_order_route():
    build = session.get("build", {})
    if not build:
        return redirect(url_for("index"))
    codigos_cantidades = []
    for v in build.values():
        if isinstance(v, dict):
            codigo = v.get("codigo")
            if codigo:
                codigos_cantidades.append((str(codigo), 1))
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, dict):
                    codigo = it.get("codigo")
                    if codigo:
                        codigos_cantidades.append((str(codigo), 1))
    try:
        place_order(codigos_cantidades, headless=False)
        flash("Pedido enviado a Technoprices correctamente.", "success")
    except Exception as e:
        flash(f"Error al realizar el pedido: {e}", "error")
    return redirect(url_for("final"))

@app.template_filter("money")
def money_filter(value):
    try:
        return f"${int(value):,}".replace(",", ".")
    except Exception:
        return str(value)

@app.route("/")
def index():
    return render_template("home.html")

@app.route("/start")
def start():
    session["build"] = {}
    session["subtotal"] = 0
    session["profit"] = 0
    first = CATEGORIES_FLOW[0]
    return render_template(
        "select.html",
        category=first,
        items=(load_stock().get(first) or []),
        build=session.get("build", {}),
        subtotal=session.get("subtotal", 0),
        next_cat=next_category(first),
        prev_cat=prev_category(first),
    )

@app.route("/select/<category>", methods=["GET", "POST"])
def select_category(category):
    if category not in CATEGORIES_FLOW:
        return redirect(url_for("index"))

    if request.method == "POST":
        # "Siguiente" sin seleccionar
        if request.form.get("skip") == "1":
            build = session.get("build", {})
            session["build"] = build
            session["subtotal"] = compute_subtotal(build)
            nxt = next_category(category)
            return redirect(url_for("select_category", category=nxt)) if nxt else redirect(url_for("final"))

        # Selección normal o "+" (agregar otro igual sin avanzar)
        code = (request.form.get("codigo") or "").strip()
        name = (request.form.get("nombre") or "").strip()
        price = request.form.get("precio", type=int)
        add_more = request.form.get("add") == "1"

        item = {"codigo": code, "nombre": name, "precio": int(price or 0)}
        build = session.get("build", {})

        if category in MULTI_CATEGORIES:
            current = build.get(category)
            if isinstance(current, dict):
                current = [current]
            elif current is None or not isinstance(current, list):
                current = []
            current.append(item)
            build[category] = current
        else:
            build[category] = item

        session["build"] = build
        session["subtotal"] = compute_subtotal(build)

        if category in MULTI_CATEGORIES and add_more:
            # quedarse en la misma categoría
            return redirect(url_for("select_category", category=category))

        nxt = next_category(category)
        return redirect(url_for("select_category", category=nxt)) if nxt else redirect(url_for("final"))

    # GET
    items = load_stock().get(category) or []
    items = sorted(items, key=lambda x: x.get("precio", 0))
    return render_template("select.html",
                           category=category,
                           items=items,
                           build=session.get("build", {}),
                           subtotal=session.get("subtotal", 0),
                           next_cat=next_category(category),
                           prev_cat=prev_category(category),
    )

@app.route("/delete")
def delete_items():
    data = load_stock()
    flat = []
    for cat, items in (data or {}).items():
        for it in items:
            flat.append({
                "categoria": cat,
                "nombre": it.get("nombre", ""),
                "codigo": str(it.get("codigo", "")),
                "precio": int(it.get("precio", 0)),
                "stock": int(it.get("stock", 0)),
            })
    flat.sort(key=lambda r: (r["categoria"], r["nombre"]))
    return render_template("delete_list.html", items=flat)

@app.route("/delete-item", methods=["POST"], endpoint="delete_item")
def delete_item_route():
    categoria = request.form.get("categoria", "").strip()
    codigo = request.form.get("codigo", "").strip()
    if not categoria or not codigo:
        flash("Faltan datos para eliminar el componente.", "error")
        return redirect(url_for("delete_items"))
    ok = delete_item_from_stock(categoria, codigo)
    flash(
        f"Componente {'eliminado' if ok else 'no encontrado'}: {categoria} / código {codigo}",
        "success" if ok else "error"
    )
    return redirect(url_for("delete_items"))

@app.route("/back/<category>")
def go_back(category):
    if category not in CATEGORIES_FLOW:
        return redirect(url_for("index"))
    prv = prev_category(category)
    return redirect(url_for("select_category", category=prv)) if prv else redirect(url_for("index"))

@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))

@app.route("/summary")
def summary():
    build = session.get("build", {})
    subtotal = session.get("subtotal", 0)
    return render_template("summary.html",
                           build=build,
                           subtotal=subtotal,
                           categories=CATEGORIES_FLOW)

@app.route("/final", methods=["GET", "POST"])
def final():
    subtotal = session.get("subtotal", 0)
    profit = session.get("profit", 0)
    venta = session.get("venta")  # precio de venta fijo (opcional)

    if request.method == "POST":
        venta_input = (request.form.get("venta") or "").strip()
        ganancia_input = (request.form.get("ganancia") or "").strip()

        # Si el usuario puso un precio de venta, tiene prioridad
        v = None
        if venta_input != "":
            try:
                v = int(venta_input)
            except ValueError:
                v = None

        if v is not None and v >= 0:
            venta = v
            session["venta"] = v
            profit = v - subtotal   # puede ser negativo si vende por debajo del costo
            session["profit"] = profit
        else:
            # Modo tradicional: usar ganancia
            session["venta"] = None
            try:
                profit = int(ganancia_input or 0)
            except ValueError:
                profit = 0
            session["profit"] = profit

    # Contado final
    contado = venta if (venta is not None) else (subtotal + profit)

    total_6 = int(round(contado * COEF_6))
    cuota_6 = total_6 / 6
    total_12 = int(round(contado * COEF_12))
    cuota_12 = total_12 / 12

    marketing_text = build_marketing_text(
        session.get("build", {}),
        contado=contado,
        total_6=total_6,
        cuota_6=cuota_6,
        total_12=total_12,
        cuota_12=cuota_12
    )
    return render_template(
        "final.html",
        build=session.get("build", {}),
        subtotal=subtotal,
        profit=profit,
        venta=venta,                 # <-- nuevo
        contado=contado,
        total_6=total_6,
        cuota_6=cuota_6,
        total_12=total_12,
        cuota_12=cuota_12,
        categories=CATEGORIES_FLOW,
        marketing_text=marketing_text
    )

if __name__ == "__main__":
    app.run(debug=True)
