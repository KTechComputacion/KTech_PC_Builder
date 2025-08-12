# --- BASE DE DATOS DE COMPONENTES (COSTO) ---
# Aquí guardamos los componentes y su precio de costo.
# Más adelante, esto vendrá de la web del distribuidor.

procesadores = {
    "Ryzen 5 4600G": 150000,
    "Ryzen 7 5700G": 250000,
    "Intel Core i5-12400F": 180000,
}

memorias_ram = {
    "16GB (2x8GB) DDR4 3200MHz": 50000,
    "32GB (2x16GB) DDR4 3600MHz": 90000,
}

almacenamiento = {
    "SSD 512GB NVMe M.2": 45000,
    "SSD 1TB NVMe M.2": 70000,
}

fuentes_poder = {
    "Fuente 600W 80+ Bronze": 60000,
    "Fuente 750W 80+ Gold": 95000,
}

gabinetes = {
    "Gabinete Gamer Standard (con 3 coolers)": 55000,
    "Gabinete Premium (con 6 coolers RGB)": 80000,
}


# --- LÓGICA DE CÁLCULO ---

# 1. SIMULAMOS UNA SELECCIÓN DE COMPONENTES
# Más adelante, esto lo elegirá el usuario en la interfaz gráfica.
# Por ahora, lo escribimos nosotros para probar.
pc_seleccionada = {
    "procesador": "Ryzen 7 5700G",
    "ram": "16GB (2x8GB) DDR4 3200MHz",
    "almacenamiento": "SSD 1TB NVMe M.2",
    "fuente": "Fuente 600W 80+ Bronze",
    "gabinete": "Gabinete Premium (con 6 coolers RGB)"
}


# 2. FUNCIÓN PARA CALCULAR EL COSTO TOTAL
# Esta función recibe una selección de componentes y devuelve la suma de sus costos.
def calcular_costo_total(seleccion):
    """Calcula el costo sumando los precios de los componentes seleccionados."""
    
    # Buscamos el precio de cada componente en nuestras "bases de datos"
    costo_cpu = procesadores[seleccion["procesador"]]
    costo_ram = memorias_ram[seleccion["ram"]]
    costo_ssd = almacenamiento[seleccion["almacenamiento"]]
    costo_fuente = fuentes_poder[seleccion["fuente"]]
    costo_gabinete = gabinetes[seleccion["gabinete"]]
    
    # Sumamos todos los costos
    costo_total = costo_cpu + costo_ram + costo_ssd + costo_fuente + costo_gabinete
    
    return costo_total


# 3. EJECUTAMOS LA FUNCIÓN Y MOSTRAMOS EL RESULTADO
# Llamamos a la función con nuestra pc_seleccionada y guardamos el resultado.
costo_final_pc = calcular_costo_total(pc_seleccionada)

# Imprimimos el resultado en la terminal de una forma clara.
print("--- Presupuesto KTech Tool ---")
print(f"Componentes Seleccionados: {pc_seleccionada}")
print(f"COSTO TOTAL DE LOS COMPONENTES: ${costo_final_pc}")

