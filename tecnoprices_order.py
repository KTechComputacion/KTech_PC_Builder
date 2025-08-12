# technoprices_order.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import config

# ===== Helpers de espera / click robustos =====

def wv(driver, by, sel, t=12):
    return WebDriverWait(driver, t).until(EC.visibility_of_element_located((by, sel)))

def wec(driver, by, sel, t=12):
    return WebDriverWait(driver, t).until(EC.element_to_be_clickable((by, sel)))

def click_candidates(driver, candidates, t=12):
    """
    Intenta hacer click con una lista de selectores (By, locator).
    Retorna True si alguno funcionó.
    """
    for by, sel in candidates:
        try:
            wec(driver, by, sel, t).click()
            return True
        except Exception:
            continue
    return False

# ===== Login =====

def login(driver):
    driver.get(config.LOGIN_URL)
    wv(driver, By.NAME, "usuario").send_keys(config.USERNAME)
    wv(driver, By.NAME, "password").send_keys(config.PASSWORD)
    wec(driver, By.NAME, "submit").click()
    WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(0.5)

# ===== Flujo de compra por código =====

def add_product_by_codigo(driver, codigo, cantidad=1):
    """
    Abre la página de producto por código y hace click en 'COMPRAR'.
    URL típica: https://www.tecnoprices.com/detail.php?codigo=XXXX
    (A veces hay URL "bonita", pero con 'codigo' funciona igual)
    """
    url = config.construir_url_producto(str(codigo))
    driver.get(url)

    # Esperar que cargue ficha
    wv(driver, By.CLASS_NAME, "pr_price")

    # Si existe input de cantidad, setear
    try:
        qty = driver.find_element(By.NAME, "cantidad")
        qty.clear()
        qty.send_keys(str(cantidad))
        time.sleep(0.2)
    except Exception:
        pass

    # Botón COMPRAR (probamos por texto y por clases comunes)
    clicked = click_candidates(driver, [
        (By.XPATH, "//button[contains(translate(., 'comprar', 'COMPRAR'), 'COMPRAR')]"),
        (By.XPATH, "//a[contains(translate(., 'comprar', 'COMPRAR'), 'COMPRAR')]"),
        (By.CSS_SELECTOR, "button.btn.btn-primary"),
        (By.CSS_SELECTOR, "a.btn.btn-primary"),
    ])
    if not clicked:
        raise RuntimeError(f"No se encontró botón COMPRAR en producto {codigo}")

    time.sleep(0.6)  # pequeña espera por animación/alerta

def go_to_cart(driver):
    driver.get("https://www.tecnoprices.com/cart.php")
    wv(driver, By.TAG_NAME, "body")
    # Botón TERMINAR COMPRA
    clicked = click_candidates(driver, [
        (By.XPATH, "//a[contains(translate(., 'terminar compra', 'TERMINAR COMPRA'), 'TERMINAR COMPRA')]"),
        (By.XPATH, "//button[contains(translate(., 'terminar compra', 'TERMINAR COMPRA'), 'TERMINAR COMPRA')]"),
        (By.XPATH, "//a[contains(.,'Finalizar') or contains(.,'Checkout')]"),
    ])
    if not clicked:
        raise RuntimeError("No se encontró botón TERMINAR COMPRA en el carrito")
    time.sleep(0.4)

def checkout_step_1(driver):
    # /checkout.php → botón CONTINUAR
    WebDriverWait(driver, 10).until(EC.url_contains("checkout.php"))
    clicked = click_candidates(driver, [
        (By.XPATH, "//button[contains(translate(., 'continuar', 'CONTINUAR'), 'CONTINUAR')]"),
        (By.XPATH, "//a[contains(translate(., 'continuar', 'CONTINUAR'), 'CONTINUAR')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ])
    if not clicked:
        raise RuntimeError("No se encontró botón CONTINUAR en checkout.php")
    time.sleep(0.4)

def checkout_step_2_facturacion(driver, opcion_texto="NO REQUIERE - DECIDIR DESPUES"):
    # /checkout2.php → seleccionar opción en el desplegable y confirmar
    WebDriverWait(driver, 10).until(EC.url_contains("checkout2.php"))

    # Intentar localizar el <select> de facturación.
    # Ajustá el name/id si ves el HTML (por ej. name="facturacion", id="fact_sel"...)
    posibles_selects = [
        (By.NAME, "facturacion"),
        (By.ID, "facturacion"),
        (By.CSS_SELECTOR, "select"),
    ]
    select_el = None
    for by, sel in posibles_selects:
        try:
            select_el = wv(driver, by, sel, 6)
            if select_el.tag_name.lower() == "select":
                break
        except Exception:
            continue
    if select_el is None or select_el.tag_name.lower() != "select":
        raise RuntimeError("No se encontró el selector de facturación (select) en checkout2.php")

    # Seleccionar por texto visible (lo que mostraste en la captura)
    s = Select(select_el)

    # Primera prueba: texto completo con asteriscos
    intentos = [
        "* NO REQUIERE - DECIDIR DESPUES *",
        "NO REQUIERE - DECIDIR DESPUES",
        "NO REQUIERE",
        opcion_texto,
    ]
    selected = False
    for txt in intentos:
        try:
            s.select_by_visible_text(txt)
            selected = True
            break
        except Exception:
            continue

    if not selected:
        # Fallback: elegir la primera opción que contenga 'NO REQUIERE'
        for opt in s.options:
            if "no requiere" in opt.text.lower():
                opt.click()
                selected = True
                break

    if not selected:
        raise RuntimeError("No se pudo seleccionar la opción de 'NO REQUIERE - DECIDIR DESPUES'")

    time.sleep(0.2)

    # Confirmar compra
    clicked = click_candidates(driver, [
        (By.XPATH, "//button[contains(translate(., 'confirmar compra', 'CONFIRMAR COMPRA'), 'CONFIRMAR COMPRA')]"),
        (By.XPATH, "//button[contains(., 'Confirmar')]"),
        (By.XPATH, "//a[contains(., 'Confirmar')]"),
    ])
    if not clicked:
        raise RuntimeError("No se encontró botón CONFIRMAR COMPRA en checkout2.php")

    # Esperar respuesta / página final
    time.sleep(1.0)

# ===== Orquestador =====

def place_order(codigos_cantidades, headless=True):
    """
    codigos_cantidades: lista de tuplas (codigo, cantidad)
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:
        login(driver)
        for codigo, qty in codigos_cantidades:
            add_product_by_codigo(driver, codigo, qty)
        # carrito → terminar compra
        go_to_cart(driver)
        # checkout.php → continuar
        checkout_step_1(driver)
        # checkout2.php → seleccionar "NO REQUIERE..." → confirmar
        checkout_step_2_facturacion(driver)
        print("[OK] Pedido confirmado en Technoprices.")
    finally:
        driver.quit()


# Prueba directa
if __name__ == "__main__":
    place_order([("18986", 1)], headless=False)
