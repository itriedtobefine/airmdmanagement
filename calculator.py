"""
Расчетный движок для оценки стоимости разработки и поддержки справочников.
"""

import pandas as pd
import os
from typing import Dict, List, Optional, Tuple

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class CostCalculator:
    """Калькулятор стоимости разработки и поддержки."""
    
    def __init__(self):
        self.dev_norms = self._load_csv("development_norms.csv")
        self.support_norms = self._load_csv("support_norms.csv")
        self.hourly_rates = self._load_csv("hourly_rates.csv")
        
        # Ставки по умолчанию (руб/час)
        self.default_dev_rate = 2500
        self.default_qa_rate = 1800
        self.default_support_rate = 1500
        self.default_analyst_rate = 2200
    
    def _load_csv(self, filename: str) -> pd.DataFrame:
        """Загружает CSV файл с нормативами."""
        filepath = os.path.join(DATA_DIR, filename)
        return pd.read_csv(filepath)
    
    def get_development_hours(self, task_type: str) -> int:
        """Получает норматив времени на разработку по типу задачи."""
        row = self.dev_norms[self.dev_norms["task_type"] == task_type]
        if not row.empty:
            return int(row.iloc[0]["hours"])
        return 0  # Задача не найдена
    
    def get_support_hours_per_month(self, support_type: str) -> int:
        """Получает норматив времени на поддержку в месяц."""
        row = self.support_norms[self.support_norms["task_type"] == support_type]
        if not row.empty:
            return int(row.iloc[0]["hours_per_month"])
        return 0
    
    def get_hourly_rate(self, role: str) -> int:
        """Получает часовую ставку специалиста."""
        row = self.hourly_rates[self.hourly_rates["role"] == role]
        if not row.empty:
            return int(row.iloc[0]["hourly_rate"])
        return self.default_dev_rate
    
    def calculate_development_cost(
        self, 
        tasks: List[str],
        include_qa: bool = True,
        include_analysis: bool = True
    ) -> Tuple[int, Dict]:
        """
        Рассчитывает стоимость разработки.
        
        Returns:
            Tuple[int, Dict]: Общая стоимость и детализация
        """
        total_hours = 0
        breakdown = {
            "development": {"hours": 0, "cost": 0},
            "qa": {"hours": 0, "cost": 0},
            "analysis": {"hours": 0, "cost": 0},
            "tasks": []
        }
        
        # Суммируем часы на разработку
        for task_type in tasks:
            hours = self.get_development_hours(task_type)
            if hours > 0:
                total_hours += hours
                breakdown["tasks"].append({
                    "type": task_type,
                    "hours": hours
                })
        
        # Если задачи не найдены, используем среднее значение
        if total_hours == 0 and tasks:
            total_hours = 20  # Базовая оценка
            breakdown["tasks"].append({
                "type": "custom",
                "hours": total_hours,
                "note": "Оценка по умолчанию (задачи не найдены в нормативах)"
            })
        
        breakdown["development"]["hours"] = total_hours
        breakdown["development"]["cost"] = total_hours * self.default_dev_rate
        
        # Добавляем тестирование (20% от разработки)
        if include_qa:
            qa_hours = int(total_hours * 0.2)
            breakdown["qa"]["hours"] = qa_hours
            breakdown["qa"]["cost"] = qa_hours * self.default_qa_rate
            total_hours += qa_hours
        
        # Добавляем анализ (10% от разработки)
        if include_analysis:
            analysis_hours = int(total_hours * 0.1)
            breakdown["analysis"]["hours"] = analysis_hours
            breakdown["analysis"]["cost"] = analysis_hours * self.default_analyst_rate
        
        total_cost = (
            breakdown["development"]["cost"] +
            breakdown["qa"]["cost"] +
            breakdown["analysis"]["cost"]
        )
        
        return total_cost, breakdown
    
    def calculate_support_cost(
        self,
        support_types: List[str],
        custom_hours_per_month: Optional[int] = None,
        months: int = 12
    ) -> Tuple[int, Dict]:
        """
        Рассчитывает годовую стоимость поддержки.
        
        Args:
            support_types: Типы поддержки
            custom_hours_per_month: Пользовательские часы на поддержку (если указаны)
            months: Количество месяцев для расчета
        
        Returns:
            Tuple[int, Dict]: Годовая стоимость и детализация
        """
        breakdown = {
            "monthly_hours": 0,
            "yearly_hours": 0,
            "cost": 0,
            "types": []
        }
        
        if custom_hours_per_month:
            # Используем пользовательское значение
            breakdown["monthly_hours"] = custom_hours_per_month
            breakdown["types"].append({
                "type": "custom",
                "hours_per_month": custom_hours_per_month,
                "note": "Указано пользователем"
            })
        else:
            # Рассчитываем по нормативам
            total_monthly = 0
            for support_type in support_types:
                hours = self.get_support_hours_per_month(support_type)
                if hours > 0:
                    total_monthly += hours
                    breakdown["types"].append({
                        "type": support_type,
                        "hours_per_month": hours
                    })
            
            # Если ничего не найдено, используем базовое значение
            if total_monthly == 0 and support_types:
                total_monthly = 8  # Базовая оценка
                breakdown["types"].append({
                    "type": "default",
                    "hours_per_month": total_monthly,
                    "note": "Оценка по умолчанию"
                })
            
            breakdown["monthly_hours"] = total_monthly
        
        breakdown["yearly_hours"] = breakdown["monthly_hours"] * months
        breakdown["cost"] = breakdown["yearly_hours"] * self.default_support_rate
        
        return breakdown["cost"], breakdown
    
    def generate_summary(
        self,
        dev_cost: int,
        dev_breakdown: Dict,
        support_cost: int,
        support_breakdown: Dict,
        tech_stack: List[str]
    ) -> str:
        """Генерирует текстовое обоснование результата."""
        lines = [
            "\n=== ОБОСНОВАНИЕ РАСЧЕТА ===\n",
            "📋 УЧТЕННЫЕ КОМПОНЕНТЫ:",
        ]
        
        # Компоненты разработки
        if dev_breakdown["tasks"]:
            for task in dev_breakdown["tasks"]:
                task_name = self._get_task_description(task["type"])
                lines.append(f"  • {task_name}: {task['hours']} ч.")
        
        lines.append(f"\n💰 ЗАДЕЙСТВОВАННЫЕ СПЕЦИАЛИСТЫ:")
        lines.append(f"  • Разработчики: {dev_breakdown['development']['hours']} ч. × {self.default_dev_rate} ₽ = {dev_breakdown['development']['cost']:,} ₽")
        
        if dev_breakdown["qa"]["hours"] > 0:
            lines.append(f"  • Тестировщики: {dev_breakdown['qa']['hours']} ч. × {self.default_qa_rate} ₽ = {dev_breakdown['qa']['cost']:,} ₽")
        
        if dev_breakdown["analysis"]["hours"] > 0:
            lines.append(f"  • Аналитики: {dev_breakdown['analysis']['hours']} ч. × {self.default_analyst_rate} ₽ = {dev_breakdown['analysis']['cost']:,} ₽")
        
        lines.append(f"\n🔧 ТЕХНОЛОГИЧЕСКИЙ СТЕК: {', '.join(tech_stack) if tech_stack else 'Не указан'}")
        
        lines.append(f"\n📊 ПОДДЕРЖКА:")
        lines.append(f"  • Часов в месяц: {support_breakdown['monthly_hours']}")
        lines.append(f"  • Часов в год: {support_breakdown['yearly_hours']}")
        lines.append(f"  • Стоимость поддержки: {support_cost:,} ₽")
        
        lines.append(f"\n💵 ИТОГО:")
        lines.append(f"  • Разработка: {dev_cost:,} ₽")
        lines.append(f"  • Годовая поддержка: {support_cost:,} ₽")
        lines.append(f"  • Общий бюджет (первый год): {dev_cost + support_cost:,} ₽")
        
        return "\n".join(lines)
    
    def _get_task_description(self, task_type: str) -> str:
        """Получает описание задачи из нормативов."""
        row = self.dev_norms[self.dev_norms["task_type"] == task_type]
        if not row.empty:
            return row.iloc[0]["description"]
        return task_type
