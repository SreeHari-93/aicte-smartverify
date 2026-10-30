import pytest
from backend.app.models.rule import Rule
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token


@pytest.fixture
def rules_setup(db_session):
    # Create Institute and Institute User
    inst = Institute(aicte_institute_id="INST_RULES_01", name="Rules Institute", state="Delhi", status="ACTIVE")
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    user = User(
        email="rules_user@inst.edu",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Seed test rules across categories
    r1 = Rule(
        rule_code="APH-2026-CH2-R01",
        category="Extension of Approval (EoA)",
        title="Continuous EoA Validity",
        description="The Institution shall maintain valid, unbroken Approval.",
        handbook_reference="Section 2.4.1",
        version="v2026.1",
        is_mandatory=True,
        rule_type="MANDATORY",
        ai_checks=["Check validity timeline"],
        evidence_required=["EoA Letter"],
        applies_to=["Extension of Approval (EoA)"],
        version_history=[{"version": "v2026.1", "date": "2026-01-10", "note": "Updated"}],
    )
    r2 = Rule(
        rule_code="APH-2026-CH2-R05",
        category="Extension of Approval (EoA)",
        title="Digital Library Subscription",
        description="Active institutional subscriptions to IEEE journals.",
        handbook_reference="Section 2.11.4",
        version="v2026.1",
        is_mandatory=False,
        rule_type="ADVISORY",
        ai_checks=["Check journal invoices"],
        evidence_required=["Invoices"],
        applies_to=["All"],
        version_history=[],
    )
    r3 = Rule(
        rule_code="APH-2026-CH3-R01",
        category="Change of Name",
        title="Society Trust Resolution",
        description="Unanimous governing body resolution approving name change.",
        handbook_reference="Section 3.1.2",
        version="v2026.1",
        is_mandatory=True,
        rule_type="MANDATORY",
        ai_checks=["Check resolution quorum"],
        evidence_required=["Trust Resolution"],
        applies_to=["Change of Name"],
        version_history=[],
    )
    r4 = Rule(
        rule_code="APH-2026-CH7-R01",
        category="Intake Change",
        title="NBA Accreditation Prerequisite",
        description="Active NBA accreditation with minimum valid score of 675.",
        handbook_reference="Section 7.1.3",
        version="v2026.1",
        is_mandatory=True,
        rule_type="MANDATORY",
        ai_checks=["Check NBA score >= 675"],
        evidence_required=["NBA Sheet"],
        applies_to=["Intake Change"],
        version_history=[],
    )
    r5 = Rule(
        rule_code="APH-2026-CH8-R04",
        category="Closure/Merger",
        title="Institutional Asset Redeployment",
        description="Redeployment of educational infrastructure and land.",
        handbook_reference="Section 8.5.1",
        version="v2026.1",
        is_mandatory=False,
        rule_type="ADVISORY",
        ai_checks=["Check title deed"],
        evidence_required=["Valuation Report"],
        applies_to=["Closure/Merger"],
        version_history=[],
    )
    db_session.add_all([r1, r2, r3, r4, r5])
    db_session.commit()

    token = create_access_token(user.id, "INSTITUTE")
    return {"token": token, "user": user}


def test_rules_unauthenticated(client):
    res = client.get("/api/institute/rules")
    assert res.status_code == 401


def test_rules_summary_and_all(client, rules_setup):
    client.cookies.set("aicte_access_token", rules_setup["token"])
    res = client.get("/api/institute/rules")
    assert res.status_code == 200
    data = res.json()

    assert "summary" in data
    assert "groups" in data

    summary = data["summary"]
    assert summary["total"] == 5
    assert summary["mandatory"] == 3
    assert summary["advisory"] == 2
    assert summary["categories_count"] == 4
    assert summary["category_counts"]["Extension of Approval (EoA)"] == 2
    assert summary["category_counts"]["Change of Name"] == 1


def test_rules_filter_by_category(client, rules_setup):
    client.cookies.set("aicte_access_token", rules_setup["token"])
    res = client.get("/api/institute/rules?category=Change of Name")
    assert res.status_code == 200
    data = res.json()

    # Summary remains global for strip/chips
    assert data["summary"]["total"] == 5

    # Filtered groups only contain the selected category
    assert len(data["groups"]) == 1
    assert data["groups"][0]["category"] == "Change of Name"
    assert len(data["groups"][0]["rules"]) == 1
    assert data["groups"][0]["rules"][0]["rule_code"] == "APH-2026-CH3-R01"


def test_rules_filter_by_type(client, rules_setup):
    client.cookies.set("aicte_access_token", rules_setup["token"])
    # Mandatory
    res_mand = client.get("/api/institute/rules?type=MANDATORY")
    assert res_mand.status_code == 200
    data_mand = res_mand.json()
    all_mand_rules = [r for g in data_mand["groups"] for r in g["rules"]]
    assert len(all_mand_rules) == 3
    for r in all_mand_rules:
        assert r["rule_type"] == "MANDATORY"

    # Advisory
    res_adv = client.get("/api/institute/rules?type=ADVISORY")
    assert res_adv.status_code == 200
    data_adv = res_adv.json()
    all_adv_rules = [r for g in data_adv["groups"] for r in g["rules"]]
    assert len(all_adv_rules) == 2
    for r in all_adv_rules:
        assert r["rule_type"] == "ADVISORY"


def test_rules_search_query(client, rules_setup):
    client.cookies.set("aicte_access_token", rules_setup["token"])
    # Search by code
    res_code = client.get("/api/institute/rules?q=CH7-R01")
    assert res_code.status_code == 200
    data_code = res_code.json()
    assert len(data_code["groups"]) == 1
    assert data_code["groups"][0]["rules"][0]["rule_code"] == "APH-2026-CH7-R01"

    # Search by handbook reference
    res_ref = client.get("/api/institute/rules?q=2.11.4")
    assert res_ref.status_code == 200
    data_ref = res_ref.json()
    assert len(data_ref["groups"]) == 1
    assert data_ref["groups"][0]["rules"][0]["rule_code"] == "APH-2026-CH2-R05"


def test_rules_sorting(client, rules_setup):
    client.cookies.set("aicte_access_token", rules_setup["token"])
    res = client.get("/api/institute/rules?sort=rule_code")
    assert res.status_code == 200
    data = res.json()
    eoa_group = next(g for g in data["groups"] if g["category"] == "Extension of Approval (EoA)")
    codes = [r["rule_code"] for r in eoa_group["rules"]]
    assert codes == sorted(codes)

