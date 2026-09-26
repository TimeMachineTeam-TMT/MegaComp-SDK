from pathlib import Path
import hashlib


def convert(input_path, project_dir):
    """
    Converte uma ROM Mega Drive para BIN.

    Suporta:
        .md  -> já está em formato BIN
        .bin -> já está em formato BIN
        .smd -> remove header e desintercala

    Retorna:
        Path do arquivo .bin criado.
    """

    input_path = Path(input_path)
    project_dir = Path(project_dir)

    # Nome do BIN
    output_path = project_dir / f"{input_path.stem}.bin"

    # Lê a ROM
    data = input_path.read_bytes()

    extension = input_path.suffix.lower()

    # ==========================================
    # MD / BIN
    # ==========================================

    if extension in (".md", ".bin"):
        output = data

    # ==========================================
    # SMD
    # ==========================================

    elif extension == ".smd":

        if len(data) < 0x200:
            raise ValueError(
                "Arquivo SMD muito pequeno para possuir header."
            )

        # Remove o header SMD
        data = data[0x200:]

        output = bytearray()

        # Desintercala os blocos SMD
        for block_start in range(0, len(data), 0x4000):

            block = data[
                block_start:
                block_start + 0x4000
            ]

            # Cada bloco SMD possui os bytes
            # pares/ímpares separados.
            for i in range(0, len(block), 2):

                output.append(
                    block[0x2000 + i // 2]
                )

                output.append(
                    block[i // 2]
                )

        output = bytes(output)

    # ==========================================
    # FORMATO DESCONHECIDO
    # ==========================================

    else:
        raise ValueError(
            f"Formato de ROM não suportado: {extension}"
        )

    # ==========================================
    # SALVA BIN
    # ==========================================

    output_path.write_bytes(output)

    # ==========================================
    # INFORMAÇÕES
    # ==========================================

    md5 = hashlib.md5(output).hexdigest()

    print(f"Arquivo criado: {output_path}")
    print(f"Tamanho: {len(output):,} bytes")
    print(f"MD5: {md5}")

    return output_path