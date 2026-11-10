# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CARINA Core Interface & Port Contracts (Clean Architecture / Hexagonal Architecture).
Centralizes abstract protocols and ABCs across all subsystems (SOLID: ISP + DIP).
"""

from src.interfaces.controller import (
    IFailsafeManager,
    IHealthMonitor,
    IOverrideManager,
    IRequestProcessor,
    ITelemetryAggregator,
    ITopologyCoordinator,
    ITrafficFrameProcessor,
    IYellowScheduleManager,
)
from src.interfaces.drivers import BaseActiveEventListener, BaseTrafficDriver
from src.interfaces.engine import (
    IActionAuthorizer,
    IActionSupervisor,
    IAgentEvaluator,
    IRewardComputer,
    IStateExtractor,
    IStepProcessor,
)
from src.interfaces.fenix import (
    IProcessRunner,
    IProcessSupervisor,
    IRecoveryPolicy,
    IStateReconciler,
)
from src.interfaces.repositories import (
    IAgentCheckpointRepository,
    ICloudVaultRepository,
    IFluidDynamicsMaintenance,
    IFluidDynamicsReader,
    IFluidDynamicsRepository,
    IFluidDynamicsWriter,
    IMaturityRepository,
    ISimulationRepository,
    IStepDecisionRepository,
    MaturityRepositoryPort,
)
from src.interfaces.security import (
    IAttemptCounterStore,
    IAuthenticator,
    ILockdownManager,
    IPasswordHasher,
    IPasswordPolicy,
    ISynchronizable,
    IUserManagement,
    IUserRepository,
)
from src.interfaces.settings import (
    IEnvironmentProvider,
    ISettingsReader,
    ISettingsStorage,
    ISettingsWriter,
)
from src.interfaces.transports import BaseMonitorTransport

__all__ = [
    "IFailsafeManager",
    "IHealthMonitor",
    "IOverrideManager",
    "IRequestProcessor",
    "ITelemetryAggregator",
    "ITopologyCoordinator",
    "ITrafficFrameProcessor",
    "IYellowScheduleManager",
    "BaseActiveEventListener",
    "BaseTrafficDriver",
    "IActionAuthorizer",
    "IActionSupervisor",
    "IAgentEvaluator",
    "IRewardComputer",
    "IStateExtractor",
    "IStepProcessor",
    "IProcessRunner",
    "IProcessSupervisor",
    "IRecoveryPolicy",
    "IStateReconciler",
    "IAgentCheckpointRepository",
    "ICloudVaultRepository",
    "IFluidDynamicsMaintenance",
    "IFluidDynamicsReader",
    "IFluidDynamicsRepository",
    "IFluidDynamicsWriter",
    "IMaturityRepository",
    "ISimulationRepository",
    "IStepDecisionRepository",
    "MaturityRepositoryPort",
    "IAttemptCounterStore",
    "IAuthenticator",
    "ILockdownManager",
    "IPasswordHasher",
    "IPasswordPolicy",
    "ISynchronizable",
    "IUserManagement",
    "IUserRepository",
    "IEnvironmentProvider",
    "ISettingsReader",
    "ISettingsStorage",
    "ISettingsWriter",
    "BaseMonitorTransport",
]
