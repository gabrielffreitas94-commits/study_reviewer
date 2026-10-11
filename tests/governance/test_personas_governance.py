"""Testes de governança para verificação automatizada dos 17 especialistas e CI/CD modular."""

from pathlib import Path

EXPECTED_PERSONAS = [
    ("01-product-specialist.md", "Especialista de Produto"),
    ("02-qa-specialist.md", "Especialista QA"),
    ("03-architect-specialist.md", "Especialista Arquiteto"),
    ("04-security-specialist.md", "Especialista de Segurança"),
    ("05-telemetry-specialist.md", "Especialista de Telemetria"),
    ("06-ux-specialist.md", "Especialista de UX"),
    ("07-ui-specialist.md", "Especialista de UI"),
    ("08-devops-specialist.md", "Especialista de DevOps"),
    ("09-accessibility-specialist.md", "Especialista de Acessibilidade"),
    ("10-lgpd-specialist.md", "Especialista em LGPD"),
    ("11-python-performance-specialist.md", "Especialista de Performance de Programação Python"),
    ("12-frontend-performance-specialist.md", "Especialista de Performance de Frontend"),
    ("13-database-performance-specialist.md", "Especialista de Performance de Banco de Dados"),
    ("14-mobile-specialist.md", "Especialista Mobile"),
    ("15-flutter-specialist.md", "Especialista Flutter"),
    ("16-ai-architecture-specialist.md", "Especialista em Arquitetura de IA"),
    ("17-payment-billing-specialist.md", "Especialista de Pagamento e Cobrança"),
]

EXPECTED_SKILLS = [
    "product-requirements-auditor",
    "product-use-cases-generator",
    "qa-tdd-coverage-auditor",
    "qa-use-cases-validator",
    "architect-clean-arch-auditor",
    "architect-spec-adr-author",
    "security-owasp-auditor",
    "security-test-enforcer",
    "telemetry-observability-auditor",
    "ux-journey-auditor",
    "ui-interface-auditor",
    "devops-infrastructure-auditor",
    "a11y-wcag-auditor",
    "lgpd-privacy-auditor",
    "python-performance-auditor",
    "frontend-performance-auditor",
    "database-performance-auditor",
    "mobile-usability-auditor",
    "mobile-security-auditor",
    "mobile-performance-auditor",
    "flutter-performance-auditor",
    "flutter-code-quality-auditor",
    "ai-performance-auditor",
    "ai-resilience-auditor",
    "ai-security-auditor",
    "ai-hallucination-mitigator",
    "payment-transactions-auditor",
    "payment-gateways-webhook-auditor",
    "billing-lifecycle-auditor",
    "parallel-audit-orchestrator",
]

EXPECTED_WORKFLOWS = [
    "ci-backend-lint.yml",
    "ci-backend-types.yml",
    "ci-backend-governance.yml",
    "ci-backend-tests-coverage.yml",
    "ci-frontend-assets.yml",
    "ci-frontend-quality.yml",
    "cd-docker-parity.yml",
]


def test_all_17_personas_exist_with_complete_structure() -> None:
    """Valida a existência e completude documental de todas as 17 personas de auditoria."""
    personas_dir = Path("docs/personas")
    assert personas_dir.exists(), "Diretório docs/personas não encontrado!"

    for filename, specialist_name in EXPECTED_PERSONAS:
        persona_path = personas_dir / filename
        assert persona_path.exists(), f"Persona {filename} não foi encontrada!"

        content = persona_path.read_text(encoding="utf-8")
        assert specialist_name.lower() in content.lower(), (
            f"{filename} deve citar '{specialist_name}'"
        )
        assert "## 1. Identidade e Propósito" in content, f"{filename} sem seção 1"
        assert "## 2. Responsabilidades Principais" in content, f"{filename} sem seção 2"
        assert "## 3. Skills Associadas" in content, f"{filename} sem seção 3"
        assert "## 4. Heurísticas e Critérios de Avaliação" in content, f"{filename} sem seção 4"
        assert "## 5. Formato do Parecer na PR" in content, f"{filename} sem seção 5"


def test_all_specialist_skills_exist_with_frontmatter() -> None:
    """Valida que todas as skills dos 17 especialistas existem com YAML frontmatter válido."""
    skills_dir = Path(".gemini/skills")
    assert skills_dir.exists(), "Diretório .gemini/skills não encontrado!"

    for skill_name in EXPECTED_SKILLS:
        skill_file = skills_dir / skill_name / "SKILL.md"
        assert skill_file.exists(), f"Skill '{skill_name}/SKILL.md' não foi encontrada!"

        content = skill_file.read_text(encoding="utf-8")
        assert content.startswith("---"), (
            f"Skill '{skill_name}' deve iniciar com frontmatter YAML (---)"
        )
        assert f"name: {skill_name}" in content, (
            f"Skill '{skill_name}' deve declarar name no frontmatter"
        )
        assert "description:" in content, (
            f"Skill '{skill_name}' deve declarar description no frontmatter"
        )


def test_pr_template_contains_all_17_specialists() -> None:
    """Garante que o template de PR contenha a bancada completa dos 17 especialistas."""
    template_path = Path(".github/PULL_REQUEST_TEMPLATE.md")
    assert template_path.exists(), "Template de PR não encontrado!"

    content = template_path.read_text(encoding="utf-8")
    assert "Bancada dos 17 Especialistas" in content

    for i in range(1, 18):
        assert f"| **{i}** |" in content, (
            f"Especialista #{i} ausente na tabela de auditoria do template de PR!"
        )


def test_all_modular_ci_cd_workflows_exist() -> None:
    """Garante que todos os 7 workflows modulares de CI/CD estejam configurados."""
    workflows_dir = Path(".github/workflows")
    assert workflows_dir.exists(), "Diretório .github/workflows não encontrado!"

    for workflow in EXPECTED_WORKFLOWS:
        wf_path = workflows_dir / workflow
        assert wf_path.exists(), f"Workflow modular '{workflow}' não encontrado!"
        content = wf_path.read_text(encoding="utf-8")
        assert "name:" in content
        assert "runs-on: ubuntu-latest" in content


def test_parallel_audit_protocol_document_exists() -> None:
    """Garante que o protocolo de auditoria concorrente por clusters esteja formalizado."""
    protocol_path = Path("docs/personas/00-parallel-audit-protocol.md")
    assert protocol_path.exists(), "docs/personas/00-parallel-audit-protocol.md não encontrado!"

    content = protocol_path.read_text(encoding="utf-8")
    assert "Cluster 1: Core & Arquitetura" in content
    assert "Cluster 2: Segurança & Compliance" in content
    assert "Cluster 3: Experiência & Interface" in content
    assert "Cluster 4: Engenharia Mobile & Flutter" in content
    assert "Cluster 5: Backend, Dados, Ops & IA" in content


def test_prd_documents_all_17_specialists() -> None:
    """Garante que o PRD.md documente formalmente a bancada dos 17 especialistas."""
    prd_path = Path("PRD.md")
    assert prd_path.exists(), "PRD.md não encontrado!"

    content = prd_path.read_text(encoding="utf-8")
    assert "Bancada dos 17 Especialistas" in content
    for _, specialist_name in EXPECTED_PERSONAS:
        assert specialist_name.lower() in content.lower(), (
            f"Especialista '{specialist_name}' não mencionado no PRD.md!"
        )
