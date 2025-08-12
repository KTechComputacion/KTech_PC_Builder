import os

def main():
    print("🔍 Archivos modificados / nuevos:")
    os.system("git status -s")

    confirm = input("\n¿Querés continuar y subir estos cambios? (s/n): ").strip().lower()
    if confirm != "s":
        print("❌ Operación cancelada.")
        return

    commit_message = input("\n📌 Escribí el mensaje del commit: ").strip()
    if not commit_message:
        print("❌ El mensaje de commit no puede estar vacío.")
        return

    os.system("git add -A")
    os.system(f'git commit -m "{commit_message}"')
    os.system("git push origin main")

if __name__ == "__main__":
    main()
