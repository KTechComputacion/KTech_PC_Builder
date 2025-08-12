# scraper.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import os
import config
import time

VERDE = '\033[92m'
ROJO = '\033[91m'
RESET = '\033[0m'


# --- LOGIN ---
def login(driver):
    driver.get(config.LOGIN_URL)

    driver.find_element(By.NAME, "usuario").send_keys(config.USERNAME)
    driver.find_element(By.NAME, "password").send_keys(config.PASSWORD)
    driver.find_element(By.NAME, "submit").click()

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print(VERDE + "[OK] Login (elemento detectado)" + RESET)
    except:
        print(ROJO + "[ADVERTENCIA] No se detectó elemento, pero continuamos" + RESET)


# --- SCRAPER DE PRODUCTO ---
def obtener_datos_producto(driver, codigo_producto):
    try:
        url_producto = config.construir_url_producto(codigo_producto)
        driver.get(url_producto)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pr_price"))
        )

        titulo_completo = driver.title
        nombre_limpio = titulo_completo.split('|')[0].strip()

        precio_texto_completo = driver.find_element(By.CLASS_NAME, "pr_price").text
        primera_linea_precio = precio_texto_completo.split('\n')[0]
        precio_sin_simbolo = primera_linea_precio.replace('$', '').strip()
        precio_sin_coma = precio_sin_simbolo.replace(',', '')
        precio_final_str = precio_sin_coma.split('.')[0]
        precio = int(precio_final_str)

        stock_elemento = driver.find_element(By.XPATH, "//font[contains(., 'DISPONIBLES:')]")
        stock_texto = stock_elemento.find_element(By.XPATH, ".//strong").text
        stock = int(stock_texto.replace('DISPONIBLES:', '').strip())

        return {
            "nombre": nombre_limpio,
            "codigo": codigo_producto,
            "precio": precio,
            "stock": stock
        }

    except Exception as e:
        print(ROJO + f"ERROR durante el scraping: {e}" + RESET)
        return None


# --- GUARDADO ---
def guardar_en_json(datos_producto, categoria):
    archivo_json = 'stock.json'
    stock_completo = {}

    if os.path.exists(archivo_json):
        with open(archivo_json, 'r', encoding='utf-8') as f:
            try:
                stock_completo = json.load(f)
            except json.JSONDecodeError:
                pass

    if categoria not in stock_completo:
        stock_completo[categoria] = []

    producto_encontrado = False
    for i, producto_existente in enumerate(stock_completo[categoria]):
        if producto_existente["codigo"] == datos_producto["codigo"]:
            stock_completo[categoria][i] = datos_producto
            producto_encontrado = True
            break

    if not producto_encontrado:
        stock_completo[categoria].append(datos_producto)

    with open(archivo_json, 'w', encoding='utf-8') as f:
        json.dump(stock_completo, f, indent=4, ensure_ascii=False)

    print(VERDE + f"--- DATOS GUARDADOS EN CATEGORÍA: {categoria} ---" + RESET)


# --- EJECUCIÓN ---
if __name__ == "__main__":
    print("--- INICIANDO KTECH STOCK UPDATER (CHROME, UNA SOLA SESIÓN) ---")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    login(driver)
    time.sleep(3)  # Espera para que la sesión quede activa

    for categoria, productos in config.CATEGORIAS.items():
        for nombre_clave, codigo in productos.items():
            print(f"\nProcesando {categoria} - {nombre_clave} (Código: {codigo})...")
            datos = obtener_datos_producto(driver, codigo)
            if datos:
                guardar_en_json(datos, categoria)

    driver.quit()
    print("\n--- PROCESO FINALIZADO ---")
