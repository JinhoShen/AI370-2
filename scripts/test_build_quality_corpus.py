#!/usr/bin/env python3
"""Offline tests for the frozen quality-corpus builder.

Every build is redirected into a system temp dir by patching ``CORPUS`` (and
``ROOT``).  The committed corpus under docs/LOCAL_MODEL_LAB/quality-corpus/v1
is only read for comparison.  No Vivado, Vitis, model or network is touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_quality_corpus as builder

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
TASKS = [f"T{i}" for i in range(1, 9)]
VARIANTS = ["V1", "V2", "V3"]
BUILDERS = [("T1", builder.build_t1), ("T2", builder.build_t2), ("T3", builder.build_t3),
            ("T4", builder.build_t4), ("T5", builder.build_t5), ("T6", builder.build_t6),
            ("T7", builder.build_t7), ("T8", builder.build_t8)]


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def temp_corpus(case: unittest.TestCase) -> Path:
    temp = tempfile.TemporaryDirectory(prefix="quality-corpus-test-")
    case.addCleanup(temp.cleanup)
    corpus = Path(temp.name).resolve() / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
    case.assertFalse(str(corpus).startswith(str(ROOT)), "temp corpus must be outside the repo")
    return corpus


def build_all(corpus: Path, tasks=TASKS) -> dict[str, list[dict]]:
    """Run the builders in __main__ order against a redirected corpus root."""
    records = {}
    with patch.object(builder, "CORPUS", corpus), patch.object(builder, "ROOT", corpus.parents[3]):
        for task, build in BUILDERS:
            if task in tasks:
                records[task] = build()
    return records


class BuildQualityCorpusReproducibilityTests(unittest.TestCase):
    def test_two_fresh_builds_are_byte_identical(self) -> None:
        first_root, second_root = temp_corpus(self), temp_corpus(self)
        first, second = build_all(first_root), build_all(second_root)
        self.assertEqual(first, second)
        first_tree, second_tree = tree(first_root), tree(second_root)
        self.assertEqual(first_tree, second_tree)
        # 4+4+9+5+4+5+5+4 data files per variant, plus one manifest each.
        expected_counts = {"T1": 5, "T2": 5, "T3": 10, "T4": 6, "T5": 5, "T6": 6, "T7": 6, "T8": 5}
        for task in TASKS:
            for variant in VARIANTS:
                prefix = f"{task}/{variant}/"
                with self.subTest(task=task, variant=variant):
                    self.assertEqual(sum(name.startswith(prefix) for name in first_tree), expected_counts[task])

    def test_fresh_build_reproduces_committed_corpus_byte_for_byte(self) -> None:
        corpus = temp_corpus(self)
        records = build_all(corpus)
        built = tree(corpus)
        committed = tree(COMMITTED)
        # CORPUS_PROGRESS.json is fixture evidence, not a builder output.
        committed.pop("CORPUS_PROGRESS.json", None)
        self.assertEqual(sorted(built), sorted(committed))
        for name in committed:
            with self.subTest(file=name):
                self.assertEqual(built[name], committed[name])
        for task in TASKS:
            for index, variant in enumerate(VARIANTS):
                saved = json.loads((COMMITTED / task / variant / "SHA256SUMS.json").read_text())
                self.assertEqual(records[task][index], saved)

    def test_cli_builds_all_tasks_and_is_idempotent(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="quality-corpus-cli-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        # A copied script derives ROOT/CORPUS from its own location, so the CLI
        # writes only into the temp tree.
        (root / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/build_quality_corpus.py", root / "scripts/build_quality_corpus.py")
        command = [sys.executable, "-B", str(root / "scripts/build_quality_corpus.py")]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        first = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(first.returncode, 0, first.stderr)
        payload = json.loads(first.stdout)
        self.assertEqual(sorted(payload), [task.lower() for task in TASKS])
        for task in TASKS:
            self.assertEqual([row["variant"] for row in payload[task.lower()]], VARIANTS)
            self.assertEqual({row["task"] for row in payload[task.lower()]}, {task})
        corpus = root / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
        before = tree(corpus)
        second = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, first.stdout)
        self.assertEqual(tree(corpus), before)
        committed = tree(COMMITTED)
        committed.pop("CORPUS_PROGRESS.json", None)
        self.assertEqual(before, committed)


class BuildQualityCorpusContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="quality-corpus-content-")
        cls.corpus = Path(cls._temp.name).resolve() / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"
        cls.records = build_all(cls.corpus)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def read(self, task: str, variant: str, rel: str) -> str:
        return (self.corpus / task / variant / rel).read_text()

    def test_manifests_match_files_and_exclude_themselves(self) -> None:
        for task in TASKS:
            for index, variant in enumerate(VARIANTS):
                with self.subTest(task=task, variant=variant):
                    folder = self.corpus / task / variant
                    raw = (folder / "SHA256SUMS.json").read_text()
                    manifest = json.loads(raw)
                    self.assertEqual(raw, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
                    self.assertEqual(manifest["schema_version"], 1)
                    self.assertEqual((manifest["task"], manifest["variant"]), (task, variant))
                    self.assertNotIn("SHA256SUMS.json", manifest["files"])
                    self.assertEqual(list(manifest["files"]), sorted(manifest["files"]))
                    actual = {p.relative_to(folder).as_posix(): sha(p.read_bytes())
                              for p in folder.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"}
                    self.assertEqual(manifest["files"], actual)
                    self.assertEqual(self.records[task][index], manifest)

    def test_write_manifest_hashes_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "TX" / "V9"
            (folder / "public/a").mkdir(parents=True)
            (folder / "public/a/x.sv").write_bytes(b"x\n")
            (folder / "private").mkdir()
            (folder / "private/y.sv").write_bytes(b"\xff\x00")
            (folder / "SHA256SUMS.json").write_text("stale")
            payload = builder.write_manifest(folder)
            self.assertEqual(payload, {"schema_version": 1, "task": "TX", "variant": "V9", "files": {
                "private/y.sv": sha(b"\xff\x00"), "public/a/x.sv": sha(b"x\n")}})
            self.assertEqual(json.loads((folder / "SHA256SUMS.json").read_text()), payload)

    def test_hidden_assets_never_appear_under_public(self) -> None:
        for task in TASKS:
            for variant in VARIANTS:
                with self.subTest(task=task, variant=variant):
                    folder = self.corpus / task / variant
                    self.assertEqual({p.name for p in folder.iterdir()}, {"public", "private", "SHA256SUMS.json"})
                    public = tree(folder / "public")
                    private = tree(folder / "private")
                    self.assertIn("TASK_SPEC.md", public)
                    self.assertTrue(private)
                    self.assertFalse(any("reference" in name or "mutant" in name for name in public))
                    public_names = {Path(name).name for name in public}
                    for name, data in private.items():
                        self.assertNotIn(Path(name).name, public_names - {"tb_axi_regs.sv"})
                        self.assertNotIn(data, public.values(), f"hidden {name} copied under public/")
                    # The hidden pass marker is printed only by the private testbench.
                    for name, data in public.items():
                        if name != "TASK_SPEC.md":
                            self.assertNotIn(b"_PASS", data, name)

    def test_t1_variants_differ_only_in_reset_values(self) -> None:
        stubs = {self.read("T1", v, "public/rtl/axi_regs.sv") for v in VARIANTS}
        self.assertEqual(len(stubs), 1)
        self.assertTrue(stubs.pop().startswith(builder.PORTS))
        seen = set()
        for variant, resets in builder.T1_SPECS.items():
            spec = self.read("T1", variant, "public/TASK_SPEC.md")
            tb = self.read("T1", variant, "private/tb_axi_regs.sv")
            ref = self.read("T1", variant, "private/reference_axi_regs.sv")
            self.assertIn(", ".join(f"0x{x}" for x in resets), spec)
            for i, value in enumerate(resets):
                self.assertIn(f"localparam logic [31:0] R{i} = 32'h{value};", tb)
                self.assertIn(f"regs[{i}] <= 32'h{value};", ref)
            self.assertNotIn("{resets}", spec)
            seen.add((spec, tb, ref))
        self.assertEqual(len(seen), 3)
        self.assertEqual(len({r for v in builder.T1_SPECS.values() for r in v}), 12)

    def test_t2_seeds_a_distinct_defect_and_perturbs_the_hidden_testbench(self) -> None:
        seeded = {}
        for variant in VARIANTS:
            public = self.read("T2", variant, "public/rtl/axi_regs.sv")
            reference = self.read("T2", variant, "private/reference_axi_regs.sv")
            tb = self.read("T2", variant, "private/tb_axi_regs.sv")
            self.assertNotEqual(public, reference)
            self.assertEqual(reference, self.read("T1", variant, "private/reference_axi_regs.sv"))
            self.assertNotEqual(tb, self.read("T1", variant, "private/tb_axi_regs.sv"))
            self.assertIn("awvalid=0; awaddr=8'hfc;", tb)
            self.assertIn("wvalid=0; wdata=32'hDEADBEEF; wstrb=0;", tb)
            seeded[variant] = public
        self.assertIn("&& s_axi_wvalid;", seeded["V1"])
        self.assertIn("&& s_axi_awvalid;", seeded["V2"])
        self.assertIn("selected_aw = s_axi_awaddr;", seeded["V3"])
        self.assertIn("selected_wd = s_axi_wdata;", seeded["V3"])
        self.assertEqual(len(set(seeded.values())), 3)

    def test_t3_mutants_are_distinct_hidden_and_reference_tb_has_all_markers(self) -> None:
        names = {"ignore-wstrb", "same-cycle-aw-w", "unstable-read-response", "wrong-reset-value", "unstable-write-response"}
        for variant, resets in builder.T1_SPECS.items():
            with self.subTest(variant=variant):
                dut = self.read("T3", variant, "public/rtl/axi_regs.sv")
                self.assertEqual(dut, builder.reference_dut(resets))
                self.assertIn("not implemented", self.read("T3", variant, "public/sim/tb_axi_regs.sv"))
                mutants = {p.stem: p.read_text() for p in (self.corpus / "T3" / variant / "private/mutants").glob("*.sv")}
                self.assertEqual(set(mutants), names)
                self.assertNotIn(dut, mutants.values())
                self.assertEqual(len(set(mutants.values())), 5)
                self.assertIn("regs[0] <= 32'h00000000;", mutants["wrong-reset-value"])
                self.assertNotIn(f"regs[0] <= 32'h{resets[0]};", mutants["wrong-reset-value"])
                golden = self.read("T3", variant, "private/reference_tb_axi_regs.sv")
                self.assertIn('$display("QUALITY_T3_PASS', golden)
                self.assertNotIn("QUALITY_T1_PASS", golden)
                self.assertIn("T3 simulation watchdog", golden)
                for scenario in ("reset", "aw_before_w", "w_before_aw", "simultaneous", "wstrb", "unmapped",
                                 "b_backpressure", "r_backpressure", "consecutive"):
                    self.assertIn(f'$display("QUALITY_T3_SCENARIO_{scenario}_PASS");', golden)

    def test_t4_and_t7_share_rtl_but_t7_has_ross_spec_and_marker(self) -> None:
        defects = {"V1": ".operation(op)", "V2": "alu_core u_alu", "V3": ".valid_o(valid)"}
        shared = None
        for variant, broken in defects.items():
            with self.subTest(variant=variant):
                top = self.read("T4", variant, "public/rtl/calc_top.sv")
                self.assertIn(broken, top)
                for other in set(defects.values()) - {broken}:
                    self.assertNotIn(other, top)
                common = (self.read("T4", variant, "public/rtl/alu.sv"), self.read("T4", variant, "public/rtl/alu_pkg.sv"),
                          self.read("T4", variant, "private/tb_calc_top.sv"))
                shared = shared or common
                self.assertEqual(common, shared)
                for rel in ("public/rtl/alu.sv", "public/rtl/alu_pkg.sv", "public/rtl/calc_top.sv"):
                    self.assertEqual(self.read("T7", variant, rel), self.read("T4", variant, rel))
                t7_spec = self.read("T7", variant, "public/TASK_SPEC.md")
                self.assertIn("T7 AMD Ross assisted Vivado XSim", t7_spec)
                self.assertIn("ross_skill_read", t7_spec)
                self.assertIn("QUALITY_T7_PASS", t7_spec)
                self.assertNotIn("QUALITY_T4_PASS", t7_spec)
                t7_tb = self.read("T7", variant, "private/tb_calc_top.sv")
                self.assertIn("QUALITY_T7_PASS", t7_tb)
                self.assertNotIn("QUALITY_T4_PASS", t7_tb)

    def test_t5_seeds_latch_prone_logic_and_reference_has_default(self) -> None:
        seeded = set()
        for variant in VARIANTS:
            public = self.read("T5", variant, "public/rtl/mux_math.sv")
            reference = self.read("T5", variant, "private/reference_mux_math.sv")
            self.assertNotIn("default", public)
            self.assertIn("default", reference)
            seeded.add(public)
        self.assertEqual(len(seeded), 3)

    def test_t6_seeds_wrong_kernel_and_variant_specific_vectors(self) -> None:
        testbenches = set()
        for variant, seed in {"V1": "return input;", "V2": "return input ^ 0x00ff00ffu;", "V3": "return ~(input >> 1);"}.items():
            src = self.read("T6", variant, "public/src/invert32.cpp")
            self.assertIn(seed, src)
            self.assertNotIn("return ~input;", src)
            self.assertIn("return ~input;", self.read("T6", variant, "private/reference_invert32.cpp"))
            tb = self.read("T6", variant, "private/testbench.cpp")
            self.assertIn("QUALITY_T6_CSIM_PASS checks=4", tb)
            pairs = [line.split("invert32(0x", 1)[1] for line in tb.splitlines() if "invert32(0x" in line]
            self.assertEqual(len(pairs), 4)
            for pair in pairs:
                x, y = pair.split("u)!=0x", 1)
                self.assertEqual(int(y[:8], 16), (~int(x, 16)) & 0xFFFFFFFF)
            testbenches.add(tb)
        self.assertEqual(len(testbenches), 3)

    def test_t8_uses_stub_public_rtl_and_t8_marker(self) -> None:
        for variant in VARIANTS:
            self.assertEqual(self.read("T8", variant, "public/rtl/axi_regs.sv"),
                             "module axi_regs;\n  // Implement the behavior specified in TASK_SPEC.md.\nendmodule\n")
            self.assertEqual(self.read("T8", variant, "private/reference_axi_regs.sv"),
                             self.read("T1", variant, "private/reference_axi_regs.sv"))
            tb = self.read("T8", variant, "private/tb_axi_regs.sv")
            self.assertIn("QUALITY_T8_PASS", tb)
            self.assertIn("T8 simulation watchdog", tb)
            self.assertNotIn("QUALITY_T1_PASS", tb)
            self.assertIn("STATUS=PASS", self.read("T8", variant, "public/TASK_SPEC.md"))


class BuildQualityCorpusFrozenGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = temp_corpus(self)
        build_all(self.corpus)
        self.snapshot = tree(self.corpus)

    def rebuild(self, task: str):
        with patch.object(builder, "CORPUS", self.corpus):
            return dict(BUILDERS)[task]()

    def test_rebuild_of_intact_corpus_returns_saved_manifests_without_writing(self) -> None:
        for task in TASKS:
            with self.subTest(task=task):
                mtimes = {p: p.stat().st_mtime_ns for p in (self.corpus / task).rglob("*") if p.is_file()}
                records = self.rebuild(task)
                self.assertEqual([r["variant"] for r in records], VARIANTS)
                self.assertEqual({p: p.stat().st_mtime_ns for p in (self.corpus / task).rglob("*") if p.is_file()}, mtimes)
        self.assertEqual(tree(self.corpus), self.snapshot)

    def test_tampered_file_is_rejected_and_left_untouched(self) -> None:
        for task in TASKS:
            with self.subTest(task=task):
                target = sorted((self.corpus / task / "V2" / "public").rglob("*.*"))[0]
                original = target.read_bytes()
                target.write_bytes(original + b"// drift\n")
                with self.assertRaisesRegex(RuntimeError, "Frozen corpus integrity check failed"):
                    self.rebuild(task)
                self.assertEqual(target.read_bytes(), original + b"// drift\n")
                target.write_bytes(original)

    def test_extra_or_missing_files_are_rejected(self) -> None:
        for task in TASKS:
            with self.subTest(task=task, change="extra"):
                extra = self.corpus / task / "V1" / "public/extra.txt"
                extra.write_text("x")
                with self.assertRaisesRegex(RuntimeError, "integrity check failed"):
                    self.rebuild(task)
                extra.unlink()
            with self.subTest(task=task, change="missing"):
                victim = next(p for p in sorted((self.corpus / task / "V3" / "private").rglob("*")) if p.is_file())
                data = victim.read_bytes()
                victim.unlink()
                with self.assertRaisesRegex(RuntimeError, "integrity check failed"):
                    self.rebuild(task)
                victim.write_bytes(data)
        self.assertEqual(tree(self.corpus), self.snapshot)

    def test_existing_variant_without_manifest_is_never_overwritten(self) -> None:
        for task in TASKS:
            with self.subTest(task=task):
                manifest = self.corpus / task / "V1" / "SHA256SUMS.json"
                saved = manifest.read_bytes()
                manifest.unlink()
                before = tree(self.corpus / task)
                with self.assertRaisesRegex(RuntimeError, "Refusing to overwrite incomplete corpus variant"):
                    self.rebuild(task)
                self.assertEqual(tree(self.corpus / task), before)
                manifest.write_bytes(saved)
        self.assertEqual(tree(self.corpus), self.snapshot)

    def test_partial_corpus_completes_only_missing_variants(self) -> None:
        shutil.rmtree(self.corpus / "T2" / "V2")
        kept = tree(self.corpus / "T2" / "V1")
        records = self.rebuild("T2")
        self.assertEqual([r["variant"] for r in records], VARIANTS)
        self.assertEqual(tree(self.corpus / "T2" / "V1"), kept)
        self.assertEqual(tree(self.corpus), self.snapshot)

    def test_t7_requires_t4_sources(self) -> None:
        corpus = temp_corpus(self)
        with patch.object(builder, "CORPUS", corpus):
            with self.assertRaises(FileNotFoundError):
                builder.build_t7()


class CommittedCorpusReadOnlyTests(unittest.TestCase):
    def test_committed_manifests_verify(self) -> None:
        for task in TASKS:
            for variant in VARIANTS:
                folder = COMMITTED / task / variant
                manifest = json.loads((folder / "SHA256SUMS.json").read_text())
                actual = {p.relative_to(folder).as_posix(): sha(p.read_bytes())
                          for p in folder.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"}
                self.assertEqual(manifest["files"], actual, f"{task}/{variant}")


if __name__ == "__main__":
    unittest.main()
