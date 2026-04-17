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
    
    def _round_decimal(self, value) -> float:
        """Round Decimal to 2 decimal places using ROUND_HALF_UP."""
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
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
        # Check for unknown task type
        if params.task_type == TaskType.UNKNOWN:
            return CostCalculationResponse(
                success=False,
                error_message="Описание не относится к сфере справочников и реестров (Reference Data Management / Master Data Management). Пожалуйста, опишите задачу разработки справочника, реестра или мастер-данных.",
                error_code="OUT_OF_SCOPE",
                development_total_hours=0.0,
                development_total_cost_rub=0.0,
                support_total_hours_per_year=0.0,
                support_total_cost_per_year_rub=0.0,
                summary="Запрос отклонен: не относится к целевому сценарию.",
                registry_name=params.registry_name,
                components_included=[],
            )
        
        development_breakdown: List[CostBreakdownItem] = []
        support_breakdown: List[CostBreakdownItem] = []
        components_included: List[str] = []
        
        dev_rate = self._get_hourly_rate("developer")
        support_rate = self._get_hourly_rate("support")
        
        # Main task development effort
        main_effort = self._lookup_development_effort(
            params.task_type.value, params.component.value
        )
        
        if main_effort is None:
            # Use default effort based on task type
            default_efforts = {
                "manual_registry": Decimal("6"),
                "external_integration": Decimal("10"),
                "classification_registry": Decimal("30"),
                "reference_data": Decimal("15"),
                "master_data": Decimal("45"),
                "ui_component": Decimal("8"),
                "data_migration": Decimal("10"),
                "documentation": Decimal("4"),
            }
            main_effort = default_efforts.get(params.task_type.value, Decimal("10"))
            logger.warning(f"Using default effort for {params.task_type.value}")
        
        main_cost = main_effort * dev_rate
        development_breakdown.append(
            CostBreakdownItem(
                component=f"{params.task_type.value}:{params.component.value}",
                effort_hours=self._round_decimal(main_effort),
                rate_rub=self._round_decimal(dev_rate),
                cost_rub=self._round_decimal(main_cost),
            )
        )
        components_included.append(f"{params.task_type.value}:{params.component.value}")
        
        # Additional components
        additional_component_mapping = {
            "audit_log": ("ui_component", "audit_log"),
            "bulk_operations": ("ui_component", "bulk_operations"),
            "search_filter": ("ui_component", "search_filter"),
            "grid_view": ("ui_component", "grid_view"),
        }
        
        for add_component in params.additional_components:
            if add_component in additional_component_mapping:
                task_t, comp = additional_component_mapping[add_component]
                add_effort = self._lookup_development_effort(task_t, comp)
                
                if add_effort is not None:
                    add_cost = add_effort * dev_rate
                    development_breakdown.append(
                        CostBreakdownItem(
                            component=add_component,
                            effort_hours=self._round_decimal(add_effort),
                            rate_rub=self._round_decimal(dev_rate),
                            cost_rub=self._round_decimal(add_cost),
                        )
                    )
                    components_included.append(add_component)
        
        # External integration adjustment
        if params.has_external_integration:
            integration_effort = self._lookup_development_effort(
                "external_integration", "api_integration"
            )
            if integration_effort is None:
                integration_effort = Decimal("10")
            
            integration_cost = integration_effort * dev_rate
            development_breakdown.append(
                CostBreakdownItem(
                    component="external_integration",
                    effort_hours=self._round_decimal(integration_effort),
                    rate_rub=self._round_decimal(dev_rate),
                    cost_rub=self._round_decimal(integration_cost),
                )
            )
            components_included.append("external_integration")
        
        # Validation rules adjustment
        if params.has_validation_rules:
            validation_effort = self._lookup_development_effort(
                "manual_registry", "validation_rules"
            )
            if validation_effort is None:
                validation_effort = Decimal("6")
            
            validation_cost = validation_effort * dev_rate
            development_breakdown.append(
                CostBreakdownItem(
                    component="validation_rules",
                    effort_hours=self._round_decimal(validation_effort),
                    rate_rub=self._round_decimal(dev_rate),
                    cost_rub=self._round_decimal(validation_cost),
                )
            )
            components_included.append("validation_rules")
        
        # Calculate totals
        total_dev_hours = sum(
            Decimal(str(item.effort_hours)) for item in development_breakdown
        )
        total_dev_cost = sum(
            Decimal(str(item.cost_rub)) for item in development_breakdown
        )
        
        # Support calculation (only if explicitly requested)
        if params.requires_support:
            support_effort = self._lookup_support_effort(
                params.task_type.value, params.component.value
            )
            
            if support_effort is None:
                support_effort = Decimal("5")  # Default support hours
            
            support_cost = support_effort * support_rate
            support_breakdown.append(
                CostBreakdownItem(
                    component=f"{params.task_type.value}:support",
                    effort_hours=self._round_decimal(support_effort),
                    rate_rub=self._round_decimal(support_rate),
                    cost_rub=self._round_decimal(support_cost),
                )
            )
            components_included.append("support")
        
        total_support_hours = sum(
            Decimal(str(item.effort_hours)) for item in support_breakdown
        )
        total_support_cost = sum(
            Decimal(str(item.cost_rub)) for item in support_breakdown
        )
        
        # Build summary
        summary_parts = [
            f"Справочник: {params.registry_name}",
            f"Тип задачи: {params.task_type.value}",
            f"Компоненты: {', '.join(components_included)}",
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
            development_breakdown=development_breakdown,
            support_breakdown=support_breakdown,
            summary=summary,
            registry_name=params.registry_name,
            components_included=components_included,
        )
