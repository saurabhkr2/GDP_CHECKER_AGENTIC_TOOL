# GDP Checker Monitoring - Raw Usage Data

Captures **raw per-session usage data** like `ChatGPT_May.csv` and `Github_May.csv`.

## Raw Data Columns

| Column | Description |
|--------|-------------|
| `timestamp` | ISO datetime |
| `period_start` | First day of month |
| `period_end` | Last day of month |
| `period_month` | Month name (June) |
| `user_email` | Employee email |
| `session_id` | Unique session ID |
| `document_name` | Document reviewed |
| `template_name` | Template used |
| `checks_run` | Checks executed (21) |
| `findings_total` | Total findings |
| `findings_critical/major/moderate/minor` | By severity |
| `comments_generated` | AI-drafted |
| `comments_approved` | Human approved |
| `comments_rejected` | Human rejected |
| `comments_edited` | Human edited |
| `processing_time_seconds` | Processing time |
| `review_time_seconds` | Review time |
| `status` | completed/error |
| `productivity_hours_saved` | Hours saved |

## Quick Start

```python
from monitoring import get_collector, get_storage

collector = get_collector()
collector.start_session("abc123", "user@philips.com", "doc.docx")
collector.record_findings("abc123", findings_list)
collector.record_review("abc123", approved=5, rejected=2, edited=1)
collector.complete_session("abc123")

# Export to CSV
storage = get_storage()
storage.export_to_csv("GDP_Checker_June.csv", period_month="June")
```

## Export

```bash
python -m monitoring.export -o GDP_Checker_June.csv -p June
```

## Config

```bash
export GDP_CHECKER_MONITORING_DB=/var/data/usage.db
```
