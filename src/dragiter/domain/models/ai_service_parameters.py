from dataclasses import dataclass

from dragiter.domain.models.settings import (
    ApiKeyStringSetting, BaseURLStringSetting, ModelNameStringSetting,
    MaxInputTokensIntSetting, MaxOutputTokensIntSetting,
    TemperatureFloatSetting, MaxRetryIntSetting, RetryDelayIntSetting)


@dataclass(frozen=True)
class AIServiceParameters:
    api_key_string_setting: ApiKeyStringSetting
    base_url_string_setting: BaseURLStringSetting
    model_name_string_setting: ModelNameStringSetting
    max_input_token_int_setting: MaxInputTokensIntSetting
    max_output_tokens_int_setting: MaxOutputTokensIntSetting
    temperature_float_setting: TemperatureFloatSetting
    retry_delay_int_setting: RetryDelayIntSetting
    max_retries_int_setting: MaxRetryIntSetting
