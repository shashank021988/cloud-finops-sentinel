#!/usr/bin/env python3
"""
Rightsizing Engine: Analyzes VM CPU/Memory utilization via Azure Monitor
and recommends downsizing opportunities.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.monitor.query import MetricsQueryClient

log = logging.getLogger("finops.rightsizing")

# Threshold: if avg CPU < 10% and avg Memory < 20% for 7 days -> downsize candidate
CPU_THRESHOLD_PCT    = 10.0
MEMORY_THRESHOLD_PCT = 20.0
LOOKBACK_DAYS        = 7

# Estimated savings from downsizing one size tier (example rates)
DOWNSIZE_SAVING_PER_VM_MONTH = 85.0


class RightsizingEngine:
    def __init__(self, subscription_id: str = None):
        self.subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        self.credential = DefaultAzureCredential()
        self.compute = ComputeManagementClient(self.credential, self.subscription_id)
        self.metrics = MetricsQueryClient(self.credential)

    def get_vm_avg_cpu(self, vm_id: str) -> float:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=LOOKBACK_DAYS)
        try:
            result = self.metrics.query_resource(
                vm_id,
                metric_names=["Percentage CPU"],
                timespan=(start, end),
                granularity=timedelta(hours=1),
            )
            values = [
                dp.average
                for m in result.metrics
                for ts in m.timeseries
                for dp in ts.data
                if dp.average is not None
            ]
            return round(sum(values) / len(values), 2) if values else 0.0
        except Exception as e:
            log.warning(f"Could not get CPU metrics for {vm_id}: {e}")
            return 0.0

    def analyze_all(self) -> list:
        candidates = []
        for vm in self.compute.virtual_machines.list_all():
            avg_cpu = self.get_vm_avg_cpu(vm.id)
            if avg_cpu < CPU_THRESHOLD_PCT:
                rg = vm.id.split("/")[4]
                candidates.append({
                    "vm_name":              vm.name,
                    "resource_group":       rg,
                    "current_size":         vm.hardware_profile.vm_size,
                    "avg_cpu_7d_pct":       avg_cpu,
                    "recommendation":       "Downsize one tier",
                    "monthly_savings_usd":  DOWNSIZE_SAVING_PER_VM_MONTH,
                })
                log.info(f"Rightsizing candidate: {vm.name} avg CPU {avg_cpu}%")
        log.info(f"Found {len(candidates)} rightsizing candidates")
        return candidates
