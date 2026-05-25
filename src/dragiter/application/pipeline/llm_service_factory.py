from dragiter.domain.models.settings import ApiKeyStringSetting, BaseURLStringSetting, ModelNameStringSetting
from dragiter.domain.models.settings import SimulateBoolSetting
from dragiter.domain.models.prompt_template import PromptTemplate
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


