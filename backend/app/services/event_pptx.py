import os
import socket

from app.services.event_pdf import MAX_PDF_BYTES


def pptx_to_pdf(data):
    if not data.startswith(b'PK') or len(data) > MAX_PDF_BYTES:
        raise ValueError('invalid presentation')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(45)
        sock.connect(os.environ.get('QB_PPTX_SOCKET', '/ipc/pptx.sock'))
        sock.sendall(len(data).to_bytes(4, 'big') + data)
        with sock.makefile('rb') as stream:
            header = stream.read(4)
            if len(header) != 4:
                raise OSError('converter disconnected')
            size = int.from_bytes(header, 'big')
            if not 0 < size <= MAX_PDF_BYTES:
                raise ValueError('invalid presentation')
            pdf = stream.read(size)
            if len(pdf) != size:
                raise OSError('incomplete conversion')
            return pdf
