from pathlib import Path
import subprocess


def convert_wav_to_ogg(input_wav: Path, output_ogg: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_wav),
            "-c:a",
            "libopus",
            "-b:a",
            "64k",
            "-vbr",
            "on",
            str(output_ogg),
        ],
        check=True,
    )
