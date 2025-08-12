# marketing.py
from datetime import datetime
import re

NEGOCIO = "KTech Computación"
CIUDAD  = "Mar del Plata"

def build_marketing_text(build, contado, total_6, cuota_6, total_12, cuota_12) -> str:
    def get_cat(cat):
        v = build.get(cat)
        if isinstance(v, dict): return v
        if isinstance(v, list): return v
        return None

    cpu   = get_cat("CPU")
    gpu   = get_cat("GPU")
    ram   = get_cat("RAM")
    ssd   = get_cat("SSD")
    mb    = get_cat("MOTHER")
    fuente= get_cat("FUENTE")
    gabi  = get_cat("GABINETE")

    cpu_name   = _first_name(cpu)
    gpu_name   = _first_name(gpu)
    mb_name    = _first_name(mb)
    fuente_name= _first_name(fuente)
    gabi_name  = _first_name(gabi)

    cpu_ct   = extraer_nucleos_hilos(cpu_name)
    cpu_ghz  = extraer_ghz(cpu_name)
    cpu_igpu = "" if hay_gpu_dedicada(gpu_name) else " con gráficos Radeon Vega para juegos en alta calidad"

    cpu_bracket = " — ".join(p for p in [cpu_ct, cpu_ghz.replace(", ", "") if cpu_ghz else ""] if p)
    cpu_line = f"🧠 *CPU:* {cpu_name}"
    if cpu_bracket:
        cpu_line += f" ({cpu_bracket})"
    if cpu_igpu:
        cpu_line += cpu_igpu

    gpu_line = ""
    if hay_gpu_dedicada(gpu_name):
        gpu_line = f"🎮 *Placa de Video:* {gpu_name} {gpu_descriptor(gpu_name)}"

    # RAM
    ram_line = format_ram_line(ram)
    if ram_line:
        # Replace label with bold
        ram_line = ram_line.replace("Memoria RAM:", "*Memoria RAM:*")
    # Insert RAM speed and positive message after ram_line
    ram_speed_line = ""
    # Try to extract MHz from RAM
    if ram:
        items = _list_items(ram)
        mhz = ""
        for it in items:
            name = (it.get("nombre") or "").lower()
            m_mhz = re.search(r"(\d{3,4})\s*mhz", name)
            if m_mhz:
                mhz = m_mhz.group(1)
                break
        if mhz:
            ram_speed_line = f"   – {mhz}MHz: velocidad ideal para gaming fluido y multitarea"
        else:
            ram_speed_line = "   – rendimiento optimizado para juegos y creación de contenido"

    ssd_line = format_ssd_line(ssd)
    if ssd_line:
        # Replace label with bold
        ssd_line = ssd_line.replace("Almacenamiento:", "*Almacenamiento:*")

    mb_line = f"🧩 *Motherboard:* {mb_name} (actualizable a futuro)" if mb_name else ""
    fuente_line = ""
    if fuente_name:
        tag = " – certificada 80 Plus (mejor eficiencia y estabilidad)" if "80 plus" in fuente_name.lower() else ""
        fuente_line = f"🔌 *Fuente:* {fuente_name}{tag}"
    gabi_line = f"🖤 *Gabinete:* {gabi_name}" if gabi_name else ""
    if gabi_line:
        gabi_line += " GAMING RGB"

    juegos    = juegos_recomendados(cpu_name, gpu_name)
    programas = programas_recomendados(cpu_name, gpu_name)
    cierre    = cierre_capacidades(cpu_name, gpu_name)

    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    partes = [
        "🔥 ¡PC GAMER COMPLETA LISTA PARA JUGAR Y TRABAJAR! 🔥",
        f"📅 Oferta válida al {fecha_hoy} — {NEGOCIO}",
        "",
        "💎 COMPONENTES DE ALTA GAMA Y ORIGINALES 💎",
        "",
        cpu_line
    ]
    if gpu_line: partes.append(gpu_line)
    if ram_line:
        partes.append(ram_line)
        if ram_speed_line:
            partes.append(ram_speed_line)
    if ssd_line: partes.append(ssd_line)
    if mb_line:  partes.append(mb_line)
    if fuente_line: partes.append(fuente_line)
    if gabi_line:
        gabi_line_full = f"{gabi_line} (gabinete con ventilación gaming e iluminación RGB)"
        partes.append(gabi_line_full)
    # Add explicit newlines after juegos and edición
    partes.append(f"🎮 Juegos: {juegos}\n")
    partes.append(f"🎨 Edición y creación: {programas}\n")
    partes.append(f"{cierre}\n")
    # Separator for WhatsApp copy/paste
    partes.append("-----------------")
    # INCLUYE SIN CARGO section
    partes += [
        "",
        "🎁 *INCLUYE GRATIS:*",
        "",
        "✅ Armado profesional y optimización (sistema estable: no se tilda)",
        "🪟 Windows 10/11 activado de por vida",
        "📦 Office completo",
        "📶 WiFi incluido",
        "⌨️ Teclado y mouse gamer RGB de regalo",
        f"🚚 Envío e instalación a domicilio ({CIUDAD})",
        "",
        "",
        "💰 PRECIOS Y FINANCIACIÓN 💳 (CUOTAS SOLO CON TARJETAS DE CREDITO BANCARIZADAS)",
        "",
        f"• *Efectivo/Transferencia/USD: {ars(contado)} 💵*",
        f"• *6 cuotas fijas de {ars_redondeado(cuota_6)}*",
        f"• *12 cuotas fijas de {ars_redondeado(cuota_12)}*",
        "",
        "🛒 Encargá tu equipo con una seña del 10% (aprox.) mediante efectivo o transferencia. Entrega inmediata o en 24hs según demanda y complejidad del armado.",
        "",
        "🛡️ 6 MESES DE GARANTÍA TOTAL",
        "",
        f"FACTURA TIPO C 📑",
        "",
        f"📍 *Retiro en zona centro (lista para usar) o pagas al recibir en tu domicilio GRATIS {CIUDAD}*",
        "",
    ]
    return "\n".join(partes)

