"""
extract_skills.py — Post-processor: scan position_description for hard-skill
keywords and merge findings into the skills column.

Reads:  config.RAW_CSV      (jobs_berlin_raw.csv)
Writes: config.ENRICHED_CSV (jobs_berlin_enriched.csv)
"""

import csv
import logging
import re

from config import RAW_CSV as INPUT_FILE, ENRICHED_CSV as OUTPUT_FILE

log = logging.getLogger(__name__)

# ── Canonical skill name → regex pattern ─────────────────────────────────────

SKILLS: list[tuple[str, str]] = [
    # ── Programming languages ─────────────────────────────────────────────────
    ("Python",          r"Python"),
    ("Java",            r"Java(?!Script|\.|\-Script)"),
    ("JavaScript",      r"JavaScript|JS(?=\b)"),
    ("TypeScript",      r"TypeScript"),
    ("C++",             r"C\+\+"),
    ("C#",              r"C#"),
    ("Go",              r"\bGo(?:\s*lang(?:uage)?)?(?=\s+[A-Z,/\-]|\s*[,;/]|\s*$|\s+(?:und|and|oder|or|mit|with|für|for|in|as|ist|wird|werden))"),
    ("Rust",            r"\bRust\b"),
    ("Kotlin",          r"Kotlin"),
    ("Swift",           r"\bSwift\b"),
    ("Scala",           r"Scala"),
    ("Ruby",            r"\bRuby\b"),
    ("PHP",             r"\bPHP\b"),
    ("Perl",            r"\bPerl\b"),
    ("R",               r"\bR\b(?=\s+(?:und|and|oder|Programmier|Studio))"),
    ("MATLAB",          r"MATLAB"),
    ("ABAP",            r"ABAP"),
    ("COBOL",           r"COBOL"),
    ("Groovy",          r"\bGroovy\b"),
    ("Dart",            r"\bDart\b"),
    ("Lua",             r"\bLua\b"),
    ("Bash",            r"\bBash\b"),
    ("PowerShell",      r"PowerShell"),
    ("Shell",           r"Shell[-\s]?Script(?:ing)?"),
    ("VBA",             r"\bVBA\b"),
    ("PL/SQL",          r"PL/SQL"),
    ("T-SQL",           r"T-SQL|Transact-SQL"),
    ("Haskell",         r"\bHaskell\b"),
    ("Elixir",          r"\bElixir\b"),
    ("Clojure",         r"\bClojure\b"),
    # ── Web / Frontend ────────────────────────────────────────────────────────
    ("React",           r"\bReact(?:\.js|JS)?\b"),
    ("Angular",         r"\bAngular(?:JS|\.js)?\b"),
    ("Vue.js",          r"\bVue(?:\.js|JS)?\b"),
    ("Next.js",         r"\bNext\.js\b"),
    ("Nuxt.js",         r"\bNuxt(?:\.js)?\b"),
    ("Svelte",          r"\bSvelte(?:Kit)?\b"),
    ("Ember.js",        r"\bEmber(?:\.js)?\b"),
    ("HTML",            r"\bHTML5?\b"),
    ("CSS",             r"\bCSS3?\b"),
    ("SASS/SCSS",       r"\bS[AC]SS\b"),
    ("Bootstrap",       r"\bBootstrap\b"),
    ("Tailwind CSS",    r"Tailwind(?:\s+CSS)?"),
    ("GraphQL",         r"GraphQL"),
    ("REST API",        r"REST(?:ful)?[\s\-]?API"),
    ("WebSocket",       r"WebSocket"),
    ("gRPC",            r"gRPC"),
    ("OpenAPI",         r"OpenAPI|Swagger"),
    # ── Backend frameworks ────────────────────────────────────────────────────
    ("Node.js",         r"Node(?:\.js|JS)"),
    ("Express.js",      r"Express(?:\.js|JS)?"),
    ("Django",          r"\bDjango\b"),
    ("Flask",           r"\bFlask\b"),
    ("FastAPI",         r"FastAPI"),
    ("Spring Boot",     r"Spring\s+Boot"),
    ("Spring",          r"\bSpring(?!\s+Boot)\b"),
    (".NET",            r"\.NET(?:\s+Core|\s+Framework)?"),
    ("ASP.NET",         r"ASP\.NET"),
    ("Laravel",         r"Laravel"),
    ("Symfony",         r"Symfony"),
    ("Rails",           r"Ruby\s+on\s+Rails|Rails"),
    ("Quarkus",         r"\bQuarkus\b"),
    ("Micronaut",       r"Micronaut"),
    ("NestJS",          r"NestJS|Nest\.js"),
    ("Gin",             r"\bGin\s+(?:Framework|Web)\b"),
    ("FastHTML",        r"FastHTML"),
    # ── Databases ─────────────────────────────────────────────────────────────
    ("SQL",             r"\bSQL\b"),
    ("MySQL",           r"MySQL"),
    ("PostgreSQL",      r"PostgreSQL|Postgres"),
    ("Oracle DB",       r"\bOracle\s+(?:DB|Database|SQL)?\b"),
    ("Microsoft SQL Server", r"SQL\s+Server|MSSQL"),
    ("MongoDB",         r"MongoDB"),
    ("Redis",           r"\bRedis\b"),
    ("Elasticsearch",   r"Elasticsearch"),
    ("Cassandra",       r"Cassandra"),
    ("DynamoDB",        r"DynamoDB"),
    ("MariaDB",         r"MariaDB"),
    ("SQLite",          r"SQLite"),
    ("Neo4j",           r"Neo4j"),
    ("InfluxDB",        r"InfluxDB"),
    ("Snowflake",       r"Snowflake"),
    ("BigQuery",        r"BigQuery"),
    ("Databricks",      r"Databricks"),
    ("Redshift",        r"\bRedshift\b"),
    ("CouchDB",         r"CouchDB"),
    ("HBase",           r"\bHBase\b"),
    ("Cosmos DB",       r"Cosmos\s+DB"),
    # ── Cloud platforms ───────────────────────────────────────────────────────
    ("AWS",             r"\bAWS\b|Amazon\s+Web\s+Services"),
    ("Microsoft Azure", r"\bAzure\b|Microsoft\s+Azure"),
    ("Google Cloud",    r"Google\s+Cloud(?:\s+Platform)?|GCP"),
    # ── AWS services ──────────────────────────────────────────────────────────
    ("AWS Lambda",      r"AWS\s+Lambda|Lambda\s+Function"),
    ("AWS S3",          r"\bS3\b(?=\s+Bucket|\s+Storage)?|Amazon\s+S3"),
    ("AWS ECS/EKS",     r"AWS\s+(?:ECS|EKS)"),
    ("AWS RDS",         r"AWS\s+RDS"),
    ("AWS CloudFormation", r"CloudFormation"),
    ("AWS CDK",         r"AWS\s+CDK"),
    # ── Azure services ────────────────────────────────────────────────────────
    ("Azure DevOps",    r"Azure\s+DevOps"),
    ("Azure Functions", r"Azure\s+Functions?"),
    ("Azure Kubernetes Service", r"\bAKS\b"),
    ("Azure Active Directory", r"Azure\s+(?:Active\s+Directory|AD)|Entra\s*ID"),
    ("Azure Service Bus", r"Azure\s+Service\s+Bus"),
    # ── Containers / Orchestration ────────────────────────────────────────────
    ("Docker",          r"\bDocker\b"),
    ("Kubernetes",      r"Kubernetes|\bK8s\b"),
    ("Helm",            r"\bHelm\b(?:\s+Chart)?"),
    ("OpenShift",       r"OpenShift"),
    ("Rancher",         r"\bRancher\b"),
    ("Podman",          r"\bPodman\b"),
    # ── Infrastructure / IaC ─────────────────────────────────────────────────
    ("Terraform",       r"Terraform"),
    ("Ansible",         r"\bAnsible\b"),
    ("Puppet",          r"\bPuppet\b"),
    ("Chef",            r"\bChef\b"),
    ("Pulumi",          r"Pulumi"),
    ("Vagrant",         r"Vagrant"),
    # ── CI/CD & DevOps ────────────────────────────────────────────────────────
    ("Jenkins",         r"\bJenkins\b"),
    ("GitLab CI",       r"GitLab\s+CI(?:/CD)?"),
    ("GitHub Actions",  r"GitHub\s+Actions"),
    ("CircleCI",        r"CircleCI"),
    ("Travis CI",       r"Travis\s+CI"),
    ("ArgoCD",          r"ArgoCD|Argo\s+CD"),
    ("Flux",            r"\bFlux(?:CD)?\b"),
    ("GitOps",          r"GitOps"),
    ("CI/CD",           r"CI/CD|Continuous\s+Integration|Continuous\s+Delivery|Continuous\s+Deployment"),
    # ── Monitoring ────────────────────────────────────────────────────────────
    ("Prometheus",      r"Prometheus"),
    ("Grafana",         r"Grafana"),
    ("Splunk",          r"Splunk"),
    ("Datadog",         r"Datadog"),
    ("New Relic",       r"New\s+Relic"),
    ("ELK Stack",       r"ELK(?:\s+Stack)?|Elasticsearch.{0,15}Kibana"),
    ("Kibana",          r"\bKibana\b"),
    ("Logstash",        r"Logstash"),
    ("Jaeger",          r"\bJaeger\b"),
    ("OpenTelemetry",   r"OpenTelemetry"),
    # ── Messaging / Streaming ─────────────────────────────────────────────────
    ("Apache Kafka",    r"Kafka"),
    ("RabbitMQ",        r"RabbitMQ"),
    ("Apache Spark",    r"Apache\s+Spark|\bSpark\b(?=\s+(?:Streaming|SQL|Job|Cluster))"),
    ("Apache Airflow",  r"Airflow"),
    ("Apache Flink",    r"\bFlink\b"),
    ("Apache Hadoop",   r"Hadoop"),
    ("Apache Hive",     r"\bHive\b"),
    ("NATS",            r"\bNATS\b"),
    ("ActiveMQ",        r"ActiveMQ"),
    ("AWS SQS",         r"\bSQS\b"),
    # ── Version control & collaboration ──────────────────────────────────────
    ("Git",             r"\bGit\b(?!Hub|Lab|Ops)"),
    ("GitHub",          r"GitHub"),
    ("GitLab",          r"GitLab(?!\s+CI)"),
    ("Bitbucket",       r"Bitbucket"),
    ("JIRA",            r"\bJIRA?\b"),
    ("Confluence",      r"Confluence"),
    ("Trello",          r"Trello"),
    # ── Data & ML / AI ────────────────────────────────────────────────────────
    ("TensorFlow",      r"TensorFlow"),
    ("PyTorch",         r"PyTorch"),
    ("scikit-learn",    r"scikit[-\s]?learn"),
    ("pandas",          r"\bpandas\b"),
    ("NumPy",           r"NumPy|Numpy"),
    ("Jupyter",         r"Jupyter(?:\s+Notebook)?"),
    ("MLflow",          r"MLflow"),
    ("Hugging Face",    r"Hugging\s+Face"),
    ("LangChain",       r"LangChain"),
    ("OpenAI",          r"OpenAI"),
    ("Power BI",        r"Power\s+BI"),
    ("Tableau",         r"Tableau"),
    ("Looker",          r"\bLooker\b"),
    ("dbt",             r"\bdbt\b"),
    ("Airbyte",         r"Airbyte"),
    ("Metabase",        r"Metabase"),
    ("Qlik",            r"\bQlik(?:View|Sense)?\b"),
    ("MicroStrategy",   r"MicroStrategy"),
    ("SSRS",            r"\bSSRS\b"),
    ("SSIS",            r"\bSSIS\b"),
    ("SSAS",            r"\bSSAS\b"),
    # ── SAP ecosystem ─────────────────────────────────────────────────────────
    ("SAP S/4HANA",     r"SAP\s+S/4\s*HANA|S/4HANA"),
    ("SAP HANA",        r"SAP\s+HANA(?!\s+S)|\bHANA\b"),
    ("SAP BW",          r"SAP\s+BW|BW/4HANA"),
    ("SAP Fiori",       r"SAP\s+Fiori|SAPUI5"),
    ("SAP CRM",         r"SAP\s+CRM"),
    ("SAP ERP",         r"SAP\s+ERP"),
    ("SAP MM",          r"\bSAP\s+MM\b"),
    ("SAP SD",          r"\bSAP\s+SD\b"),
    ("SAP FI/CO",       r"SAP\s+(?:FI|CO|FI/CO)"),
    ("SAP HCM",         r"SAP\s+HCM|Human\s+Capital\s+Management"),
    ("SAP BTP",         r"SAP\s+BTP|Business\s+Technology\s+Platform"),
    ("SAP Integration Suite", r"SAP\s+Integration\s+Suite|CPI"),
    ("SAP",             r"\bSAP\b"),
    # ── Microsoft ecosystem ───────────────────────────────────────────────────
    ("Microsoft 365",   r"Microsoft\s+365|Office\s+365|M365"),
    ("SharePoint",      r"SharePoint"),
    ("Microsoft Teams", r"Microsoft\s+Teams|\bMSTeams\b"),
    ("Power Platform",  r"Power\s+Platform"),
    ("Power Apps",      r"Power\s+Apps"),
    ("Power Automate",  r"Power\s+Automate"),
    ("Dynamics 365",    r"Dynamics\s+365"),
    ("Active Directory", r"Active\s+Directory|LDAP(?=\s+(?:und|and|with|mit))"),
    ("Microsoft Visio", r"(?:Microsoft\s+)?Visio"),
    ("Excel",           r"\bExcel\b"),
    ("Microsoft SQL Server", r"SQL\s+Server"),
    # ── Security ──────────────────────────────────────────────────────────────
    ("Penetration Testing", r"Penetration\s+Test(?:ing)?|Pentesting|PenTest"),
    ("SIEM",            r"\bSIEM\b"),
    ("IAM",             r"\bIAM\b|Identity\s+(?:and\s+)?Access\s+Management"),
    ("OAuth",           r"OAuth\s*2?(?:\.0)?"),
    ("OIDC",            r"\bOIDC\b|OpenID\s+Connect"),
    ("Keycloak",        r"Keycloak"),
    ("HashiCorp Vault", r"HashiCorp\s+Vault|\bVault\b(?=\s+(?:für|for|to|zur))"),
    ("Nessus",          r"Nessus"),
    ("Burp Suite",      r"Burp\s+Suite"),
    ("Wireshark",       r"Wireshark"),
    ("Snyk",            r"\bSnyk\b"),
    ("SonarQube",       r"SonarQube|Sonar(?=\s+Lint)"),
    ("ISO 27001",       r"ISO\s*27001"),
    ("BSI-Grundschutz", r"BSI(?:-|\s+)Grundschutz"),
    ("OWASP",           r"OWASP"),
    ("Zero Trust",      r"Zero\s+Trust"),
    ("PKI",             r"\bPKI\b"),
    ("TLS/SSL",         r"\bTLS\b|\bSSL\b"),
    # ── Networking ────────────────────────────────────────────────────────────
    ("TCP/IP",          r"TCP/IP"),
    ("DNS",             r"\bDNS\b"),
    ("VPN",             r"\bVPN\b"),
    ("Firewall",        r"Firewall"),
    ("BGP",             r"\bBGP\b"),
    ("OSPF",            r"\bOSPF\b"),
    ("SD-WAN",          r"SD-WAN"),
    ("MPLS",            r"\bMPLS\b"),
    ("Netzwerksicherheit", r"Netzwerksicherheit|Network\s+Security"),
    # ── Operating systems ─────────────────────────────────────────────────────
    ("Linux",           r"\bLinux\b"),
    ("Windows Server",  r"Windows\s+Server"),
    ("macOS",           r"\bmacOS\b|Mac\s+OS\s+X"),
    ("VMware",          r"VMware|vSphere|vCenter"),
    ("Hyper-V",         r"Hyper-V"),
    # ── Testing ───────────────────────────────────────────────────────────────
    ("JUnit",           r"\bJUnit\b"),
    ("pytest",          r"\bpytest\b"),
    ("Selenium",        r"Selenium"),
    ("Playwright",      r"\bPlaywright\b"),
    ("Cypress",         r"\bCypress\b"),
    ("Jest",            r"\bJest\b"),
    ("Postman",         r"Postman"),
    ("k6",              r"\bk6\b"),
    ("Gatling",         r"Gatling"),
    ("TestNG",          r"TestNG"),
    # ── Architecture / Methodologies ─────────────────────────────────────────
    ("Microservices",   r"Microservices?"),
    ("Event-Driven",    r"Event[-\s]Driven(?:\s+Architecture)?"),
    ("Domain-Driven Design", r"Domain[-\s]Driven\s+Design|DDD"),
    ("Clean Architecture", r"Clean\s+Architecture"),
    ("SOLID",           r"\bSOLID\b"),
    ("Design Patterns", r"Design\s+Patterns?"),
    ("Scrum",           r"\bScrum\b"),
    ("Kanban",          r"\bKanban\b"),
    ("Agile",           r"\bAgile(?:\s+Methoden)?\b"),
    ("ITIL",            r"\bITIL\b"),
    ("TOGAF",           r"\bTOGAF\b"),
    ("DevOps",          r"\bDevOps\b"),
    ("DevSecOps",       r"\bDevSecOps\b"),
    ("Site Reliability Engineering", r"Site\s+Reliability\s+Engineer(?:ing)?|SRE"),
    ("Platform Engineering", r"Platform\s+Engineering"),
    # ── Misc tools ────────────────────────────────────────────────────────────
    ("Nginx",           r"\bNginx\b"),
    ("Apache HTTP",     r"Apache\s+(?:HTTP\s+Server|Webserver|httpd)"),
    ("Tomcat",          r"\bTomcat\b"),
    ("Camunda",         r"Camunda"),
    ("BPMN",            r"\bBPMN\b"),
    ("MinIO",           r"\bMinIO\b"),
    ("Istio",           r"\bIstio\b"),
    ("Envoy",           r"\bEnvoy\b"),
    ("Linkerd",         r"Linkerd"),
    ("Celery",          r"\bCelery\b"),
    ("Solr",            r"\bSolr\b"),
    ("Figma",           r"\bFigma\b"),
    ("Sketch",          r"\bSketch\b(?=\s+(?:und|or|für|Design))"),
    ("Adobe XD",        r"Adobe\s+XD"),
]

