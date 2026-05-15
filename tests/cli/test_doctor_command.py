import json

from click.testing import CliRunner

from src.cli.commands.doctor import doctor
from src.cli.security_scan import scan_text


def test_scan_text_detects_local_paths_and_api_keys():
    text = "\n".join(
        [
            "backend = " + repr("/" + "Users/alice/FAgent"),
            "openrouter = " + repr("sk-or-v1-" + "a" * 32),
        ]
    )

    findings = scan_text("config.py", text)
    rule_ids = {finding.rule_id for finding in findings}

    assert "local-home-path" in rule_ids
    assert "openrouter-api-key" in rule_ids


def test_scan_text_ignores_placeholder_examples():
    text = "\n".join(
        [
            'Environment=OPENAI_API_KEY="your-key"',
            'Environment=JWT_SECRET="<strong-random-string>"',
        ]
    )

    assert scan_text("DEPLOY.md", text) == []


def test_doctor_security_scan_json_passes(tmp_path):
    (tmp_path / "safe.py").write_text("print('ok')\n", encoding="utf-8")

    result = CliRunner().invoke(
        doctor,
        ["security-scan", "--root", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["scanned_files"] == 1
    assert payload["findings"] == []


def test_doctor_security_scan_fails_without_printing_secret(tmp_path):
    fake_token = "ghp_" + "a" * 36
    (tmp_path / "leak.txt").write_text("token = " + fake_token + "\n", encoding="utf-8")

    result = CliRunner().invoke(
        doctor,
        ["security-scan", "--root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "github-token" in result.output
    assert "leak.txt:1" in result.output
    assert fake_token not in result.output
