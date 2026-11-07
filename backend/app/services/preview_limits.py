"""Per-request parser safety ceilings, not user storage or subscription quotas."""
MAX_FILES = 3
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_PAGES = 500
MAX_TEXT_CHARS = 1_000_000
MAX_PAGE_CHARS = 100_000
MAX_CHUNKS = 2000
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
TIMEOUT_SECONDS = 45
CPU_SECONDS = 20
MEMORY_BYTES = 768 * 1024 * 1024
MAX_PARALLEL = 2


def check_chunk_settings(size, overlap):
    if (type(size) is not int or type(overlap) is not int
            or not 256 <= size <= 4000 or not 0 <= overlap <= size // 2):
        raise ValueError("Chunk size must be 256-4000; overlap must be between zero and half the chunk size")
