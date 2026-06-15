"""
visualize_skills.py — Top-N skill frequency chart from jobs_berlin_enriched.csv.
Output: output/skills_chart.png
"""

import csv
import logging
from collections import Counter

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from config import ENRICHED_CSV as DATA_FILE, CHART_PNG as OUTPUT_FILE, TOP_N_SKILLS as TOP_N

log = logging.getLogger(__name__)

# ── Category → colour mapping ─────────────────────────────────────────────────

CATEGORIES: dict[str, tuple[str, list[str]]] = {
    "Language":           ("#4C9BE8", [
        "python", "java", "javascript", "typescript", "c++", "c#", "go",
        "rust", "kotlin", "swift", "scala", "ruby", "php", "perl", "r",
        "matlab", "abap", "cobol", "groovy", "dart", "lua", "bash",
        "powershell", "shell", "vba", "pl/sql", "t-sql", "haskell",
        "elixir", "clojure",
    ]),
    "Framework / Library": ("#F0883E", [
        "react", "angular", "vue.js", "next.js", "nuxt.js", "svelte",
        "ember.js", "bootstrap", "tailwind css", "node.js", "express.js",
        "django", "flask", "fastapi", "spring boot", "spring", ".net",
        "asp.net", "laravel", "symfony", "rails", "quarkus", "micronaut",
        "nestjs", "graphql", "rest api", "websocket", "grpc", "openapi",
        "html", "css", "sass/scss",
    ]),
    "Cloud & Infrastructure": ("#3FB950", [
        "aws", "amazon web services", "microsoft azure", "azure", "google cloud",
        "gcp", "docker", "kubernetes", "helm", "openshift", "rancher",
        "podman", "terraform", "ansible", "puppet", "chef", "pulumi",
        "vagrant", "aws lambda", "aws s3", "aws ecs/eks", "aws rds",
        "aws cloudformation", "aws cdk", "azure devops", "azure functions",
        "azure kubernetes service", "azure active directory", "azure service bus",
        "cloud computing", "linux", "windows server", "vmware", "hyper-v",
        "nginx", "apache http", "tomcat",
    ]),
    "Database": ("#D2A8FF", [
        "sql", "mysql", "postgresql", "oracle db", "microsoft sql server",
        "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb",
        "mariadb", "sqlite", "neo4j", "influxdb", "snowflake", "bigquery",
        "databricks", "redshift", "couchdb", "hbase", "cosmos db",
        "datenbanken",
    ]),
    "DevOps & Methodology": ("#26A69A", [
        "devops", "devsecops", "ci/cd", "jenkins", "gitlab ci", "github actions",
        "circleci", "travis ci", "argocd", "flux", "gitops", "prometheus",
        "grafana", "splunk", "datadog", "new relic", "elk stack", "kibana",
        "logstash", "jaeger", "opentelemetry", "apache kafka", "rabbitmq",
        "apache spark", "apache airflow", "apache flink", "apache hadoop",
        "scrum", "kanban", "agile", "itil", "togaf", "microservices",
        "event-driven", "domain-driven design", "clean architecture",
        "solid", "design patterns", "site reliability engineering",
        "platform engineering",
    ]),
    "Security": ("#FF7B72", [
        "penetration testing", "siem", "iam", "oauth", "oidc", "keycloak",
        "hashicorp vault", "nessus", "burp suite", "wireshark", "snyk",
        "sonarqube", "iso 27001", "bsi-grundschutz", "owasp", "zero trust",
        "pki", "tls/ssl", "netzwerksicherheit", "tcp/ip", "dns", "vpn",
        "firewall", "bgp", "ospf", "sd-wan", "mpls",
        "active directory", "identity", "access management",
    ]),
    "SAP": ("#E3B341", [
        "sap s/4hana", "sap hana", "sap bw", "sap fiori", "sap crm",
        "sap erp", "sap mm", "sap sd", "sap fi/co", "sap hcm",
        "sap btp", "sap integration suite", "sap", "abap", "abap oo",
        "sapui5",
    ]),
    "Data / AI": ("#BF88F5", [
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "jupyter", "mlflow", "hugging face", "langchain", "openai",
        "power bi", "tableau", "looker", "dbt", "airbyte", "metabase",
        "qlik", "microstrategy", "ssrs", "ssis", "ssas",
        "artificial intelligence (ai)", "artificial intelligence", "big data",
        "business intelligence", "data engineering", "machine learning",
    ]),
}

_SKILL_TO_CAT: dict[str, tuple[str, str]] = {}
for _cat_name, (_colour, _skills) in CATEGORIES.items():
    for _s in _skills:
        _SKILL_TO_CAT[_s.lower()] = (_cat_name, _colour)

FALLBACK_COLOUR = "#8B949E"
FALLBACK_CAT    = "General / Other"


def categorise(skill: str) -> tuple[str, str]:
    key = skill.lower().strip()
    if key in _SKILL_TO_CAT:
        return _SKILL_TO_CAT[key]
    for stored_key, (cat, colour) in _SKILL_TO_CAT.items():
        if stored_key in key or key in stored_key:
            return cat, colour
    return FALLBACK_CAT, FALLBACK_COLOUR


# ── run / main ────────────────────────────────────────────────────────────────

def run():
    counter: Counter = Counter()
    with open(DATA_FILE, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for skill in row["skills"].split(";"):
                skill = skill.strip()
                if skill:
                    counter[skill] += 1

    top_skills = counter.most_common(TOP_N)
    labels  = [s for s, _ in top_skills][::-1]
    counts  = [c for _, c in top_skills][::-1]
    colours = [categorise(s)[1] for s in labels]

    available_styles = plt.style.available
    for style in ("seaborn-v0_8-whitegrid", "seaborn-whitegrid", "ggplot"):
        if style in available_styles:
            plt.style.use(style)
            break

    fig, ax = plt.subplots(figsize=(13, 11))
    bars = ax.barh(labels, counts, color=colours, height=0.7, edgecolor="white", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + 2,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center", ha="left",
            fontsize=9, color="#555555",
        )

    ax.set_xlabel("Number of job listings", fontsize=12, labelpad=10)
    ax.set_title(
        f"Top {TOP_N} Skills in Berlin IT Jobs  ·  get-in-it.de",
        fontsize=15, fontweight="bold", pad=18,
    )
    ax.set_xlim(0, max(counts) * 1.12)
    ax.tick_params(axis="y", labelsize=10)
    ax.tick_params(axis="x", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    seen_cats: dict[str, str] = {}
    for skill, colour in zip(labels, colours):
        cat, _ = categorise(skill)
        if cat not in seen_cats:
            seen_cats[cat] = colour

    legend_patches = [
        mpatches.Patch(color=col, label=cat)
        for cat, col in seen_cats.items()
    ]
    ax.legend(
        handles=legend_patches, loc="lower right",
        fontsize=9, framealpha=0.85,
        title="Category", title_fontsize=9,
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Chart saved: %s", OUTPUT_FILE)


def main():
    run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    main()