def ars_redondeado(n):
    try:
        n = int(round(n))
        # Round up to nearest 1000
        remainder = n % 1000
        if remainder != 0:
            n = n + (1000 - remainder)
        return f"${n:,}".replace(",", ".")
    except:
        return str(n)

def _first_name(val) -> str:
    if isinstance(val, dict):
        return (val.get("nombre") or "").strip()
    if isinstance(val, list) and val:
        return (val[0].get("nombre") or "").strip()
    return ""

def _list_items(val):
    if isinstance(val, list): return val
    if isinstance(val, dict): return [val]
    return []

def format_ram_line(ram_val) -> str:
    items = _list_items(ram_val)
    if not items:
        return ""

    total_gb = 0
    per_stick_gb = []
    ddr_tag = ""
    mhz = ""
    for it in items:
        name = (it.get("nombre") or "").lower()
        g = _parse_gb(name)
        if g: 
            total_gb += g
            per_stick_gb.append(g)
        if not ddr_tag:
            m_ddr = re.search(r"(ddr\d)", name)
            if m_ddr:
                ddr_tag = m_ddr.group(1).upper()
        if not mhz:
            m_mhz = re.search(r"(\d{3,4})\s*mhz", name)
            if m_mhz:
                mhz = m_mhz.group(1)

    count = len(items)
    human_mhz = f" @{mhz}MHz" if mhz else ""
    if total_gb == 0:
        if count >= 2:
            suffix = f" (x{count}, Dual Channel)"
        else:
            suffix = f" (x{count})"
        base_name = (items[0].get("nombre") or "").strip()
        return f"⚡ Memoria RAM: {base_name}{suffix}"

    per_stick_pretty = ""
    if count >= 2:
        if len(set(per_stick_gb)) == 1:
            per_stick_pretty = f" ({count}x{per_stick_gb[0]}GB Dual Channel)"
        else:
            per_stick_pretty = f" (x{count} Dual Channel)"
    ddr_pretty = f" {ddr_tag}" if ddr_tag else ""
    return f"⚡ Memoria RAM: {total_gb}GB{ddr_pretty}{human_mhz}{per_stick_pretty}"

