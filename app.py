from flask import Flask, render_template, session, redirect, url_for, request, flash
import json
import os
from tecnoprices_order import place_order
from marketing import build_marketing_text

DATA_FILE = "stock.json"  # tu archivo real

def actualizar_item(categoria, codigo_original, nombre, codigo, precio, stock):
    with open("stock.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if categoria in data:
        for item in data[categoria]:
            if str(item["codigo"]) == str(codigo_original):
                item["nombre"] = nombre
                item["codigo"] = codigo
                if precio is not None:
                    item["precio"] = precio
                if stock is not None:
                    item["stock"] = stock
                break

    with open("stock.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)    # Cargar datos existentes
    if not os.path.exists(DATA_FILE):
        return False

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Buscar y actualizar
    if categoria in data:
        for item in data[categoria]:
            if str(item["codigo"]) == str(codigo_original):
                item["nombre"] = nombre
                item["codigo"] = codigo
                item["precio"] = precio
                item["stock"] = stock
                break

    # Guardar cambios
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return True

# Coeficientes de financiación
COEF_6 = 1.32117
COEF_12 = 1.65

# --- Formato de moneda ---
def ars(n):
    try:
        return f"${int(round(n)):,}".replace(",", ".")
    except Exception:
        return str(n)

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

@app.route("/update_item", methods=["POST"])
def update_item():
    categoria = request.form.get("categoria")
    codigo_original = request.form.get("original_codigo")
    nombre = request.form.get("nombre")
    codigo = request.form.get("codigo")

    # Procesar precio: limpiar símbolos y convertir a entero
    precio_str = (request.form.get("precio", "") or "").strip()
    precio_str = precio_str.replace("$", "").replace(".", "").replace(",", "").strip()
    precio = int(precio_str) if precio_str.isdigit() else None

    # Procesar stock: limpiar separadores y convertir a entero
    stock_str = (request.form.get("stock", "") or "").strip()
    stock_str = stock_str.replace(",", "").strip()
    stock = int(stock_str) if stock_str.isdigit() else None

    # Actualizar el item en el archivo JSON
    actualizar_item(categoria, codigo_original, nombre, codigo, precio, stock)

    flash("Componente actualizado correctamente.", "success")
    return redirect(url_for("delete_items"))

@app.route("/place-order")
def place_order_route():
    build = session.get("build", {})
    if not build:
        return redirect(url_for("index"))

    codigos_cantidades = []
    for item in build.values():
        codigo = str(item.get("codigo", "")).strip()
        # Solo enviar si el código es completamente numérico
        if codigo.isdigit():
            codigos_cantidades.append((codigo, 1))

    if not codigos_cantidades:
        flash("No hay productos de Tecnoprices para ordenar.", "warning")
        return redirect(url_for("final"))

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
