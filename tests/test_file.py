from pathlib import Path

import pytest

from python_multipart.exceptions import FileError
from python_multipart.multipart import File


def test_upload_dir_with_leading_slash_in_filename(tmp_path: Path) -> None:
    upload_dir = tmp_path / "upload"
    upload_dir.mkdir()

    # When the file_name provided has a leading slash, we should only use the basename.
    # This is to avoid directory traversal.
    to_upload = tmp_path / "foo.txt"

    file = File(
        bytes(to_upload),
        config={
            "UPLOAD_DIR": bytes(upload_dir),
            "UPLOAD_KEEP_FILENAME": True,
            "UPLOAD_KEEP_EXTENSIONS": True,
            "MAX_MEMORY_FILE_SIZE": 10,
        },
    )
    file.write(b"123456789012")
    assert not file.in_memory
    assert Path(upload_dir / "foo.txt").exists()
    assert Path(upload_dir / "foo.txt").read_bytes() == b"123456789012"


def test_str_upload_dir_with_keep_filename(tmp_path: Path) -> None:
    file = File(
        b"foo.txt",
        config={
            "UPLOAD_DIR": str(tmp_path),
            "UPLOAD_KEEP_FILENAME": True,
            "UPLOAD_KEEP_EXTENSIONS": True,
            "MAX_MEMORY_FILE_SIZE": 10,
        },
    )
    file.write(b"123456789012")
    file.close()

    assert not file.in_memory
    assert file.actual_file_name == b"foo.txt"
    assert (tmp_path / "foo.txt").read_bytes() == b"123456789012"


def test_keep_extensions_without_filename() -> None:
    # An application/octet-stream upload has no filename; keeping the
    # extension must not fail when the file moves to disk.
    file = File(None, config={"UPLOAD_KEEP_EXTENSIONS": True, "MAX_MEMORY_FILE_SIZE": 10})
    file.write(b"123456789012")
    assert not file.in_memory
    assert file.actual_file_name is not None


def test_keep_filename_without_filename(tmp_path: Path) -> None:
    # Without a filename to keep, the file goes to a temporary name in UPLOAD_DIR.
    file = File(
        None,
        config={
            "UPLOAD_DIR": bytes(tmp_path),
            "UPLOAD_KEEP_FILENAME": True,
            "UPLOAD_KEEP_EXTENSIONS": True,
            "UPLOAD_DELETE_TMP": False,
            "MAX_MEMORY_FILE_SIZE": 10,
        },
    )
    file.write(b"123456789012")
    file.close()
    assert not file.in_memory
    assert file.actual_file_name is not None
    assert Path(file.actual_file_name.decode()).parent == tmp_path
    assert Path(file.actual_file_name.decode()).read_bytes() == b"123456789012"


def test_nul_in_kept_filename_raises_file_error(tmp_path: Path) -> None:
    # A NUL in the kept filename must surface as FileError when flushing to disk.
    file = File(
        b"a\x00.txt",
        config={
            "UPLOAD_DIR": str(tmp_path),
            "UPLOAD_KEEP_FILENAME": True,
            "UPLOAD_KEEP_EXTENSIONS": True,
            "MAX_MEMORY_FILE_SIZE": 10,
        },
    )
    with pytest.raises(FileError):
        file.write(b"123456789012")


def test_nul_in_extension_raises_file_error() -> None:
    # A NUL in the kept extension must surface as FileError from NamedTemporaryFile.
    file = File(b"a.tx\x00t", config={"UPLOAD_KEEP_EXTENSIONS": True, "MAX_MEMORY_FILE_SIZE": 10})
    with pytest.raises(FileError):
        file.write(b"123456789012")


def test_non_utf8_extension_raises_file_error() -> None:
    # Extension bytes that are not valid in the filesystem encoding must be FileError.
    file = File(b"a.\xff", config={"UPLOAD_KEEP_EXTENSIONS": True, "MAX_MEMORY_FILE_SIZE": 10})
    with pytest.raises(FileError):
        file.write(b"123456789012")
