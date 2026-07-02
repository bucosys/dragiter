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

from dragiter.domain.models.prompt_template import PromptTemplate
from dragiter.domain.models.settings import ApiKeyStringSetting, BaseURLStringSetting, ModelNameStringSetting
from dragiter.domain.models.settings import SimulateBoolSetting
from dragiter.domain.ports.llm_service import *
from dragiter.infrastructure.llm.llm_service_adapter import LLMServiceAdapter
from dragiter.infrastructure.llm.mockai_service import MockAIService
from dragiter.infrastructure.llm.openai_service import OpenAIService


class LLMServiceFactory():
    def __init__(self) -> None:
        pass

    def run(self,
            api_key_string_setting: ApiKeyStringSetting,
            base_url_string_setting: BaseURLStringSetting,
            model_name_string_setting: ModelNameStringSetting,
            prompt: PromptTemplate,
            simulation_boolean_setting: SimulateBoolSetting
            ) -> LLMService:

        llmservice_protocol = None

        try:
            if simulation_boolean_setting.value:
                llmservice_protocol = MockAIService(
                    api_key=api_key_string_setting.value,
                    base_url=base_url_string_setting.value,
                    model_name=model_name_string_setting.value,
                    temperature=prompt.temperature)
            else:
                llmservice_protocol = OpenAIService(
                    api_key=api_key_string_setting.value,
                    base_url=base_url_string_setting.value,
                    model_name=model_name_string_setting.value,
                    temperature=prompt.temperature)

            return LLMServiceAdapter(llmservice_protocol)

        except Exception as e:
            raise LLMServiceFactoryError(f"Failed to create LLMService.") from e


class LLMServiceFactoryError(Exception):
    pass
