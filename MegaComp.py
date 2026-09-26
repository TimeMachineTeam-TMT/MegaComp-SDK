from pathlib import Path
from SCRIPT.rom_to_bin import convert
from SCRIPT.disassembler import disassemble
from SCRIPT.analyzer import analyze
from SCRIPT.codegen import generate


ROOT_DIR = Path(__file__).resolve().parent

PROJECTS_DIR = ROOT_DIR / "PROJECTS"
OUTPUT_DIR = ROOT_DIR / "OUTPUT"


def print_header():
    print()
    print("========================================")
    print("             TMT MegaComp")
    print("========================================")
    print()


def ask_path():
    while True:
        path = input("Path da ROM:\n> ").strip().strip('"')

        if not path:
            print("ERRO: nenhum caminho informado.\n")
            continue

        path = Path(path)

        if not path.exists():
            print("ERRO: arquivo não encontrado.\n")
            continue

        if not path.is_file():
            print("ERRO: o caminho informado não é um arquivo.\n")
            continue

        return path


def ask_name(text, default):
    name = input(f"\n{text} [{default}]:\n> ").strip()

    if not name:
        name = default

    return name


def main():

    print_header()

    # ==============================
    # CONFIGURAÇÃO
    # ==============================

    rom_path = ask_path()

    default_name = rom_path.stem

    project_name = ask_name(
        "Nome da pasta do projeto",
        default_name
    )

    output_name = ask_name(
        "Nome do executável",
        default_name
    )

    if output_name.lower().endswith(".exe"):
        output_name = output_name[:-4]

    # ==============================
    # DIRETÓRIOS
    # ==============================

    project_dir = PROJECTS_DIR / project_name
    output_dir = OUTPUT_DIR

    project_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("----------------------------------------")
    print("Projeto")
    print("----------------------------------------")
    print(f"ROM:     {rom_path}")
    print(f"Projeto: {project_dir}")
    print(f"Output:  {output_dir / (output_name + '.exe')}")
    print()

    # ==============================
    # ROM → BIN
    # ==============================

    print("----------------------------------------")
    print("Etapa 1: ROM → BIN")
    print("----------------------------------------")

    bin_path = convert(rom_path, project_dir)

    # ==============================
    # BIN → 68000 ASM
    # ==============================

    print()
    print("----------------------------------------")
    print("Etapa 2: BIN → 68000 ASM")
    print("----------------------------------------")

    asm_path = disassemble(bin_path, project_dir)

    # ==============================
    # ANÁLISE
    # ==============================

    print()
    print("----------------------------------------")
    print("Etapa 3: Análise")
    print("----------------------------------------")

    analysis = analyze(asm_path, bin_path)

    # ==============================
    # CODEGEN
    # ==============================

    print()
    print("----------------------------------------")
    print("Etapa 4: 68000 → x86-64")
    print("----------------------------------------")

    win_asm_path = generate(analysis, project_dir)

    # ==============================
    # BUILD
    # ==============================

    print()
    print("----------------------------------------")
    print("Etapa 5: Build")
    print("----------------------------------------")

    # Futuramente:
    # build.build(win_asm_path, output_dir, output_name)

    print()
    print("========================================")
    print("       MegaComp concluído!")
    print("========================================")


if __name__ == "__main__":
    main()