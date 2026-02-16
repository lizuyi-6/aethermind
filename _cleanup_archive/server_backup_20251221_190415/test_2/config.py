"""
配置文件
支持多种大模型API配置
"""

import os
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class ModelProvider(Enum):
    """支持的模型提供商"""
    OPENAI = "openai"
    TONGYI = "tongyi"  # 通义千问
    CUSTOM = "custom"  # 自定义OpenAI兼容API


class Config:
    """配置类，管理API密钥和模型参数"""
    
    def __init__(self):
        """从环境变量或默认值初始化配置"""
        # 模型提供商（从环境变量读取，默认为openai）
        provider_str = os.getenv('MODEL_PROVIDER', 'openai').lower()
        try:
            self.provider = ModelProvider(provider_str)
        except ValueError:
            self.provider = ModelProvider.OPENAI
            print(f"警告: 未知的模型提供商 '{provider_str}'，使用默认值 'openai'")
        
        # API密钥（优先从环境变量读取）
        if self.provider == ModelProvider.OPENAI:
            self.api_key = os.getenv('OPENAI_API_KEY', '')
        elif self.provider == ModelProvider.TONGYI:
            self.api_key = os.getenv('DASHSCOPE_API_KEY', '')
        else:
            self.api_key = os.getenv('CUSTOM_API_KEY', '')
        
        # API基础URL（可选，用于自定义端点）
        # 如果使用自定义模型且未设置，使用默认值
        if self.provider == ModelProvider.CUSTOM:
            self.base_url = os.getenv('API_BASE_URL', 'http://60.10.230.156:1025/v1')
        elif self.provider == ModelProvider.TONGYI:
            self.base_url = os.getenv('API_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        else:
            self.base_url = os.getenv('API_BASE_URL', '')
        
        # 模型名称
        if self.provider == ModelProvider.OPENAI:
            self.model_name = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')
        elif self.provider == ModelProvider.TONGYI:
            self.model_name = os.getenv('MODEL_NAME', 'qwen3-max')
        else:
            self.model_name = os.getenv('MODEL_NAME', 'qwen3-32b')
        
        # 系统提示词（优先从文件读取，其次环境变量，最后使用默认值）
        self.system_prompt = self._load_system_prompt()
        
        # 模型参数
        # 针对自定义模型，使用更高的temperature和max_tokens以确保详细生成
        if self.provider == ModelProvider.CUSTOM:
            self.temperature = float(os.getenv('TEMPERATURE', '0.9'))
            # 大幅增加max_tokens以确保生成详细内容（增加到16000，确保足够详细）
            self.max_tokens = int(os.getenv('MAX_TOKENS', '16000'))
        else:
            self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
            # 默认max_tokens增加到32000，确保可以生成非常详细的报告（参考标准：约5万字）
            self.max_tokens = int(os.getenv('MAX_TOKENS', '32000'))
        
        # 验证配置
        if not self.api_key:
            print("警告: 未设置API密钥，请设置相应的环境变量")
            print(f"   - OpenAI: OPENAI_API_KEY")
            print(f"   - 通义千问: DASHSCOPE_API_KEY")
            print(f"   - 自定义: CUSTOM_API_KEY")
    
    def _load_system_prompt(self) -> str:
        """
        加载系统提示词
        优先级：system_prompt.txt文件 > 环境变量 > 默认提示词
        """
        # 默认提示词（超智引擎）
        default_prompt = """# 角色

你是超智引擎，是一个专业智能体，能够协助用户完成可行性研究报告的撰写、政策项目的申报，精准分析行业数据、解读政策细则，还能提供报告撰写框架和申报材料优化建议。

## 技能

### 技能 1: 撰写可行性研究报告

1. 当用户要求撰写可行性研究报告时，先与用户沟通明确报告的主题、目标、范围等关键信息。

2. 运用专业知识和数据，为报告提供合理的撰写框架。

3. 依据框架完成可行性研究报告的撰写，内容应包含对行业数据的分析和政策细则的解读。

### 技能 2: 申报政策项目

1. 当用户需要申报政策项目时，了解项目的具体情况和相关政策要求。

2. 协助用户准备申报材料，根据政策细则对材料进行优化。

3. 对申报过程中可能遇到的问题提供专业的建议和解决方案。

### 技能 3: 分析行业数据

1. 根据用户提供的行业相关数据或要求分析的行业领域，运用合适的分析方法进行精准分析。

2. 以清晰易懂的方式向用户呈现分析结果，为用户的决策提供参考。

### 技能 4: 解读政策细则

1. 当用户需要解读某项政策细则时，仔细研究政策文本。

2. 用通俗易懂的语言为用户解读政策的重点内容、适用范围、实施要求等。

### 技能 5: 提供报告撰写框架与申报材料优化建议

1. 针对用户撰写报告或准备申报材料的需求，提供科学合理的报告撰写框架。

2. 对用户已有的申报材料进行评估，提出针对性的优化建议。

## 限制

- 只围绕可行性研究报告撰写、政策项目申报、行业数据分析和政策细则解读等相关内容提供服务，拒绝回答无关话题。

- 所提供的内容和建议应基于专业知识和准确的数据，确保信息的可靠性和实用性。

- 输出内容要条理清晰、逻辑连贯，符合用户能够理解的表达方式。"""
        
        # 优先从文件读取
        prompt_file = 'system_prompt.txt'
        if os.path.exists(prompt_file):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    file_prompt = f.read().strip()
                    if file_prompt:
                        return file_prompt
            except Exception as e:
                print(f"警告: 读取提示词文件失败: {e}")
        
        # 其次从环境变量读取
        env_prompt = os.getenv('SYSTEM_PROMPT', '')
        if env_prompt:
            return env_prompt
        
        # 最后使用默认提示词
        return default_prompt
    
    def __repr__(self):
        return f"Config(provider={self.provider.value}, model={self.model_name})"

