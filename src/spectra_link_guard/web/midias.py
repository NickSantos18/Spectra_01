"""Validação completa e recodificação de imagens antes da persistência."""
from io import BytesIO
import warnings
from threading import BoundedSemaphore
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS=16_000_000
FORMATOS={'image/png':'PNG','image/jpeg':'JPEG','image/webp':'WEBP'}
_PROCESSAMENTO=BoundedSemaphore(2)


class ImagemOcupada(Exception):
    """Evita que múltiplas descompressões esgotem a memória do servidor."""

def validar_imagem(raw,mime,*,max_dimensao=4096):
    if not _PROCESSAMENTO.acquire(blocking=False):
        raise ImagemOcupada('Muitas imagens em processamento. Tente novamente.')
    try:
        return _validar_imagem(raw,mime,max_dimensao=max_dimensao)
    finally:
        _PROCESSAMENTO.release()


def _validar_imagem(raw,mime,*,max_dimensao):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as im:
                if im.format!=FORMATOS.get(mime) or im.width>max_dimensao or im.height>max_dimensao or getattr(im,'n_frames',1)!=1:
                    raise ValueError('Formato ou dimensões inválidos.')
                im.verify()
            with Image.open(BytesIO(raw)) as im:
                im.load()
                limpa=im.convert('RGBA' if mime=='image/png' else 'RGB')
                saida=BytesIO()
                limpa.save(saida,format=FORMATOS[mime])
                return saida.getvalue()
    except (UnidentifiedImageError,OSError,SyntaxError,Image.DecompressionBombError,Image.DecompressionBombWarning) as e:
        raise ValueError('Imagem inválida ou excessivamente grande.') from e
