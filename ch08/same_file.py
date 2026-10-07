from pathlib import Path


class UnmeasurablePath(RuntimeError):
    pass


def same_file(path_a: Path, path_b: Path) -> bool:
    """이름이 아니라 (device, inode)로 두 경로가 같은 파일인지 확인한다."""
    try:
        stat_a = path_a.stat()
        stat_b = path_b.stat()
    except OSError:
        raise UnmeasurablePath(f"{path_a} 또는 {path_b}를 조회할 수 없다")
    return (stat_a.st_dev, stat_a.st_ino) == (stat_b.st_dev, stat_b.st_ino)
