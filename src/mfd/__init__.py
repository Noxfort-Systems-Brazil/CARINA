# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Macroscopic Fundamental Diagram (MFD) Package.

Architected following SOLID, DDD, and Clean Architecture principles:
- Orchestrators & Facades: mfd.py, mfd_processor.py, mfd_analyzer.py, mfd_report_generator.py, mfd_worker.py
- Domain Layer (Value Objects, Entities, Services): snapshot, calculator, tracker, classifier, metrics, comparisons, impacts
- Application Layer: data_normalizer, prompt_builder, section_builder, template_provider, neural_proofreader
- Infrastructure Layer: network_parser, db_fetcher, baseline_manager, template_repository, subprocess_fallback
"""

from mfd.mfd import (
    MacroscopicFundamentalDiagram,
    MFDCalculator,
    MFDClassifier,
    MFDSnapshot,
    MFDTracker,
    NetworkState,
)
from mfd.mfd_analyzer import (
    MFDAnalyzer,
    MFDComparisonEngine,
    MFDDataNormalizer,
    MFDFallbackFactory,
    MFDImpactCalculator,
    MFDImpactLabels,
    MFDIntersectionMetricsCalculator,
    MFDMapResolver,
    MFDMaturityEvaluator,
    MFDMetricsCalculator,
    MFDReportBaselineManager,
    MFDStageAggregator,
    MFDZoneCalculator,
)
from mfd.mfd_plotter import MFDPlotter
from mfd.mfd_processor import (
    MFDDataFetcher,
    MFDHistoryReconstructor,
    MFDMetricsProcessor,
    MFDNetworkParser,
    MFDProcessor,
)
from mfd.mfd_report_generator import (
    MFDAuditSheetFormatter,
    MFDJustificationResolver,
    MFDNeuralProofreader,
    MFDPromptBuilder,
    MFDReportGenerator,
    MFDSectionBuilder,
    MFDSubprocessFallback,
    MFDTableFormatter,
    MFDTemplateProvider,
    MFDTemplateRepository,
)
from mfd.mfd_worker import MFDOrchestrator, run_mfd_worker

__all__ = [
    "MacroscopicFundamentalDiagram",
    "MFDCalculator",
    "MFDClassifier",
    "MFDSnapshot",
    "MFDTracker",
    "NetworkState",
    "MFDAnalyzer",
    "MFDComparisonEngine",
    "MFDDataNormalizer",
    "MFDFallbackFactory",
    "MFDImpactCalculator",
    "MFDImpactLabels",
    "MFDIntersectionMetricsCalculator",
    "MFDMapResolver",
    "MFDMaturityEvaluator",
    "MFDMetricsCalculator",
    "MFDReportBaselineManager",
    "MFDStageAggregator",
    "MFDZoneCalculator",
    "MFDPlotter",
    "MFDDataFetcher",
    "MFDHistoryReconstructor",
    "MFDMetricsProcessor",
    "MFDNetworkParser",
    "MFDProcessor",
    "MFDAuditSheetFormatter",
    "MFDJustificationResolver",
    "MFDNeuralProofreader",
    "MFDPromptBuilder",
    "MFDReportGenerator",
    "MFDSectionBuilder",
    "MFDSubprocessFallback",
    "MFDTableFormatter",
    "MFDTemplateProvider",
    "MFDTemplateRepository",
    "MFDOrchestrator",
    "run_mfd_worker",
]
