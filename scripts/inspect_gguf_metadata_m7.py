#!/usr/bin/env python3
"""Read GGUF header, metadata and tensor descriptors without loading weights."""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = REPO / "resources/Downloads/LocalAI/llama.cpp/llama.cpp-v0.5.0-7fe450e19305.tar.gz"

def scalar(reader, key, default=None):
    field = reader.get_field(key)
    if field is None:
        return default
    value = field.contents()
    return value.item() if hasattr(value, "item") else value

def load_gguf_package(archive: Path, destination: Path) -> Path:
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        init = next(m for m in members if m.name.endswith("/gguf-py/gguf/__init__.py"))
        prefix = init.name.removesuffix("gguf/__init__.py")
        root = destination / "gguf-py"
        for member in members:
            if not member.name.startswith(prefix):
                continue
            relative = PurePosixPath(member.name[len(prefix):])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe archive path: {member.name}")
            target = root.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError(f"cannot read {member.name}")
                with source, target.open("wb") as output:
                    output.write(source.read())
    return root

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--source-archive", type=Path, default=DEFAULT_ARCHIVE)
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error(f"model not found: {args.model}")
    with tempfile.TemporaryDirectory(prefix="gguf-header-") as temporary:
        package_root = load_gguf_package(args.source_archive, Path(temporary))
        sys.path.insert(0, str(package_root))
        import gguf
        reader = gguf.GGUFReader(args.model, mode="r")
        metadata = {
            key: scalar(reader, key)
            for key in (
                "GGUF.version", "general.architecture", "general.name",
                "general.size_label", "general.file_type",
                "general.quantization_version", "qwen35moe.block_count",
                "qwen35moe.context_length", "qwen35moe.embedding_length",
                "qwen35moe.expert_count", "qwen35moe.expert_used_count",
            )
        }
        file_type = gguf.LlamaFileType(int(metadata["general.file_type"])).name
        tensor_counts = collections.Counter(t.tensor_type.name for t in reader.tensors)
        tensor_elements = collections.Counter()
        total_parameters = 0
        for tensor in reader.tensors:
            elements = int(tensor.n_elements)
            total_parameters += elements
            tensor_elements[tensor.tensor_type.name] += elements
        result = {
            "status": "PARSED",
            "parser": "gguf-py from the locally installed llama.cpp source archive",
            "parser_source_archive": str(args.source_archive),
            "weights_loaded": False,
            "tensor_payloads_validated": False,
            "metadata_kv_pairs": len(reader.fields) - 3,
            "tensor_count": len(reader.tensors),
            "total_parameter_elements": total_parameters,
            "quantization": file_type,
            "tensor_type_counts": dict(sorted(tensor_counts.items())),
            "tensor_elements_by_type": dict(sorted(tensor_elements.items())),
            "metadata": metadata,
            "data_offset_bytes": reader.data_offset,
            "alignment_bytes": reader.alignment,
            "model_bytes": args.model.stat().st_size,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
