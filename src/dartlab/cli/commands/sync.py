"""dartlab sync — 수집 파이프라인 실행(로컬). dartlab.pipeline SSOT 호출.

로컬에서 한 명령으로 수집 — CI 워크플로(`python -m dartlab.pipeline`)와 동일 진입점.

    dartlab sync                  # recent set(finance,report,panel)
    dartlab sync finance          # finance 증분 + HF push
    dartlab sync panel --mode online
    dartlab sync --list
"""

from __future__ import annotations


def configureParser(subparsers) -> None:
    """sync 서브커맨드 등록."""
    parser = subparsers.add_parser("sync", help="데이터 수집 파이프라인 실행 (로컬/CI 단일 SSOT)")
    parser.add_argument("stage", nargs="?", help="stage category (생략 시 recent set)")
    parser.add_argument("--mode", default="recent", help="수집 모드 (recent/full/online 등)")
    parser.add_argument("--no-upload", action="store_true", help="HF 업로드 생략")
    parser.add_argument("--all", action="store_true", help="recent set 전체 실행")
    parser.add_argument("--list", action="store_true", dest="list_stages", help="등록 stage 목록")
    parser.set_defaults(handler=run)


def run(args) -> int:
    """sync 핸들러 — orchestrator 위임.

    Args:
        args: argparse Namespace.

    Returns:
        종료코드(0 성공, 1 실패).

    Raises:
        없음.

    Example:
        >>> run(argparse.Namespace(list_stages=True))  # doctest: +SKIP
        0
    """
    from dartlab.pipeline.orchestrator import describeStages, runPipeline, runStage

    if getattr(args, "list_stages", False):
        for d in describeStages():
            print(f"  {d['category']:12} {d['label']}")
        return 0

    upload = not getattr(args, "no_upload", False)
    mode = getattr(args, "mode", "recent")
    stage = getattr(args, "stage", None)
    if getattr(args, "all", False) or not stage:
        results = runPipeline(mode=mode, upload=upload)
    else:
        results = {stage: runStage(stage, mode=mode, upload=upload)}

    failed = False
    for cat, r in results.items():
        rp = r.report
        print(
            f"[sync] {cat}: ok={rp.ok} skip={rp.skip} err={rp.err} fail={rp.fail} changed={len(r.changedFiles)}",
            flush=True,
        )
        for f in rp.failures[:5]:
            print(f"    - {f}", flush=True)
        failed = failed or bool(rp.err or rp.fail)
    return 1 if failed else 0