_COMPILED: list[tuple[str, re.Pattern]] = [
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in SKILLS
]


def extract_hard_skills(text: str) -> list[str]:
    found: list[str] = []
    found_lower: set[str] = set()
    for name, rx in _COMPILED:
        if rx.search(text) and name.lower() not in found_lower:
            found.append(name)
            found_lower.add(name.lower())
    return found


def merge_skills(existing: str, extracted: list[str]) -> str:
    existing_items = [s.strip() for s in existing.split(";") if s.strip()]
    existing_lower = [s.lower() for s in existing_items]

    def already_covered(candidate: str) -> bool:
        c = candidate.lower()
        return any(c in e or e in c for e in existing_lower)

    for skill in extracted:
        if not already_covered(skill):
            existing_items.append(skill)
            existing_lower.append(skill.lower())

    return ";".join(existing_items)


def dedup_skills(skills_str: str) -> str:
    items = [s.strip() for s in skills_str.split(";") if s.strip()]
    items_lower = [s.lower() for s in items]
    keep = []
    for i, item in enumerate(items):
        il = items_lower[i]
        subsumed = any(
            j != i and (il in items_lower[j] or items_lower[j] in il)
            for j in range(len(items))
            if j != i and abs(len(items_lower[j]) - len(il)) > 1
        )
        if not subsumed:
            keep.append(item)
    return ";".join(keep)


# ── run / main ────────────────────────────────────────────────────────────────

def run():
    rows: list[dict] = []
    with open(INPUT_FILE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys()) if rows else []
    enriched = 0
    total_new = 0

    for row in rows:
        desc   = row.get("position_description", "")
        before = row["skills"]
        merged = merge_skills(before, extract_hard_skills(desc)) if desc else before
        row["skills"] = dedup_skills(merged)

        after_count  = row["skills"].count(";")
        before_count = before.count(";") if before else -1
        if after_count > before_count:
            enriched += 1
            total_new += after_count - before_count

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log.info(
        "%d/%d rows enriched, %d new skill tags added → %s",
        enriched, len(rows), total_new, OUTPUT_FILE,
    )

    top3 = sorted(rows, key=lambda r: r["skills"].count(";"), reverse=True)[:3]
    for r in top3:
        log.info("  %s | %s", r["company_name"], r["position_name"][:55])
        log.info("  skills: %s", r["skills"][:120])


def main():
    run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    main()
