from pathlib import Path
import hashlib
import sys


def convert_smd(data: bytes) -> bytes:
    """Converte uma ROM SMD para BIN."""

    if len(data) < 0x200:
        raise ValueError("Arquivo SMD muito pequeno.")

    # Remove o header SMD de 512 bytes
    data = data[0x200:]

    output = bytearray()

    # Processa os blocos de 0x4000 bytes
    for block_start in range(0, len(data), 0x4000):
        block = data[block_start:block_start + 0x4000]

        if len(block) != 0x4000:
            raise ValueError(
                f"Bloco SMD incompleto em 0x{block_start:X}."
            )

        # Desinterleave
        for i in range(0, len(block), 2):
            output.append(block[0x2000 + i // 2])
            output.append(block[i // 2])

    return bytes(output)


def convert_rom(input_file: Path) -> bytes:
    """Converte SMD/MD/BIN para BIN."""

    extension = input_file.suffix.lower()
    data = input_file.read_bytes()

    if extension == ".smd":
        return convert_smd(data)

    if extension in (".md", ".bin"):
        return data

    raise ValueError(
        f"Formato não suportado: {extension}"
    )


def main():
    print("================================")
    print("       TMT MegaComp")
    print("      ROM Converter")
    print("================================")
    print()

    # Permite passar a ROM como argumento:
    #
    # MegaCompROMConv.exe "Sonic 3.smd"
    #
    if len(sys.argv) >= 2:
        input_path = Path(sys.argv[1])

    else:
        input_path = Path(
            input("Digite o caminho da ROM:\n> ").strip('" ')
        )

    if not input_path.exists():
        print()
        print("ERRO: arquivo não encontrado.")
        return 1

    if not input_path.is_file():
        print()
        print("ERRO: o caminho informado não é um arquivo.")
        return 1

    extension = input_path.suffix.lower()

    if extension not in (".smd", ".md", ".bin"):
        print()
        print(f"ERRO: formato não suportado: {extension}")
        return 1

    print(f"ROM: {input_path.name}")
    print(f"Formato detectado: {extension[1:].upper()}")
    print(f"Tamanho original: {input_path.stat().st_size:,} bytes")
    print()

    try:
        output = convert_rom(input_path)

    except Exception as error:
        print(f"ERRO durante a conversão: {error}")
        return 1

    # Nome padrão do BIN
    output_file = input_path.with_suffix(".bin")

    # Caso o usuário tenha passado um segundo argumento:
    #
    # MegaCompROMConv.exe "Sonic 3.md" "S3.bin"
    #
    if len(sys.argv) >= 3:
        output_file = Path(sys.argv[2])

    print("Convertendo...")

    output_file.write_bytes(output)

    md5 = hashlib.md5(output).hexdigest()

    print()
    print("Arquivo criado:")
    print(output_file)
    print()
    print(f"Tamanho: {len(output):,} bytes")
    print(f"MD5:     {md5}")
    print()
    print("Concluído!")

    return 0


if __name__ == "__main__":
    sys.exit(main())

