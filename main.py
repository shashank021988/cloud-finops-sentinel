#!/usr/bin/env python3
"""
Cloud FinOps Sentinel - Main Entry Point
Orchestrates waste detection, rightsizing, and reporting.
"""

import argparse
import logging
from datetime import datetime
from analyzers.waste_detector import WasteDetector
from analyzers.rightsizing import RightsizingEngine
from reporters.slack_reporter import SlackReporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("finops-sentinel")


def main():
    parser = argparse.ArgumentParser(description="Cloud FinOps Sentinel")
    parser.add_argument("--subscription-id", default=None, help="Azure Subscription ID")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not delete")
    parser.add_argument("--slack-webhook", default=None, help="Slack webhook URL")
    args = parser.parse_args()

    log.info("=== Cloud FinOps Sentinel Starting ===")
    log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE - WILL DELETE WASTE'}")

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "dry_run": args.dry_run,
        "waste": {},
        "rightsizing": [],
        "total_monthly_savings_usd": 0.0
    }

    # 1. Waste Detection
    detector = WasteDetector(subscription_id=args.subscription_id, dry_run=args.dry_run)
    waste_results = detector.run_all_checks()
    report["waste"] = waste_results
    report["total_monthly_savings_usd"] += waste_results.get("total_savings_usd", 0)

    # 2. Rightsizing
    rightsizer = RightsizingEngine(subscription_id=args.subscription_id)
    sizing_results = rightsizer.analyze_all()
    report["rightsizing"] = sizing_results
    report["total_monthly_savings_usd"] += sum(r.get("monthly_savings_usd", 0) for r in sizing_results)

    log.info(f"Total estimated monthly savings: ${report['total_monthly_savings_usd']:.2f}")

    # 3. Report
    if args.slack_webhook:
        reporter = SlackReporter(webhook_url=args.slack_webhook)
        reporter.send_report(report)

    return report


if __name__ == "__main__":
    main()
