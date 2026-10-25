import httpx
import logging
from datetime import datetime

log = logging.getLogger("finops.reporter")


class SlackReporter:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_report(self, report: dict):
        waste = report.get("waste", {})
        total_savings = report.get("total_monthly_savings_usd", 0)
        rightsizing_count = len(report.get("rightsizing", []))

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "Cloud FinOps Sentinel Report"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Timestamp:* {report['timestamp']}\n*Mode:* {'Dry Run' if report['dry_run'] else 'Live'}"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": (
                f"*Waste Detected:*\n"
                f"  Unattached Disks: {waste.get('unattached_disks', {}).get('count', 0)} "
                f"(${waste.get('unattached_disks', {}).get('total_savings_usd', 0):.2f}/mo)\n"
                f"  Orphan Snapshots: {waste.get('orphan_snapshots', {}).get('count', 0)} "
                f"(${waste.get('orphan_snapshots', {}).get('total_savings_usd', 0):.2f}/mo)\n"
                f"  Idle Public IPs: {waste.get('unassociated_pub_ips', {}).get('count', 0)} "
                f"(${waste.get('unassociated_pub_ips', {}).get('total_savings_usd', 0):.2f}/mo)\n"
                f"  Rightsizing VMs: {rightsizing_count} candidates"
            )}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f":moneybag: *Total Estimated Monthly Savings: ${total_savings:.2f}*"}},
        ]
        payload = {"blocks": blocks}
        r = httpx.post(self.webhook_url, json=payload, timeout=10)
        if r.status_code == 200:
            log.info("Slack report sent successfully")
        else:
            log.error(f"Slack report failed: {r.status_code} {r.text}")
