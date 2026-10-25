# Cloud FinOps Sentinel

Serverless cloud financial management bot that automatically detects and eliminates cloud waste across Azure and AWS.

## Features
- Detects unattached managed disks, orphan snapshots, idle public IPs
- VM rightsizing recommendations via Azure Monitor metrics
- Auto-schedules non-prod workloads to save costs off-hours
- Infracost PR gates blocking budget overruns
- Slack/Teams notifications with savings breakdown

## Impact
- Saved **32% cloud OPEX** across 100+ workloads
- Fully automated, zero manual intervention required

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Azure credentials
python main.py --dry-run
```
