# =============================================================================
# dragiter - Deterministic RAG Iterator
# Copyright (c) 2026 Michael Buchold <michael.buchold@dragiter.app>
#
# This file is part of dragiter.
#
# dragiter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dragiter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with dragiter. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing (closed-source use, SaaS, etc.), please contact:
# Michael Buchold <michael.buchold@dragiter.app>
# =============================================================================

from dataclasses import dataclass

from dragiter.domain.models.settings import (
    ApiKeyStringSetting, BaseURLStringSetting, ModelNameStringSetting,
    MaxContextTokensIntSetting, MaxOutputTokensIntSetting,
    TemperatureFloatSetting, MaxRetryIntSetting, RetryDelayIntSetting, CharsPerTokenFloatSetting)


@dataclass(frozen=True)
class AIServiceParameters:
    api_key_string_setting: ApiKeyStringSetting
    base_url_string_setting: BaseURLStringSetting
    model_name_string_setting: ModelNameStringSetting
    max_context_token_int_setting: MaxContextTokensIntSetting
    max_output_tokens_int_setting: MaxOutputTokensIntSetting
    chars_per_token_float_setting: CharsPerTokenFloatSetting
    temperature_float_setting: TemperatureFloatSetting
    retry_delay_int_setting: RetryDelayIntSetting
    max_retries_int_setting: MaxRetryIntSetting
