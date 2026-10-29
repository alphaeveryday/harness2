"""Publish authorized milestones to the originating Buzz thread."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def notify(root: Path, phase: str, completed: int, minimum: int, error: str) -> None:
    channel = os.environ.get("QUANT_FACTORY_CHANNEL")
    reply = os.environ.get("QUANT_FACTORY_REPLY")
    milestone = phase == "hypothesis_completed" and completed > 0 and (completed == 1 or completed % 10 == 0)
    terminal = phase in {"blocked", "completed", "stopped"}
    if not channel or not reply or not (milestone or terminal):
        return
    receipts = root / "notifications"
    receipts.mkdir(exist_ok=True)
    receipt = receipts / f"{phase}-{completed}.json"
    if receipt.exists():
        return
    content = (f"Linux 단일 알파 공장: 새 후보 {completed}/{minimum}개 평가·회고 완료. "
               "중복·재현·실행 오류는 이 수에 포함하지 않았습니다. "
               f"상태={phase}. 투자 승격은 기존 엔진 한계로 계속 차단합니다. "
               f"근거: {root / 'status.json'}")
    if error:
        content += "\n중단 원인: " + error[:1500]
    command = ["buzz", "messages", "send", "--channel", channel, "--reply-to", reply, "--content"]
    owner = os.environ.get("QUANT_FACTORY_OWNER")
    if terminal and owner:
        content = "@junyoung " + content
    command.append(content)
    if terminal and owner:
        command.extend(["--mention", owner])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as failure:
        (receipts / f"{phase}-{completed}.error").write_text(str(failure))
        return
    if result.returncode == 0:
        receipt.write_text(result.stdout)
    else:
        (receipts / f"{phase}-{completed}.error").write_text(result.stderr)