def _parse_gb(text: str):
    m = re.search(r"(\d{1,3})\s*gb", text, flags=re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except:
            return 0
    return 0

def format_ssd_line(ssd_val) -> str:
    items = _list_items(ssd_val)
    if not items:
        return ""

    total_gb = 0
    has_nvme = False
    names = []
    for it in items:
        name = (it.get("nombre") or "")
        names.append(name.strip())
        nlow = name.lower()
        cap = _parse_gb(nlow)
        total_gb += cap
        if ("m.2" in nlow) or ("nvme" in nlow):
            has_nvme = True

    tipo = "NVMe" if has_nvme else "SATA"
    total_pretty = _pretty_capacity(total_gb)
    count = len(items)
    if count == 1:
        return f"🚀 Almacenamiento: {names[0]}{ssd_tagline(names[0])}"
    return f"🚀 Almacenamiento: {total_pretty} {tipo} (x{count}, {'ultra rápido' if has_nvme else 'arranque rápido'})"

def _pretty_capacity(total_gb: int) -> str:
    if total_gb >= 1000:
        tb = total_gb / 1000.0
        if abs(round(tb) - tb) < 0.05:
            return f"{int(round(tb))}TB"
        return f"{tb:.1f}TB"
    return f"{total_gb}GB"

def ars(n):
    try: return f"${int(round(n)):,}".replace(",", ".")
    except: return str(n)

def hay_gpu_dedicada(gpu_name: str) -> bool:
    if not gpu_name: return False
    t = gpu_name.lower()
    return any(k in t for k in ["gtx", "rtx", "rx", "arc"])

def extraer_nucleos_hilos(cpu_name: str) -> str:
    n = (cpu_name or "").lower()
    m = re.search(r"(\d{1,2})\s*[cC]?\s*/\s*(\d{1,2})\s*[tT]?", n)
    if m:
        return f"{m.group(1)} Núcleos / {m.group(2)} Hilos"
    for c,t in [("16","32"),("12","24"),("10","20"),("8","16"),("6","12"),("4","8")]:
        if c in n and t in n:
            return f"{c} Núcleos / {t} Hilos"
    return ""

def extraer_ghz(cpu_name: str) -> str:
    vals = re.findall(r"(\d\.\d{1,2})\s*ghz", (cpu_name or "").lower())
    if vals:
        if len(vals) >= 2:
            return f", {vals[0]} GHz base / {vals[1]} GHz turbo"
        return f", {vals[0]} GHz"
    return ""

def ssd_tagline(ssd_name: str) -> str:
    t = (ssd_name or "").lower()
    if "m.2" in t or "nvme" in t: return " – ultra rápido"
    if "ssd" in t:                return " – arranque rápido"
    return ""

_GPU_DB = [
    (r"rtx\s*3070", {"vram":"8GB GDDR6", "tec":"Ampere", "cuda":"5888", "rt":True, "dlss":True, "orient":"1440p Ultra / 4K Medio"})
]

def gpu_descriptor(gpu_name: str) -> str:
    t = (gpu_name or "").lower()
    for pattern, meta in _GPU_DB:
        if re.search(pattern, t):
            parts = [f"({meta['vram']}, {meta['tec']}"]
            if meta.get("rt"):   parts.append("Ray Tracing")
            if meta.get("dlss"): parts.append("DLSS")
            if meta.get("cuda"): parts.append(f"CUDA {meta['cuda']}")
            parts.append(f"— {meta['orient']})")
            return " ".join(parts)
    return "(alto rendimiento en 1080p/1440p; compatibilidad con APIs modernas)"

def _is(cpu: str, *needles):
    s = (cpu or "").lower()
    return any(n in s for n in needles)

def juegos_recomendados(cpu_name: str, gpu_name: str) -> str:
    base = ["CS2", "LoL", "Fortnite", "GTA V"]
    if _is(cpu_name, "ryzen 3", "i3", "ryzen 5", "i5"):
        base = ["Minecraft", "Roblox"] + base
    if _is(cpu_name, "ryzen 7", "i7") or hay_gpu_dedicada(gpu_name):
        base += ["CoD Warzone", "Battlefield", "iRacing", "Assetto Corsa Competizione"]
    return ", ".join(base) + " y mucho más."

def programas_recomendados(cpu_name: str, gpu_name: str) -> str:
    if _is(cpu_name, "ryzen 3", "i3") and not hay_gpu_dedicada(gpu_name):
        return "Canva, CapCut, Filmora, Google Workspace y suite Office."
    pesados = ["Adobe Photoshop", "Premiere Pro", "After Effects", "DaVinci Resolve", "Blender"]
    if hay_gpu_dedicada(gpu_name) or _is(cpu_name, "ryzen 5", "i5", "ryzen 7", "i7"):
        return ", ".join(pesados) + " (fluido, incluso proyectos exigentes)."
    return "Canva, CapCut y edición fotográfica básica con fluidez."

def cierre_capacidades(cpu_name: str, gpu_name: str) -> str:
    if hay_gpu_dedicada(gpu_name):
        return "🎯 *Gaming en ULTRA, edición 4K, streaming y creación de contenido profesional sin límites.*"
    if _is(cpu_name, "ryzen 7", "i7"):
        return "🎯 *Gaming en ultra, edición profesional, streaming y multitarea intensa.*"
    if _is(cpu_name, "ryzen 5", "i5"):
        return "🎯 *Gaming en alta calidad, competitivo online, edición de video y fotos con gran fluidez.*"
    if _is(cpu_name, "ryzen 3", "i3"):
        return "🎯 *Ideal para jugar en buena calidad, edición en Canva o CapCut y trabajo/estudio fluido.*"
    return "🎯 *PC versátil para gaming, trabajo y creación de contenido.*"