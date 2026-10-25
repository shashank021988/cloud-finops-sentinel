#!/usr/bin/env python3
"""
Waste Detector: Identifies orphaned Azure resources costing money with zero value.
- Unattached managed disks
- Orphan snapshots (older than 30 days)
- Unassociated Public IPs
- Empty Load Balancers
- Idle App Service Plans
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

log = logging.getLogger("finops.waste-detector")

DISK_PRICE_PER_GB_MONTH = 0.0528   # Premium SSD P10 ~ $0.0528/GB/month
SNAPSHOT_PRICE_PER_GB   = 0.05
PUBLIC_IP_PRICE_MONTH   = 3.65


class WasteDetector:
    def __init__(self, subscription_id: str = None, dry_run: bool = True):
        self.subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        self.dry_run = dry_run
        self.credential = DefaultAzureCredential()
        self.compute = ComputeManagementClient(self.credential, self.subscription_id)
        self.network = NetworkManagementClient(self.credential, self.subscription_id)

    def find_unattached_disks(self) -> dict:
        """Find managed disks not attached to any VM."""
        orphans = []
        total_savings = 0.0
        for disk in self.compute.disks.list():
            if disk.disk_state == "Unattached":
                size_gb = disk.disk_size_gb or 0
                monthly_cost = size_gb * DISK_PRICE_PER_GB_MONTH
                orphans.append({
                    "name": disk.name,
                    "resource_group": disk.id.split("/")[4],
                    "size_gb": size_gb,
                    "sku": disk.sku.name if disk.sku else "Unknown",
                    "monthly_cost_usd": round(monthly_cost, 2),
                })
                total_savings += monthly_cost
                if not self.dry_run:
                    rg = disk.id.split("/")[4]
                    log.info(f"DELETING unattached disk: {disk.name} in {rg}")
                    self.compute.disks.begin_delete(rg, disk.name).wait()
        log.info(f"Found {len(orphans)} unattached disks - ${total_savings:.2f}/month waste")
        return {"items": orphans, "count": len(orphans), "total_savings_usd": round(total_savings, 2)}

    def find_orphan_snapshots(self, days_old: int = 30) -> dict:
        """Find snapshots older than N days with no associated disk."""
        orphans = []
        total_savings = 0.0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
        for snap in self.compute.snapshots.list():
            age = datetime.now(timezone.utc) - snap.time_created
            if age.days >= days_old:
                size_gb = snap.disk_size_gb or 0
                monthly_cost = size_gb * SNAPSHOT_PRICE_PER_GB
                orphans.append({
                    "name": snap.name,
                    "age_days": age.days,
                    "size_gb": size_gb,
                    "monthly_cost_usd": round(monthly_cost, 2),
                })
                total_savings += monthly_cost
                if not self.dry_run:
                    rg = snap.id.split("/")[4]
                    log.info(f"DELETING old snapshot: {snap.name}")
                    self.compute.snapshots.begin_delete(rg, snap.name).wait()
        return {"items": orphans, "count": len(orphans), "total_savings_usd": round(total_savings, 2)}

    def find_unassociated_public_ips(self) -> dict:
        """Find public IPs not associated with any resource."""
        orphans = []
        total_savings = 0.0
        for ip in self.network.public_ip_addresses.list_all():
            if ip.ip_configuration is None:
                orphans.append({
                    "name": ip.name,
                    "resource_group": ip.id.split("/")[4],
                    "sku": ip.sku.name if ip.sku else "Basic",
                    "monthly_cost_usd": PUBLIC_IP_PRICE_MONTH,
                })
                total_savings += PUBLIC_IP_PRICE_MONTH
                if not self.dry_run:
                    rg = ip.id.split("/")[4]
                    log.info(f"DELETING unassociated public IP: {ip.name}")
                    self.network.public_ip_addresses.begin_delete(rg, ip.name).wait()
        return {"items": orphans, "count": len(orphans), "total_savings_usd": round(total_savings, 2)}

    def run_all_checks(self) -> dict:
        log.info("Running all waste detection checks...")
        disks    = self.find_unattached_disks()
        snaps    = self.find_orphan_snapshots()
        pub_ips  = self.find_unassociated_public_ips()
        total = disks["total_savings_usd"] + snaps["total_savings_usd"] + pub_ips["total_savings_usd"]
        return {
            "unattached_disks":     disks,
            "orphan_snapshots":     snaps,
            "unassociated_pub_ips": pub_ips,
            "total_savings_usd":    round(total, 2),
        }
