"""
Cost calculation engine.
Deterministic calculation based on CSV lookup tables.
All arithmetic uses Decimal for precision with 2-digit rounding.
License: MIT
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd

from models.schemas import (
    ExtractedParameters,
    RegistryItem,
    CostBreakdownItem,
    CostCalculationResponse,
    TaskType,
    ComponentLevel,
)


logger = logging.getLogger(__name__)


class CostCalculator:
    """
    Deterministic cost calculation engine.
    Uses CSV lookup tables for effort norms and hourly rates.
    All calculations use Decimal for financial precision.
    """
    
    def __init__(
        self,
        development_effort_path: Path,
        support_effort_path: Path,
        hourly_rates_path: Path,
    ):
        """
        Initialize calculator with CSV data paths.
        
        Args:
            development_effort_path: Path to development effort CSV
            support_effort_path: Path to support effort CSV
            hourly_rates_path: Path to hourly rates CSV
        """
        self.development_effort_df = pd.read_csv(development_effort_path)
        self.support_effort_df = pd.read_csv(support_effort_path)
        self.hourly_rates_df = pd.read_csv(hourly_rates_path)
        
        logger.info("CostCalculator initialized with CSV tables.")
    
    def _round_decimal(self, value: Decimal) -> float:
        """Round Decimal to 2 decimal places using ROUND_HALF_UP."""
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    
    def _lookup_development_effort(
        self, task_type: str, component: str
    ) -> Optional[Decimal]:
        """Lookup development effort hours from CSV."""
        mask = (
            (self.development_effort_df["task_type"] == task_type) &
            (self.development_effort_df["component"] == component)
        )
        matched = self.development_effort_df[mask]
        
        if matched.empty:
            return None
        
        hours = matched.iloc[0]["effort_hours"]
        return Decimal(str(hours))
    
    def _lookup_support_effort(
        self, task_type: str, component: str
    ) -> Optional[Decimal]:
        """Lookup annual support effort hours from CSV."""
        mask = (
            (self.support_effort_df["task_type"] == task_type) &
            (self.support_effort_df["component"] == component)
        )
        matched = self.support_effort_df[mask]
        
        if matched.empty:
            return None
        
        hours = matched.iloc[0]["support_effort_hours_per_year"]
        return Decimal(str(hours))
    
    def _get_hourly_rate(self, role: str) -> Decimal:
        """Get hourly rate for a role from CSV."""
        mask = self.hourly_rates_df["role"] == role
        matched = self.hourly_rates_df[mask]
        
        if matched.empty:
            # Default to developer rate
            return Decimal("3500.00")
        
        rate = matched.iloc[0]["hourly_rate_rub"]
        return Decimal(str(rate))
    
    def _calculate_registry_costs(
        self, 
        registry: RegistryItem, 
        dev_rate: Decimal, 
        support_rate: Decimal,
        requires_support: bool
    ) -> Tuple[List[CostBreakdownItem], List[CostBreakdownItem], List[str]]:
        """
        Calculate costs for a single registry item.
        
        Returns:
            Tuple of (development_breakdown, support_breakdown, components_included)
        """
        development_breakdown: List[CostBreakdownItem] = []
        support_breakdown: List[CostBreakdownItem] = []
        components_included: List[str] = []
        
        # Main task development effort
        main_effort = self._lookup_development_effort(
            registry.task_type.value, registry.component.value
        )
        
        if main_effort is None:
            # Use default effort based on task type
            default_efforts = {
                "manual_registry": Decimal("6"),
                "external_integration": Decimal("19"),
                "classification_registry": Decimal("30"),
                "reference_data": Decimal("15"),
                "master_data": Decimal("45"),
                "ui_component": Decimal("8"),
                "data_migration": Decimal("10"),
                "documentation": Decimal("4"),
            }
            main_effort = default_efforts.get(registry.task_type.value, Decimal("10"))
            logger.warning(f"Using default effort for {registry.task_type.value}")
        
        # Multiply by quantity
        total_main_effort = main_effort * registry.quantity
        main_cost = total_main_effort * dev_rate
        
        component_name = f"{registry.task_type.value}:{registry.component.value}"
        if registry.quantity > 1:
            component_name += f" (x{registry.quantity})"
        
        development_breakdown.append(
            CostBreakdownItem(
                component=component_name,
                effort_hours=self._round_decimal(total_main_effort),
                rate_rub=self._round_decimal(dev_rate),
                cost_rub=self._round_decimal(main_cost),
            )
        )
        components_included.append(component_name)
        
        # External integration adjustment
        if registry.has_external_integration:
            integration_effort = self._lookup_development_effort(
                "external_integration", "api_integration"
            )
            if integration_effort is None:
                integration_effort = Decimal("10")
            
            # Multiply by quantity
            total_integration_effort = integration_effort * registry.quantity
            integration_cost = total_integration_effort * dev_rate
            
            integration_component = "external_integration"
            if registry.quantity > 1:
                integration_component += f" (x{registry.quantity})"
            
            development_breakdown.append(
                CostBreakdownItem(
                    component=integration_component,
                    effort_hours=self._round_decimal(total_integration_effort),
                    rate_rub=self._round_decimal(dev_rate),
                    cost_rub=self._round_decimal(integration_cost),
                )
            )
            components_included.append(integration_component)
        
        # Validation rules adjustment
        if registry.has_validation_rules:
            validation_effort = self._lookup_development_effort(
                "manual_registry", "validation_rules"
            )
            if validation_effort is None:
                validation_effort = Decimal("6")
            
            # Multiply by quantity
            total_validation_effort = validation_effort * registry.quantity
            validation_cost = total_validation_effort * dev_rate
            
            validation_component = "validation_rules"
            if registry.quantity > 1:
                validation_component += f" (x{registry.quantity})"
            
            development_breakdown.append(
                CostBreakdownItem(
                    component=validation_component,
                    effort_hours=self._round_decimal(total_validation_effort),
                    rate_rub=self._round_decimal(dev_rate),
                    cost_rub=self._round_decimal(validation_cost),
                )
            )
            components_included.append(validation_component)
        
        # Additional components
        additional_component_mapping = {
            "audit_log": ("ui_component", "audit_log"),
            "bulk_operations": ("ui_component", "bulk_operations"),
            "search_filter": ("ui_component", "search_filter"),
            "grid_view": ("ui_component", "grid_view"),
        }
        
        for add_component in registry.additional_components:
            if add_component in additional_component_mapping:
                task_t, comp = additional_component_mapping[add_component]
                add_effort = self._lookup_development_effort(task_t, comp)
                
                if add_effort is not None:
                    # Multiply by quantity
                    total_add_effort = add_effort * registry.quantity
                    add_cost = total_add_effort * dev_rate
                    
                    add_comp_name = add_component
                    if registry.quantity > 1:
                        add_comp_name += f" (x{registry.quantity})"
                    
                    development_breakdown.append(
                        CostBreakdownItem(
                            component=add_comp_name,
                            effort_hours=self._round_decimal(total_add_effort),
                            rate_rub=self._round_decimal(dev_rate),
                            cost_rub=self._round_decimal(add_cost),
                        )
                    )
                    components_included.append(add_comp_name)
        
        # Support calculation (only if explicitly requested)
        if requires_support:
            support_effort = self._lookup_support_effort(
                registry.task_type.value, registry.component.value
            )
            
            if support_effort is None:
                # Default: external integrations require 2 hours/week if manual,
                # manual registries require 0.1 hours/week for infrastructure
                if registry.task_type == TaskType.EXTERNAL_INTEGRATION:
                    # If this were manual, it would take 2 hours/week to fill
                    support_effort = Decimal("2")
                else:
                    # Infrastructure overhead for manual registries
                    support_effort = Decimal("0.1")
            else:
                # Override with business logic from requirements:
                # - External integration: 2 hours/week (regardless of CSV value)
                # - Manual registry: 0.1 hours/week for infrastructure only
                if registry.task_type == TaskType.EXTERNAL_INTEGRATION:
                    support_effort = Decimal("2")
                elif registry.task_type == TaskType.MANUAL_REGISTRY:
                    support_effort = Decimal("0.1")
            
            # Multiply by quantity and by 52 weeks for annual
            annual_support_effort = support_effort * registry.quantity * Decimal("52")
            support_cost = annual_support_effort * support_rate
            
            support_component = f"{registry.task_type.value}:support"
            if registry.quantity > 1:
                support_component += f" (x{registry.quantity})"
            support_component += f" ({support_effort} ч/нед)"
            
            support_breakdown.append(
                CostBreakdownItem(
                    component=support_component,
                    effort_hours=self._round_decimal(annual_support_effort),
                    rate_rub=self._round_decimal(support_rate),
                    cost_rub=self._round_decimal(support_cost),
                )
            )
            components_included.append(support_component)
        
        return development_breakdown, support_breakdown, components_included
    
    def calculate(
        self, params: ExtractedParameters
    ) -> CostCalculationResponse:
        """
        Calculate development and support costs based on extracted parameters.
        
        Args:
            params: Validated ExtractedParameters object
            
        Returns:
            CostCalculationResponse with detailed breakdown
        """
        # Check for unknown task type in all registries
        has_unknown = any(r.task_type == TaskType.UNKNOWN for r in params.registries)
        if has_unknown:
            return CostCalculationResponse(
                success=False,
                error_message="Описание не относится к сфере справочников и реестров (Reference Data Management / Master Data Management). Пожалуйста, опишите задачу разработки справочника, реестра или мастер-данных.",
                error_code="OUT_OF_SCOPE",
                development_total_hours=0.0,
                development_total_cost_rub=0.0,
                support_total_hours_per_year=0.0,
                support_total_cost_per_year_rub=0.0,
                summary="Запрос отклонен: не относится к целевому сценарию.",
                registry_name=", ".join(r.registry_name for r in params.registries),
                components_included=[],
            )
        
        all_dev_breakdown: List[CostBreakdownItem] = []
        all_support_breakdown: List[CostBreakdownItem] = []
        all_components: List[str] = []
        
        dev_rate = self._get_hourly_rate("developer")
        support_rate = self._get_hourly_rate("support")
        
        # Process each registry
        for idx, registry in enumerate(params.registries):
            dev_breakdown, support_breakdown, components = self._calculate_registry_costs(
                registry, dev_rate, support_rate, params.requires_support
            )
            
            # Add index prefix if multiple registries
            if len(params.registries) > 1:
                for item in dev_breakdown:
                    item.component = f"[{idx+1}] {item.component}"
                for item in support_breakdown:
                    item.component = f"[{idx+1}] {item.component}"
                components = [f"[{idx+1}] {c}" for c in components]
            
            all_dev_breakdown.extend(dev_breakdown)
            all_support_breakdown.extend(support_breakdown)
            all_components.extend(components)
        
        # Calculate totals
        total_dev_hours = sum(
            Decimal(str(item.effort_hours)) for item in all_dev_breakdown
        )
        total_dev_cost = sum(
            Decimal(str(item.cost_rub)) for item in all_dev_breakdown
        )
        
        total_support_hours = sum(
            Decimal(str(item.effort_hours)) for item in all_support_breakdown
        )
        total_support_cost = sum(
            Decimal(str(item.cost_rub)) for item in all_support_breakdown
        )
        
        # Build summary
        registry_names = ", ".join(r.registry_name for r in params.registries)
        summary_parts = [
            f"Справочники: {registry_names}",
            f"Всего справочников: {len(params.registries)}",
            f"Компоненты: {', '.join(all_components[:5])}" + ("..." if len(all_components) > 5 else ""),
            f"Ставка разработки: {self._round_decimal(dev_rate)} руб/час",
        ]
        
        if params.requires_support:
            summary_parts.append(
                f"Ставка поддержки: {self._round_decimal(support_rate)} руб/час"
            )
        
        summary_parts.append(
            f"Итого разработка: {self._round_decimal(total_dev_hours)} ч × ставка = {self._round_decimal(total_dev_cost)} руб."
        )
        
        if params.requires_support:
            summary_parts.append(
                f"Итого поддержка (год): {self._round_decimal(total_support_hours)} ч × ставка = {self._round_decimal(total_support_cost)} руб./год"
            )
        
        summary = " | ".join(summary_parts)
        
        return CostCalculationResponse(
            success=True,
            error_message=None,
            development_total_hours=self._round_decimal(total_dev_hours),
            development_total_cost_rub=self._round_decimal(total_dev_cost),
            support_total_hours_per_year=self._round_decimal(total_support_hours),
            support_total_cost_per_year_rub=self._round_decimal(total_support_cost),
            development_breakdown=all_dev_breakdown,
            support_breakdown=all_support_breakdown,
            summary=summary,
            registry_name=registry_names,
            components_included=all_components,
        )
