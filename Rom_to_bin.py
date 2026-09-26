
from pathlib import Path
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox


def convert_smd(data: bytes) -> bytes:
    """
    Converte uma ROM SMD para BIN.
    Remove o header de 512 bytes e desfaz o interleaving.
    """

    # SMD possui um header de 512 bytes.
    if len(data) < 0x200:
        raise ValueError("Arquivo SMD muito pequeno.")

    data = data[0x200:]

    output = bytearray()

    # Processa os blocos SMD de 0x4000 bytes.
    for block_start in range(0, len(data), 0x4000):
        block = data[block_start:block_start + 0x4000]

        # Um bloco incompleto não deve ser processado como SMD.
        if len(block) != 0x4000:
            raise ValueError(
                f"Bloco SMD incompleto em 0x{block_start:X}."
            )

        # SMD armazena os bytes pares/ímpares separados.
        for i in range(0, len(block), 2):
            output.append(block[0x2000 + i // 2])
            output.append(block[i // 2])

    return bytes(output)


def convert_rom(input_file: Path) -> bytes:
    """
    Converte uma ROM .SMD, .MD ou .BIN para BIN.
    """

    extension = input_file.suffix.lower()
    data = input_file.read_bytes()

    if extension == ".smd":
        return convert_smd(data)

    elif extension in (".md", ".bin"):
        # .MD e .BIN são tratados como ROM binária normal.
        return data

    else:
        raise ValueError(
            f"Formato não suportado: {input_file.suffix}"
        )


def main():
    root = tk.Tk()
    root.withdraw()

    # Selecionar ROM
    input_path = filedialog.askopenfilename(
        title="Selecione uma ROM do Mega Drive",
        filetypes=[
            (
                "ROMs do Mega Drive",
                "*.smd *.md *.bin"
            ),
            ("SMD", "*.smd"),
            ("MD", "*.md"),
            ("BIN", "*.bin"),
            ("Todos os arquivos", "*.*"),
        ],
    )

    if not input_path:
        return

    input_file = Path(input_path)

    # Nome padrão do arquivo de saída
    output_file = input_file.with_suffix(".bin")

    # Se a entrada já for BIN, perguntar onde salvar
    if input_file.suffix.lower() == ".bin":
        output_path = filedialog.asksaveasfilename(
            title="Salvar BIN",
            initialfile=input_file.name,
            defaultextension=".bin",
            filetypes=[
                ("BIN", "*.bin"),
                ("Todos os arquivos", "*.*"),
            ],
        )

        if not output_path:
            return

        output_file = Path(output_path)

    try:
        # Converter
        output = convert_rom(input_file)

        # Salvar
        output_file.write_bytes(output)

        # Calcular MD5
        md5 = hashlib.md5(output).hexdigest()

        message = (
            "ROM convertida com sucesso!\n\n"
            f"Entrada:\n{input_file.name}\n\n"
            f"Saída:\n{output_file.name}\n\n"
            f"Tamanho: {len(output):,} bytes\n"
            f"MD5: {md5}"
        )

        print(message)

        messagebox.showinfo(
            "MegaComp ROM Converter",
            message
        )

    except Exception as error:
        messagebox.showerror(
            "Erro",
            f"Não foi possível converter a ROM:\n\n{error}"
        )


if __name__ == "__main__":
    main()

