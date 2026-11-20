"""One conversion at a time in a networkless, credential-free container."""
import os
import signal
import socketserver
import subprocess
import tempfile
import zipfile
from pathlib import Path
from io import BytesIO

LIMIT = 10 * 1024 * 1024


def convert(data):
    with zipfile.ZipFile(BytesIO(data)) as archive:
        files = archive.infolist()
        names = set(archive.namelist())
        if (not {'[Content_Types].xml', 'ppt/presentation.xml'} <= names
                or len(files) > 4000 or sum(f.file_size for f in files) > 80 * 1024**2
                or any('vbaproject' in n.lower() or n.lower().startswith('ppt/embeddings/') for n in names)):
            raise ValueError('unsupported presentation')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / 'slides.pptx'
        source.write_bytes(data)
        proc = subprocess.Popen(['soffice', '-env:UserInstallation=' + (root / 'profile').as_uri(),
                                 '--headless', '--convert-to', 'pdf:impress_pdf_Export', '--outdir',
                                 tmp, str(source)], start_new_session=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            if proc.wait(timeout=35):
                raise ValueError('conversion failed')
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise ValueError('conversion timed out') from None
        output = source.with_suffix('.pdf')
        if not output.is_file() or output.stat().st_size > LIMIT:
            raise ValueError('invalid output')
        return output.read_bytes()


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(10)
        try:
            size = int.from_bytes(self.rfile.read(4), 'big')
            if not 0 < size <= LIMIT:
                raise ValueError()
            data = self.rfile.read(size)
            if len(data) != size:
                raise ValueError()
            pdf = convert(data)
        except (ValueError, OSError, zipfile.BadZipFile):
            pdf = b''
        self.wfile.write(len(pdf).to_bytes(4, 'big') + pdf)


if __name__ == '__main__':
    path = os.getenv('QB_PPTX_SOCKET', '/ipc/pptx.sock')
    Path(path).unlink(missing_ok=True)
    with socketserver.UnixStreamServer(path, Handler) as server:
        os.chmod(path, 0o660)
        server.serve_forever()
