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
