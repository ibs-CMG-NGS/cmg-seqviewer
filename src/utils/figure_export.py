"""중앙 figure export — mm 단위 사이징, DPI, 편집 가능한 벡터."""
from pathlib import Path
import matplotlib as mpl

MM_PER_INCH = 25.4
JOURNAL_WIDTH_MM = {'single': 85.0, 'one-half': 114.0, 'double': 170.0}
VECTOR = {'pdf', 'svg', 'eps'}
RASTER = {'png', 'tiff', 'tif', 'jpg', 'jpeg'}

# 편집 가능한 벡터 텍스트 보장 (테마 밖에서 호출돼도 안전)
_VECTOR_RC = {'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none'}


def filter_string() -> str:
    """QFileDialog용 필터 문자열 반환."""
    return (
        "PDF Files (*.pdf);;"
        "SVG Files (*.svg);;"
        "PNG Files (*.png);;"
        "TIFF Files (*.tiff);;"
        "EPS Files (*.eps);;"
        "All Files (*)"
    )


def save_figure(fig, path, fmt: str = None,
                dpi: int = 300, size_mm: tuple = None,
                transparent: bool = False) -> Path:
    """figure를 저장한다. size_mm 지정 시 저장 후 원래 크기로 복원."""
    path = Path(path)
    fmt = (fmt or path.suffix.lstrip('.') or 'png').lower()
    if not path.suffix:
        path = path.with_suffix('.' + fmt)

    supported = fig.canvas.get_supported_filetypes()
    if fmt not in supported:
        raise ValueError(
            f"Unsupported format '{fmt}'. "
            f"Supported: {', '.join(sorted(supported))}"
        )

    if fmt == 'eps' and transparent:
        transparent = False  # EPS는 투명도 미지원

    old_size = fig.get_size_inches()
    try:
        if size_mm:
            fig.set_size_inches(size_mm[0] / MM_PER_INCH, size_mm[1] / MM_PER_INCH)

        kwargs = dict(bbox_inches='tight', transparent=transparent)
        if fmt in RASTER:
            kwargs['dpi'] = dpi
        with mpl.rc_context(_VECTOR_RC):
            fig.savefig(path, format=fmt, **kwargs)
    finally:
        fig.set_size_inches(*old_size)

    return path
